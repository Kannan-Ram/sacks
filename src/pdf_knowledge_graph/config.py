"""Configuration management for the PDF Knowledge Graph application.

This module handles loading and validating environment variables
using pydantic-settings for type safety and validation.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    llm_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        description="Base URL for local LLM OpenAI-compatible API",
    )
    llm_api_key: str = Field(
        default="placeholder-api-key",
        description="API key for LLM (if required)",
    )
    llm_model_name: str = Field(
        default="placeholder-model",
        description="Model name for chat completions",
    )
    llm_embedding_model: str = Field(
        default="placeholder-embedding",
        description="Model name for embeddings",
    )

    # Neo4j Configuration
    neo4j_uri: str = Field(
        default="neo4j://127.0.0.1:7687",
        description="Neo4j database URI",
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username",
    )
    neo4j_password: str = Field(
        default="placeholder-password",
        description="Neo4j password",
    )

    # Application Configuration
    upload_dir: Path = Field(
        default=Path("./uploads"),
        description="Directory for uploaded PDFs",
    )
    working_dir: Path = Field(
        default=Path("./working"),
        description="Working directory for LightRAG",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Server Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="FastAPI host",
    )
    api_port: int = Field(
        default=8000,
        description="FastAPI port",
    )
    streamlit_port: int = Field(
        default=8501,
        description="Streamlit port",
    )

    @field_validator("upload_dir", "working_dir")
    @classmethod
    def create_directory(cls, v: Path) -> Path:
        """Ensure directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper


# Global settings instance
settings = Settings()
