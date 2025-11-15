"""Logging configuration for the PDF Knowledge Graph application.

This module sets up structured logging with appropriate formatters
and handlers for both file and console output.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .config import settings


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: Optional[str] = None,
) -> logging.Logger:
    """Set up a logger with console and optional file handlers.

    Args:
        name: Logger name (typically __name__ of the calling module)
        log_file: Optional path to log file
        level: Optional log level override (defaults to settings.log_level)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    log_level = getattr(logging, level or settings.log_level)
    logger.setLevel(log_level)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# Default application logger
app_logger = setup_logger("pdf_knowledge_graph", log_file=Path("app.log"))
