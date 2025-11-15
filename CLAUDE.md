# Claude Code Development Guide

This guide is designed for working on the PDF Knowledge Graph project using VS Code with Claude Code.

## Project Overview

**PDF Knowledge Graph Builder** is a Python web application that:
- Extracts text from PDF documents (with OCR fallback)
- Uses LightRAG framework with local LLM to extract knowledge graphs
- Stores graphs in Neo4j for visualization and querying
- Provides FastAPI backend and Streamlit frontend

## Quick Start for Development

### Initial Setup

```bash
# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in development mode with dev dependencies
uv pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your actual configuration
```

### Running the Application

**Terminal 1 - FastAPI Backend:**
```bash
python -m src.pdf_knowledge_graph.main
# Runs on http://localhost:8000
```

**Terminal 2 - Streamlit Frontend:**
```bash
streamlit run src/pdf_knowledge_graph/app.py
# Runs on http://localhost:8501
```

**Terminal 3 - Neo4j (if using Docker):**
```bash
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-password neo4j:latest
```

## Project Architecture

### Core Components

1. **`config.py`**: Environment-based configuration using Pydantic Settings
   - Validates all settings on load
   - Creates necessary directories automatically
   - Single source of truth for all configuration

2. **`logger.py`**: Centralized logging setup
   - Console and file handlers
   - Configurable log levels
   - Module-specific loggers

3. **`models.py`**: Pydantic models for data validation
   - `JobInfo`: Internal job tracking
   - `UploadResponse`: API upload response
   - `StatusResponse`: Job status response
   - `PDFMetadata`: PDF extraction metadata

4. **`pdf_processor.py`**: PDF text extraction
   - Direct text extraction using PyMuPDF
   - OCR fallback using Tesseract
   - Automatic method selection based on text availability

5. **`neo4j_client.py`**: Neo4j database operations
   - Connection management with context manager
   - Query execution
   - Graph statistics
   - Node/relationship creation helpers

6. **`lightrag_integration.py`**: LightRAG framework wrapper
   - Configures LightRAG with local LLM endpoints
   - Processes text to extract knowledge graphs
   - Progress callbacks for long-running operations
   - Automatic Neo4j integration

7. **`main.py`**: FastAPI backend
   - `/upload` - PDF upload endpoint
   - `/status/{job_id}` - Job status checking
   - `/health` - Health check with Neo4j status
   - Background task processing

8. **`app.py`**: Streamlit frontend
   - File upload interface
   - Real-time status monitoring
   - Progress visualization
   - Neo4j browser links

## Development Workflow

### Adding New Features

When adding features, follow this pattern:

1. **Update Models** (`models.py`) if new data structures needed
2. **Implement Core Logic** in appropriate module
3. **Add API Endpoint** (`main.py`) if needed
4. **Update UI** (`app.py`) to expose new functionality
5. **Add Tests** in `tests/` directory
6. **Update Documentation** (README.md)

### Code Style

The project uses:
- **Black**: Code formatting (line length 100)
- **Ruff**: Linting and code quality
- **MyPy**: Type checking
- **Type hints**: Required for all functions

Run quality checks:
```bash
# Format code
black src/

# Check linting
ruff check src/

# Type checking
mypy src/

# Run all at once
black src/ && ruff check src/ && mypy src/
```

### Type Hints Best Practices

```python
# Good examples from the project:

# Function with type hints
async def process_text(
    self,
    text: str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """Process text to extract knowledge graph."""
    pass

# Pydantic model with validation
class JobInfo(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    filename: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

## Common Development Tasks

### Testing PDF Processing

```python
from pathlib import Path
from src.pdf_knowledge_graph.pdf_processor import extract_text_from_pdf

# Test with a sample PDF
pdf_path = Path("test.pdf")
text, metadata = extract_text_from_pdf(pdf_path)

