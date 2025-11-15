# PDF Knowledge Graph Builder

Build knowledge graphs from PDF documents using LightRAG and Neo4j, powered by local LLM models.

## Overview

This application automatically extracts knowledge graphs from PDF documents by:
1. Extracting text from PDFs (with OCR fallback for scanned documents)
2. Processing text with LightRAG using a local LLM
3. Storing entities and relationships in Neo4j graph database
4. Providing a web interface for upload and monitoring

## Features

- **PDF Processing**: Handles both text-based and scanned PDFs with OCR fallback
- **Local LLM Integration**: Uses OpenAI-compatible API endpoints for privacy and control
- **Knowledge Graph Extraction**: Automatically identifies entities and relationships
- **Neo4j Storage**: Stores graphs in Neo4j for powerful querying and visualization
- **Modern Web UI**: Clean Streamlit interface for file upload and progress tracking
- **RESTful API**: FastAPI backend for programmatic access
- **Type Safety**: Full type hints and validation with Pydantic
- **Production Ready**: Comprehensive logging, error handling, and configuration management

## Architecture

```
┌─────────────────┐
│   Streamlit UI  │  (Frontend - Port 8501)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI       │  (Backend - Port 8000)
└────────┬────────┘
         │
    ┌────┴────────────────┐
    ▼                     ▼
┌─────────┐         ┌──────────┐
│ LightRAG│         │  Neo4j   │
└────┬────┘         └──────────┘
     │
     ▼
┌─────────────┐
│  Local LLM  │  (OpenAI-compatible API)
└─────────────┘
```

## Requirements

### System Requirements

