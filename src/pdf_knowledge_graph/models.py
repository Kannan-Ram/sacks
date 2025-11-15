"""Pydantic models for request/response validation and data structures.

This module defines the data models used throughout the application
for type safety and validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Status of PDF processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadResponse(BaseModel):
    """Response model for PDF upload endpoint."""

    job_id: UUID = Field(default_factory=uuid4, description="Unique job identifier")
    filename: str = Field(description="Name of uploaded file")
    status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING,
        description="Current processing status",
    )
    message: str = Field(description="Status message")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Job creation timestamp",
    )


class StatusResponse(BaseModel):
    """Response model for job status endpoint."""

    job_id: UUID = Field(description="Job identifier")
    filename: str = Field(description="Name of processed file")
    status: ProcessingStatus = Field(description="Current processing status")
    message: str = Field(description="Status message or error details")
    progress: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Processing progress percentage",
    )
    created_at: datetime = Field(description="Job creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Job completion timestamp",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed",
    )


class JobInfo(BaseModel):
    """Internal job tracking model."""

    job_id: UUID = Field(default_factory=uuid4)
    filename: str
    file_path: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    message: str = "Job created"
    progress: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_status_response(self) -> StatusResponse:
        """Convert to StatusResponse model."""
        return StatusResponse(
            job_id=self.job_id,
            filename=self.filename,
            status=self.status,
            message=self.message,
            progress=self.progress,
            created_at=self.created_at,
            updated_at=self.updated_at,
            completed_at=self.completed_at,
            error=self.error,
        )


class PDFMetadata(BaseModel):
    """Metadata extracted from PDF."""

    filename: str
    num_pages: int
    text_length: int
    has_text: bool
    extraction_method: str  # "direct" or "ocr"
