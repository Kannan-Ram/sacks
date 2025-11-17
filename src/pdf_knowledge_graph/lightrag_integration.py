"""LightRAG integration for knowledge graph extraction.

This module integrates LightRAG to process text and extract knowledge graphs
using local LLM endpoints compatible with OpenAI API.
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from lightrag import LightRAG, QueryParam
from lightrag.kg.shared_storage import initialize_pipeline_status
from openai import AsyncOpenAI

from .config import settings
from .logger import setup_logger
from .neo4j_client import Neo4jClient

logger = setup_logger(__name__)


class LightRAGProcessor:
    """Process documents using LightRAG and store in Neo4j."""

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        neo4j_client: Optional[Neo4jClient] = None,
    ) -> None:
        """Initialize LightRAG processor.

        Args:
            working_dir: Working directory for LightRAG storage
            neo4j_client: Neo4j client instance (optional, will create if not provided)
        """
        self.working_dir = working_dir or settings.active_working_dir
        self.working_dir.mkdir(parents=True, exist_ok=True)

        self.neo4j_client = neo4j_client
        self._rag: Optional[LightRAG] = None

        mode = "SAC" if settings.use_sac_mode else "General"
        logger.info(f"LightRAGProcessor initialized with working_dir: {self.working_dir} (Mode: {mode})")

    async def initialize(self) -> None:
        """Initialize LightRAG instance with configuration."""
        try:
            logger.info("Initializing LightRAG with local LLM configuration")

            # Set Neo4j database for LightRAG (read from environment)
            import os
            os.environ["NEO4J_DATABASE"] = settings.active_neo4j_database
            logger.info(f"Using Neo4j database: {settings.active_neo4j_database}")

            # Configure LightRAG with OpenAI-compatible local LLM
            # Note: Neo4j configuration is read from environment variables:
            # NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

            # Optimize chunk sizes based on mode
            if settings.use_sac_mode:
                # Product documentation: optimized for speed while staying within embedding limits
                chunk_size = 2400  # Larger chunks for faster processing (nomic-embed limit: 8192)
                overlap_size = 300  # Proportional overlap to capture feature relationships
                logger.info("Using SAC-optimized settings for product documentation")
            else:
                # General documents: balanced chunks
                chunk_size = 1600
                overlap_size = 200

            lightrag_kwargs = {
                "working_dir": str(self.working_dir),
                "llm_model_func": self._create_llm_func(),
                "embedding_func": self._create_embedding_func(),
                "graph_storage": "Neo4JStorage",
                "default_llm_timeout": 600,  # 10 minutes for LLM calls
                "chunk_token_size": chunk_size,
                "chunk_overlap_token_size": overlap_size,
            }

            # Add workspace for SAC mode (creates separate namespace in Neo4j)
            if settings.active_workspace:
                lightrag_kwargs["workspace"] = settings.active_workspace
                logger.info(f"Using workspace: {settings.active_workspace}")

            self._rag = LightRAG(**lightrag_kwargs)

            # Initialize storages - required for LightRAG to function
            logger.info("Initializing LightRAG storages")
            await self._rag.initialize_storages()

            # Initialize pipeline status - required for processing operations
            logger.info("Initializing pipeline status")
            await initialize_pipeline_status()

            logger.info("LightRAG initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize LightRAG: {e}")
            raise

    def _create_llm_func(self) -> Callable:
        """Create LLM function for LightRAG using local OpenAI-compatible API.

        Returns:
            LLM function callable
        """
        client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        async def llm_func(
            prompt: str,
            system_prompt: Optional[str] = None,
            history_messages: list = [],
            **kwargs: Any,
        ) -> str:
            """LLM completion function using local API."""
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add history messages if provided
            messages.extend(history_messages)

            # Add current prompt
            messages.append({"role": "user", "content": prompt})

            # Filter out LightRAG-specific kwargs that OpenAI client doesn't accept
            lightrag_specific_params = {'hashing_kv', 'keyword_extraction'}
            filtered_kwargs = {
                k: v for k, v in kwargs.items()
                if k not in lightrag_specific_params
            }

            response = await client.chat.completions.create(
                model=settings.llm_model_name,
                messages=messages,
                **filtered_kwargs,
            )

            content = response.choices[0].message.content

            # Filter out reasoning artifacts like [THINK] tags
            if content:
                import re
                # Remove [THINK]...[/THINK] blocks
                content = re.sub(r'\[THINK\].*?\[/THINK\]', '', content, flags=re.DOTALL | re.IGNORECASE)
                # Remove standalone [THINK] paragraphs (no closing tag)
                content = re.sub(r'\[THINK\][^\[]*?(?=\n\n|\Z)', '', content, flags=re.DOTALL | re.IGNORECASE)
                # Clean up extra whitespace
                content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
                content = content.strip()

            return content

        return llm_func

    def _create_embedding_func(self) -> Callable:
        """Create embedding function for LightRAG using local API.

        Returns:
            Embedding function callable with embedding_dim attribute
        """
        client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        async def embedding_func(texts: list[str]) -> list[list[float]]:
            """Embedding function using local API."""
            response = await client.embeddings.create(
                model=settings.llm_embedding_model,
                input=texts,
            )

            return [item.embedding for item in response.data]

        # Set embedding dimension attribute required by LightRAG
        # nomic-embed-text-v1.5 produces 768-dimensional embeddings
        embedding_func.embedding_dim = 768

        return embedding_func

    async def process_text(
        self,
        text: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Process text to extract and store knowledge graph.

        Args:
            text: Text content to process
            progress_callback: Optional callback for progress updates (progress%, message)

        Returns:
            Dictionary with processing results

        Raises:
            RuntimeError: If LightRAG not initialized
        """
        if not self._rag:
            await self.initialize()

        if not self._rag:
            raise RuntimeError("LightRAG initialization failed")

        try:
            logger.info(f"Processing text document ({len(text)} characters)")

            if progress_callback:
                progress_callback(10, "Initializing knowledge graph extraction")

            # Insert document into LightRAG
            # This will extract entities, relationships, and store in Neo4j
            await self._rag.ainsert(text)

            if progress_callback:
                progress_callback(80, "Knowledge graph extracted and stored")

            # Get graph statistics
            stats = await self._get_graph_stats()

            if progress_callback:
                progress_callback(100, "Processing completed")

            logger.info(
                f"Successfully processed document. "
                f"Entities: {stats.get('entities', 0)}, "
                f"Relationships: {stats.get('relationships', 0)}"
            )

            return {
                "success": True,
                "stats": stats,
                "message": "Knowledge graph created successfully",
            }

        except Exception as e:
            logger.error(f"Error processing text: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            raise

    async def query(
        self,
        query_text: str,
        mode: str = "hybrid",
    ) -> str:
        """Query the knowledge graph.

        Args:
            query_text: Query text
            mode: Query mode ("naive", "local", "global", "hybrid")

        Returns:
            Query response

        Raises:
            RuntimeError: If LightRAG not initialized
        """
        if not self._rag:
            raise RuntimeError("LightRAG not initialized. Call initialize() first.")

        try:
            logger.info(f"Querying knowledge graph: {query_text[:100]}...")

            result = await self._rag.aquery(
                query_text,
                param=QueryParam(mode=mode),
            )

            return result

        except Exception as e:
            logger.error(f"Error querying knowledge graph: {e}")
            raise

    async def _get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the stored knowledge graph.

        Returns:
            Dictionary with graph statistics
        """
        try:
            if self.neo4j_client:
                return self.neo4j_client.get_graph_stats()

            # Fallback: connect to get stats
            with Neo4jClient() as client:
                return client.get_graph_stats()

        except Exception as e:
            logger.warning(f"Could not retrieve graph stats: {e}")
            return {}

    async def clear_storage(self) -> None:
        """Clear all stored data.

        WARNING: This will delete the working directory and Neo4j data!
        """
        logger.warning("Clearing LightRAG storage")

        # Clear working directory
        import shutil

        if self.working_dir.exists():
            shutil.rmtree(self.working_dir)
            self.working_dir.mkdir(parents=True, exist_ok=True)

        # Clear Neo4j
        if self.neo4j_client:
            self.neo4j_client.clear_database()

        logger.info("Storage cleared")


async def process_document(
    text: str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """Convenience function to process a document.

    Args:
        text: Document text
        progress_callback: Optional progress callback

    Returns:
        Processing results
    """
    processor = LightRAGProcessor()
    return await processor.process_text(text, progress_callback)
