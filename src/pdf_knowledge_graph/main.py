"""FastAPI backend for PDF Knowledge Graph application.

This module provides REST API endpoints for uploading PDFs,
processing them into knowledge graphs, and tracking job status.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Dict
from uuid import UUID, uuid4

import aiofiles
from fastapi import FastAPI, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .logger import setup_logger
from .models import (
    JobInfo,
    ProcessingStatus,
    StatusResponse,
    UploadResponse,
)
from .pdf_processor import PDFProcessor
from .lightrag_integration import LightRAGProcessor
from .neo4j_client import Neo4jClient

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting PDF Knowledge Graph API")
    logger.info(f"Upload directory: {settings.upload_dir}")
    logger.info(f"Working directory: {settings.active_working_dir}")

    # Log SAC mode if enabled
    if settings.use_sac_mode:
        logger.info(f"SAC Mode: ENABLED")
        logger.info(f"Workspace: {settings.active_workspace}")
        logger.info(f"Chunk size optimized for product documentation")
    else:
        logger.info(f"SAC Mode: DISABLED")

    # Verify Neo4j connection
    try:
        with Neo4jClient() as client:
            if client.verify_connection():
                logger.info("Neo4j connection verified")
            else:
                logger.warning("Could not verify Neo4j connection")
    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down PDF Knowledge Graph API")


# FastAPI app
app = FastAPI(
    title="PDF Knowledge Graph API",
    description="Build knowledge graphs from PDF documents using LightRAG and Neo4j",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job storage (in production, use Redis or database)
jobs: Dict[UUID, JobInfo] = {}

# Processors
pdf_processor = PDFProcessor()


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "PDF Knowledge Graph API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "upload": "POST /upload",
            "status": "GET /status/{job_id}",
            "health": "GET /health",
        },
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    # Check Neo4j connection
    neo4j_status = "unknown"
    try:
        with Neo4jClient() as client:
            neo4j_status = "connected" if client.verify_connection() else "disconnected"
    except Exception as e:
        neo4j_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "neo4j": neo4j_status,
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    """Upload PDF file for processing.

    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded PDF file

    Returns:
        Upload response with job ID

    Raises:
        HTTPException: If file validation fails
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted",
        )

    # Create job
    job_id = uuid4()
    file_path = settings.upload_dir / f"{job_id}_{file.filename}"

    job = JobInfo(
        job_id=job_id,
        filename=file.filename,
        file_path=str(file_path),
        status=ProcessingStatus.PENDING,
        message="File uploaded, processing queued",
    )
    jobs[job_id] = job

    logger.info(f"Created job {job_id} for file: {file.filename}")

    # Save uploaded file
    try:
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"Saved file to: {file_path}")

    except Exception as e:
        logger.error(f"Error saving file: {e}")
        job.status = ProcessingStatus.FAILED
        job.error = f"Failed to save file: {str(e)}"
        raise HTTPException(status_code=500, detail=str(e))

    # Schedule background processing
    background_tasks.add_task(process_pdf_job, job_id)

    return UploadResponse(
        job_id=job_id,
        filename=file.filename,
        status=ProcessingStatus.PENDING,
        message="File uploaded successfully, processing started",
    )


@app.get("/status/{job_id}", response_model=StatusResponse)
async def get_job_status(job_id: UUID) -> StatusResponse:
    """Get processing status for a job.

    Args:
        job_id: Job identifier

    Returns:
        Job status response

    Raises:
        HTTPException: If job not found
    """
    job = jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found",
        )

    return job.to_status_response()


async def process_pdf_job(job_id: UUID) -> None:
    """Background task to process PDF and create knowledge graph.

    Args:
        job_id: Job identifier
    """
    job = jobs.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    try:
        # Update status
        job.status = ProcessingStatus.PROCESSING
        job.message = "Extracting text from PDF"
        job.progress = 10
        job.updated_at = datetime.utcnow()

        logger.info(f"Processing job {job_id}: {job.filename}")

        # Extract text from PDF
        pdf_path = Path(job.file_path)
        text, metadata = pdf_processor.extract_text(pdf_path)

        job.message = f"Extracted {metadata.text_length} characters using {metadata.extraction_method}"
        job.progress = 30
        job.updated_at = datetime.utcnow()

        logger.info(
            f"Extracted {metadata.text_length} chars from {metadata.num_pages} pages"
        )

        # Process with LightRAG
        job.message = "Creating knowledge graph with LightRAG"
        job.progress = 40
        job.updated_at = datetime.utcnow()

        def progress_callback(progress: int, message: str) -> None:
            """Update job progress."""
            job.progress = min(40 + int(progress * 0.5), 90)
            job.message = message
            job.updated_at = datetime.utcnow()

        processor = LightRAGProcessor()
        result = await processor.process_text(text, progress_callback)

        # Complete job
        job.status = ProcessingStatus.COMPLETED
        job.message = "Knowledge graph created successfully"
        job.progress = 100
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()

        logger.info(f"Job {job_id} completed successfully")
        logger.info(f"Graph stats: {result.get('stats', {})}")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        job.status = ProcessingStatus.FAILED
        job.message = "Processing failed"
        job.error = str(e)
        job.updated_at = datetime.utcnow()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "pdf_knowledge_graph.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
