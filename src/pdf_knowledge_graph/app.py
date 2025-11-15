"""Streamlit frontend for PDF Knowledge Graph application.

This module provides a user-friendly interface for uploading PDFs
and monitoring the knowledge graph creation process.
"""

import time
from typing import Optional
from uuid import UUID

import httpx
import streamlit as st

from pdf_knowledge_graph.config import settings

# Page configuration
st.set_page_config(
    page_title="PDF Knowledge Graph Builder",
    page_icon="📚",
    layout="wide",
)


class APIClient:
    """Client for communicating with FastAPI backend."""

    def __init__(self, base_url: str) -> None:
        """Initialize API client.

        Args:
            base_url: Base URL of the FastAPI backend
        """
        self.base_url = base_url.rstrip("/")

    def upload_pdf(self, file_bytes: bytes, filename: str) -> dict:
        """Upload PDF file to backend.

        Args:
            file_bytes: PDF file content
            filename: Name of the file

        Returns:
            Upload response dictionary

        Raises:
            httpx.HTTPError: If upload fails
        """
        with httpx.Client(timeout=30.0) as client:
            files = {"file": (filename, file_bytes, "application/pdf")}
            response = client.post(f"{self.base_url}/upload", files=files)
            response.raise_for_status()
            return response.json()

    def get_status(self, job_id: UUID) -> dict:
        """Get job status from backend.

        Args:
            job_id: Job identifier

        Returns:
            Status response dictionary

        Raises:
            httpx.HTTPError: If request fails
        """
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self.base_url}/status/{job_id}")
            response.raise_for_status()
            return response.json()

    def check_health(self) -> dict:
        """Check backend health.

        Returns:
            Health status dictionary
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception:
            return {"status": "unhealthy"}


def render_header() -> None:
    """Render application header."""
    st.title("📚 PDF Knowledge Graph Builder")
    st.markdown(
        """
        Upload PDF documents to automatically extract knowledge graphs using LightRAG and Neo4j.
        The application processes your PDFs, extracts entities and relationships,
        and stores them in a Neo4j graph database for visualization and querying.
        """
    )
    st.divider()


def render_sidebar() -> None:
    """Render sidebar with configuration and help."""
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API connection status
        api_url = f"http://{settings.api_host}:{settings.api_port}"
        client = APIClient(api_url)
        health = client.check_health()

        if health.get("status") == "healthy":
            st.success("✅ Backend: Connected")
            neo4j_status = health.get("neo4j", "unknown")
            if "connected" in str(neo4j_status):
                st.success("✅ Neo4j: Connected")
            else:
                st.error(f"❌ Neo4j: {neo4j_status}")
        else:
            st.error("❌ Backend: Disconnected")
            st.warning(f"Make sure the API is running at {api_url}")

        st.divider()

        st.header("ℹ️ About")
        st.markdown(
            """
            **Components:**
            - **LightRAG**: Knowledge extraction
            - **Neo4j**: Graph database storage
            - **Local LLM**: Text processing

            **Neo4j Browser:**
            Access your graph at:
            """
        )
        neo4j_browser_url = settings.neo4j_uri.replace("neo4j://", "http://").replace(
            ":7687", ":7474"
        )
        st.code(neo4j_browser_url, language=None)

        st.divider()

        st.header("📖 Quick Start")
        st.markdown(
            """
            1. Upload a PDF file
            2. Wait for processing to complete
            3. View the knowledge graph in Neo4j Browser
            4. Query your data using Cypher
            """
        )


def render_upload_section() -> Optional[dict]:
    """Render PDF upload section.

    Returns:
        Upload response if file uploaded, None otherwise
    """
    st.header("📤 Upload PDF")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload a PDF document to extract its knowledge graph",
    )

    if uploaded_file is not None:
        # Display file info
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Filename", uploaded_file.name)
        with col2:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.metric("File Size", f"{file_size_mb:.2f} MB")

        # Upload button
        if st.button("🚀 Process PDF", type="primary", use_container_width=True):
            try:
                with st.spinner("Uploading file..."):
                    api_url = f"http://{settings.api_host}:{settings.api_port}"
                    client = APIClient(api_url)

                    file_bytes = uploaded_file.read()
                    response = client.upload_pdf(file_bytes, uploaded_file.name)

                st.success("✅ File uploaded successfully!")
                return response

            except Exception as e:
                st.error(f"❌ Upload failed: {str(e)}")
                return None

    return None


def render_status_section(job_id: str) -> None:
    """Render job status monitoring section.

    Args:
        job_id: Job identifier to monitor
    """
    st.header("📊 Processing Status")

    api_url = f"http://{settings.api_host}:{settings.api_port}"
    client = APIClient(api_url)

    # Status container
    status_container = st.empty()
    progress_bar = st.progress(0)
    message_container = st.empty()

    # Poll for status updates
    max_polls = 300  # 5 minutes max (with 1 second interval)
    poll_count = 0

    while poll_count < max_polls:
        try:
            status = client.get_status(UUID(job_id))

            # Update progress
            progress = status.get("progress", 0)
            progress_bar.progress(progress / 100)

            # Update message
            message = status.get("message", "Processing...")
            message_container.info(f"📝 {message}")

            # Check status
            job_status = status.get("status")

            if job_status == "completed":
                status_container.success("✅ Processing completed successfully!")
                st.balloons()

                # Display Neo4j link
                st.success(
                    """
                    **🎉 Knowledge Graph Created!**

                    Your PDF has been processed and the knowledge graph is now stored in Neo4j.
                    """
                )

                neo4j_browser_url = settings.neo4j_uri.replace(
                    "neo4j://", "http://"
                ).replace(":7687", ":7474")

                st.markdown(
                    f"""
                    **View your graph:**
                    - Open [Neo4j Browser]({neo4j_browser_url})
                    - Login with your credentials
                    - Run queries to explore your knowledge graph

                    **Example Cypher query:**
                    ```cypher
                    MATCH (n)-[r]->(m)
                    RETURN n, r, m
                    LIMIT 100
                    ```
                    """
                )
                break

            elif job_status == "failed":
                error = status.get("error", "Unknown error")
                status_container.error(f"❌ Processing failed: {error}")
                break

            # Continue polling
            time.sleep(1)
            poll_count += 1

        except Exception as e:
            message_container.error(f"❌ Error checking status: {str(e)}")
            break

    if poll_count >= max_polls:
        st.warning("⚠️ Status check timed out. The job may still be processing.")


def main() -> None:
    """Main Streamlit application."""
    render_header()
    render_sidebar()

    # Session state for job tracking
    if "current_job_id" not in st.session_state:
        st.session_state.current_job_id = None

    # Upload section
    upload_response = render_upload_section()

    if upload_response:
        job_id = upload_response.get("job_id")
        if job_id:
            st.session_state.current_job_id = job_id

    # Status section
    if st.session_state.current_job_id:
        st.divider()
        render_status_section(st.session_state.current_job_id)

        # Reset button
        if st.button("🔄 Process Another PDF", use_container_width=True):
            st.session_state.current_job_id = None
            st.rerun()


if __name__ == "__main__":
    main()