- **Python**: 3.11 or higher
- **uv**: Modern Python package manager ([installation guide](https://github.com/astral-sh/uv))
- **Neo4j**: 5.x or higher
- **Tesseract**: For OCR functionality (optional, for scanned PDFs)
- **Poppler**: For PDF to image conversion (optional, for scanned PDFs)

### Local LLM Server

You need a local LLM server with OpenAI-compatible API endpoints:
- [LM Studio](https://lmstudio.ai/)
- [Ollama with OpenAI compatibility](https://github.com/ollama/ollama/blob/main/docs/openai.md)
- [Text Generation WebUI](https://github.com/oobabooga/text-generation-webui)
- [vLLM](https://github.com/vllm-project/vllm)

Your LLM server must provide:
- `/v1/chat/completions` endpoint
- `/v1/embeddings` endpoint

## Installation

### 1. Install System Dependencies

#### Ubuntu/Debian
```bash
# Install Tesseract and Poppler for OCR support
sudo apt-get update
sudo apt-get install tesseract-ocr poppler-utils

# Install Neo4j (optional if using Docker)
# See: https://neo4j.com/docs/operations-manual/current/installation/linux/debian/
```

#### macOS
```bash
# Install Tesseract and Poppler
brew install tesseract poppler

# Install Neo4j (optional if using Docker)
brew install neo4j
```

#### Windows
- Download and install Tesseract from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- Download and install Poppler from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)
- Add both to your PATH

### 2. Install Neo4j

#### Option A: Using Docker (Recommended)
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-password \
  neo4j:latest
```

#### Option B: Native Installation
Follow the [official Neo4j installation guide](https://neo4j.com/docs/operations-manual/current/installation/)

### 3. Set Up Local LLM Server

1. Install and run your preferred LLM server (e.g., LM Studio)
2. Load a model that supports both chat and embeddings
3. Enable the OpenAI-compatible API server
4. Note the base URL (typically `http://127.0.0.1:1234/v1`)

### 4. Install Python Application

```bash
# Clone the repository
cd pdf-knowledge-graph

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or your preferred editor
```

Required configuration in `.env`:

```bash
# Local LLM Configuration
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_API_KEY=placeholder-api-key
LLM_MODEL_NAME=your-model-name
LLM_EMBEDDING_MODEL=your-embedding-model-name

# Neo4j Configuration
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
```

## Usage

### Start the Application

#### Terminal 1: Start FastAPI Backend
```bash
source .venv/bin/activate
python -m src.pdf_knowledge_graph.main
```

The API will be available at `http://localhost:8000`

#### Terminal 2: Start Streamlit Frontend
```bash
source .venv/bin/activate
streamlit run src/pdf_knowledge_graph/app.py
```

The UI will be available at `http://localhost:8501`

### Using the Web Interface

1. Open `http://localhost:8501` in your browser
2. Upload a PDF file using the file uploader
3. Click "Process PDF"
4. Monitor the processing status
5. Once complete, open Neo4j Browser to visualize your knowledge graph

### Using the API Directly

#### Upload PDF
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@your-document.pdf"
```

Response:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "your-document.pdf",
  "status": "pending",
  "message": "File uploaded successfully, processing started",
  "created_at": "2024-01-15T10:30:00"
}
```

#### Check Status
```bash
curl "http://localhost:8000/status/{job_id}"
```

### Viewing the Knowledge Graph

1. Open Neo4j Browser: `http://localhost:7474`
2. Login with your credentials (default: neo4j/your-password)
3. Run Cypher queries to explore your graph:

```cypher
// View all nodes and relationships
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 100

// Find specific entities
MATCH (n)
WHERE n.name CONTAINS 'keyword'
RETURN n

// Analyze graph structure
CALL db.schema.visualization()
```

## Project Structure

```
pdf-knowledge-graph/
├── src/
│   └── pdf_knowledge_graph/
│       ├── __init__.py           # Package initialization
│       ├── main.py               # FastAPI backend
│       ├── app.py                # Streamlit frontend
│       ├── config.py             # Configuration management
│       ├── logger.py             # Logging setup
│       ├── models.py             # Pydantic models
│       ├── pdf_processor.py     # PDF text extraction
│       ├── lightrag_integration.py  # LightRAG wrapper
│       └── neo4j_client.py      # Neo4j operations
├── pyproject.toml               # Project dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── README.md                    # This file
└── CLAUDE.md                    # Development guide
```

## Development

### Install Development Dependencies

```bash
uv pip install -e ".[dev]"
```

### Code Quality

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

### Running Tests

```bash
pytest
```

## Troubleshooting

### Common Issues

#### Neo4j Connection Failed
- Verify Neo4j is running: `docker ps` or check Neo4j service
- Check URI and credentials in `.env`
- Ensure ports 7474 and 7687 are not blocked

#### LLM API Errors
- Verify LLM server is running
- Check the base URL in `.env`
- Ensure the model names match your loaded models
- Test API manually: `curl http://127.0.0.1:1234/v1/models`

#### OCR Not Working
- Install Tesseract: Follow installation instructions above
- Install Poppler: Required for PDF to image conversion
- Check logs for specific OCR errors

#### Out of Memory
- Process smaller PDFs
- Reduce batch size in LightRAG configuration
- Use a lighter LLM model
- Increase system memory allocation

### Logs

Application logs are written to:
- Console output (stdout)
- `app.log` file in the working directory

Adjust log level in `.env`:
```bash
LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Configuration Reference

See `.env.example` for all available configuration options.

### Key Settings

- `LLM_BASE_URL`: Base URL for your local LLM API
- `LLM_MODEL_NAME`: Model to use for text processing
- `LLM_EMBEDDING_MODEL`: Model to use for embeddings
- `NEO4J_URI`: Neo4j connection URI
- `UPLOAD_DIR`: Directory for uploaded PDFs (default: `./uploads`)
- `WORKING_DIR`: LightRAG working directory (default: `./working`)

## Performance Tips

1. **Use a fast LLM**: Choose models optimized for your hardware
2. **GPU acceleration**: Ensure your LLM server uses GPU if available
3. **Batch processing**: Process multiple PDFs sequentially
4. **Neo4j tuning**: Configure Neo4j memory settings for large graphs
5. **PDF preprocessing**: Clean and optimize PDFs before upload

## Security Considerations

- **API access**: The FastAPI backend accepts connections from any origin (CORS: `*`). Restrict this in production.
- **File uploads**: Implement file size limits and validation in production
- **Neo4j credentials**: Use strong passwords and restrict network access
- **LLM data**: Local LLM ensures your data doesn't leave your system

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run code quality checks
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/pdf-knowledge-graph/issues)
- Documentation: See CLAUDE.md for development guide

## Acknowledgments

- [LightRAG](https://github.com/HKUDS/LightRAG) - Knowledge graph extraction framework
- [Neo4j](https://neo4j.com/) - Graph database platform
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Streamlit](https://streamlit.io/) - Interactive web apps
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing library