print(f"Extracted {len(text)} characters")
print(f"Method: {metadata.extraction_method}")
print(f"Pages: {metadata.num_pages}")
```

### Testing Neo4j Connection

```python
from src.pdf_knowledge_graph.neo4j_client import Neo4jClient

with Neo4jClient() as client:
    stats = client.get_graph_stats()
    print(f"Nodes: {stats['nodes']}")
    print(f"Relationships: {stats['relationships']}")
```

### Testing LightRAG Integration

```python
import asyncio
from src.pdf_knowledge_graph.lightrag_integration import process_document

async def test_lightrag():
    sample_text = "Your test document text here..."

    def progress(percent, message):
        print(f"{percent}% - {message}")

    result = await process_document(sample_text, progress)
    print(result)

# Run async function
asyncio.run(test_lightrag())
```

## Debugging Tips

### Enable Debug Logging

In `.env`:
```bash
LOG_LEVEL=DEBUG
```

This provides detailed logs for:
- PDF processing steps
- LightRAG operations
- Neo4j queries
- API requests

### Common Issues and Solutions

#### Issue: "Neo4j connection failed"
**Solution:**
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Or check Neo4j service
sudo systemctl status neo4j

# Verify connection manually
curl http://localhost:7474
```

#### Issue: "LLM API timeout"
**Solution:**
- Check if LLM server is running
- Verify model is loaded in LM Studio/Ollama
- Test API endpoint:
```bash
curl http://127.0.0.1:1234/v1/models
```

#### Issue: "OCR not working"
**Solution:**
```bash
# Verify Tesseract installation
tesseract --version

# Verify Poppler installation
pdftoppm -v
```

#### Issue: "Import errors"
**Solution:**
```bash
# Reinstall in development mode
uv pip install -e .

# Or force reinstall
uv pip install --force-reinstall -e .
```

### Using Python Debugger

Add breakpoints in VS Code or use `pdb`:

```python
import pdb; pdb.set_trace()
```

For async code:
```python
import ipdb; await ipdb.set_trace()
```

## Testing Strategy

### Unit Tests

Create tests in `tests/` directory:

```python
# tests/test_pdf_processor.py
import pytest
from pathlib import Path
from src.pdf_knowledge_graph.pdf_processor import PDFProcessor

def test_pdf_validation():
    processor = PDFProcessor()
    assert processor.validate_pdf(Path("test.pdf"))

@pytest.mark.asyncio
async def test_lightrag_processing():
    # Test async functions
    pass
```

Run tests:
```bash
pytest
pytest -v  # verbose
pytest tests/test_pdf_processor.py  # specific file
pytest -k "test_name"  # specific test
```

### Integration Tests

Test full workflow:

```python
@pytest.mark.asyncio
async def test_full_workflow():
    # 1. Upload PDF
    # 2. Process with LightRAG
    # 3. Verify Neo4j storage
    # 4. Query graph
    pass
```

## Environment Variables Reference

Key variables to configure for development:

```bash
# LLM Configuration - Update these for your setup
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_MODEL_NAME=your-model-name  # e.g., "llama-2-7b-chat"
LLM_EMBEDDING_MODEL=your-embedding-model  # e.g., "nomic-embed-text"

# Neo4j - Use different DB for testing
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test-password

# Directories - Use test directories
UPLOAD_DIR=./test_uploads
WORKING_DIR=./test_working

# Logging
LOG_LEVEL=DEBUG  # Development: DEBUG, Production: INFO
```

## Performance Optimization

### For Large PDFs

1. **Chunk Processing**: Break large documents into chunks
```python
# In pdf_processor.py, modify _extract_text_direct
# Process pages in batches
```

2. **Async Processing**: Leverage async/await for I/O operations
```python
# Already implemented in lightrag_integration.py
await processor.process_text(text)
```

3. **Caching**: LightRAG includes caching via `openai_complete_if_cache`

### Database Performance

Configure Neo4j for better performance:

```cypher
// Create indexes for common queries
CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name);
CREATE INDEX document_id IF NOT EXISTS FOR (n:Document) ON (n.id);
```

## Extending the Application

### Adding New PDF Processing Methods

```python
# In pdf_processor.py
def _extract_text_custom(self, pdf_path: Path) -> str:
    """Your custom extraction method."""
    pass

# Update extract_text() to use it
```

### Adding Custom LightRAG Prompts

```python
# In lightrag_integration.py
# LightRAG supports custom prompt templates
# See LightRAG documentation for details
```

### Adding New API Endpoints

```python
# In main.py
@app.post("/custom-endpoint")
async def custom_endpoint(data: CustomModel) -> Response:
    """Your custom endpoint."""
    pass
```

### Adding UI Components

```python
# In app.py
def render_custom_section():
    st.header("Custom Feature")
    # Your Streamlit components
```

## Git Workflow

### Branch Naming
- Feature: `feature/description`
- Bug fix: `fix/description`
- Documentation: `docs/description`

### Commit Messages
```
type(scope): description

- feat: New feature
- fix: Bug fix
- docs: Documentation
- refactor: Code refactoring
- test: Tests
- chore: Maintenance

Example:
feat(pdf): add support for password-protected PDFs
```

## Resources

### Documentation Links
- [LightRAG](https://github.com/HKUDS/LightRAG)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://docs.streamlit.io/)
- [PyMuPDF](https://pymupdf.readthedocs.io/)
- [Pydantic](https://docs.pydantic.dev/)

### Neo4j Cypher Queries

Useful queries for development:

```cypher
// Count all nodes
MATCH (n) RETURN count(n)

// View schema
CALL db.schema.visualization()

// Find entities by type
MATCH (n:Entity) RETURN n.name, n.type LIMIT 25

// Find relationships
MATCH ()-[r]->() RETURN type(r), count(r)

// Delete all data (careful!)
MATCH (n) DETACH DELETE n
```

## Best Practices

1. **Always use type hints**: Helps catch bugs early
2. **Validate inputs**: Use Pydantic models
3. **Log appropriately**: Debug for development, Info for production
4. **Handle errors gracefully**: Use try/except with specific exceptions
5. **Test edge cases**: Empty PDFs, large files, network failures
6. **Document functions**: Use docstrings with Args/Returns/Raises
7. **Use async for I/O**: File operations, API calls, database queries
8. **Keep secrets in .env**: Never commit credentials
9. **Use context managers**: For database connections, file handles
10. **Profile performance**: Use cProfile for bottlenecks

## Quick Reference Commands

```bash
# Development
source .venv/bin/activate
python -m src.pdf_knowledge_graph.main  # Start API
streamlit run src/pdf_knowledge_graph/app.py  # Start UI

# Code Quality
black src/ && ruff check src/ && mypy src/

# Testing
pytest -v

# Package Management
uv pip install package-name
uv pip list
uv pip freeze > requirements.txt

# Docker (Neo4j)
docker start neo4j
docker stop neo4j
docker logs neo4j

# Debugging
tail -f app.log  # Watch logs
python -m pdb script.py  # Debug script
```

## Getting Help

When asking for help from Claude Code:

1. **Provide context**: "I'm working on the PDF processor module..."
2. **Include error messages**: Full stack traces help
3. **Share relevant code**: The specific function/class
4. **Describe expected vs actual**: What should happen vs what does
5. **Mention what you've tried**: Steps already attempted

## Next Steps

Common development tasks to explore:

1. Add authentication to the API
2. Implement PDF chunking for large documents
3. Add query interface in Streamlit UI
4. Create visualization of knowledge graph in UI
5. Add batch processing for multiple PDFs
6. Implement caching layer with Redis
7. Add support for other document types (DOCX, TXT)
8. Create CLI interface
9. Add export functionality (JSON, CSV)
10. Implement user management and multi-tenancy

Happy coding! 🚀
