# SAC Knowledge Graph-Grounded Chatbot

An AI-powered testing assistant for SAP Analytics Cloud (SAC) that generates contextually accurate test scenarios grounded by a Neo4j knowledge graph.

## Overview

This chatbot uses:
- **Neo4j Knowledge Graph**: 600+ SAC entities and 419+ relationships
- **Local LLM**: OpenAI-compatible API (LM Studio, Ollama, etc.)
- **Streamlit UI**: Interactive chat interface
- **RAG Pattern**: Retrieval-Augmented Generation for grounded responses

## Features

✅ **Knowledge Graph-Grounded Responses**: All responses are grounded by actual SAC feature relationships
✅ **Test Scenario Generation**: Create exploratory, functional, and integration test scenarios
✅ **Feature Exploration**: Understand SAC features and their relationships
✅ **Interactive Chat**: Clean, user-friendly Streamlit interface
✅ **Context Transparency**: See the knowledge graph context used for each response
✅ **Quick Actions**: Pre-built queries for common testing needs

## Architecture

```
User Query → Keyword Extraction → Neo4j KG Search → Context Building → LLM Prompt → Grounded Response
```

### Components

1. **`kg_context_retriever.py`**: Neo4j knowledge graph query and context retrieval
2. **`sac_chatbot_service.py`**: LLM integration and response generation
3. **`sac_chatbot_ui.py`**: Streamlit chat interface

## Prerequisites

- Python 3.8+
- Neo4j database with `sac-top-kg` loaded (see `load_kg_to_neo4j.py`)
- Local LLM server with OpenAI-compatible API (LM Studio, Ollama, etc.)

## Installation

1. **Ensure Neo4j is running** with the SAC knowledge graph:
   ```bash
   # If you haven't loaded the KG yet
   python load_kg_to_neo4j.py
   ```

2. **Start your local LLM server** (e.g., LM Studio on port 1234)

3. **Configure environment variables** (already in `.env`):
   ```bash
   LLM_BASE_URL=http://127.0.0.1:1234/v1
   LLM_MODEL_NAME=openai/gpt-oss-20b
   NEO4J_URI=bolt://127.0.0.1:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=Password1
   ```

## Usage

### Start the Chatbot UI

```bash
streamlit run sac_chatbot_ui.py
```

The chatbot will open in your browser at `http://localhost:8501`

### Example Queries

**Test Scenario Generation:**
- "Generate an exploratory test scenario for Geo Map widget"
- "Create integration test cases for Story with Chart and Table widgets"
- "Generate test scenarios for Data Actions in Planning"

**Feature Exploration:**
- "What are the relationships between Story and Canvas Pages?"
- "Explain the Geo Map widget and its capabilities"
- "What features support Planning?"

**Testing Guidance:**
- "What should I test for R Visualization widget?"
- "Create edge case tests for Table widget"
- "Integration points between Calendar and Data Actions"

### Using the Python API

You can also use the chatbot programmatically:

```python
from sac_chatbot_service import SACChatbot

# Initialize chatbot
chatbot = SACChatbot()

# Generate response
result = chatbot.generate_response(
    "Generate an exploratory test scenario for Geo Map"
)

print(result['response'])
print(result['kg_context'])

# Generate test scenario
scenario = chatbot.generate_test_scenario(
    feature="Geo Map",
    test_type="exploratory"
)

print(scenario)

# Get feature details
details = chatbot.get_feature_details("Geo Map")
print(details)

# Clean up
chatbot.close()
```

## How It Works

### 1. Query Processing
- User submits a question
- Keywords are extracted (e.g., "Geo Map", "test scenario")

### 2. Knowledge Graph Retrieval
- Keywords matched against Neo4j entities
- Related entities and relationships retrieved
- Context built with relationship metadata (confidence, provenance)

### 3. Response Generation
- Knowledge graph context injected into LLM prompt
- System prompt guides the LLM to generate grounded responses
- LLM generates contextually accurate answer

### 4. Response Display
- Response shown to user
- Optional: Knowledge graph context displayed for transparency

## Example Interaction

**User:** "Generate an exploratory test scenario for Geo Map widget"

**Knowledge Graph Context Retrieved:**
```
Geo Map (WidgetType):
  - SUPPORTS → Canvas Pages (0.95, Page 6)
  - SUPPORTS → Responsive Pages (0.95, Page 6)
  - DISPLAYS → Bubble Layer (0.92, Page 6)
  - DISPLAYS → Heat Map Layer (0.92, Page 6)
  - DISPLAYS → Choropleth Layer (0.92, Page 6)
```

**Chatbot Response:**
```
Exploratory Test Scenario: Geo Map Widget

Test Case: Multi-Layer Geo Map Visualization
Objective: Verify Geo Map widget functionality across different page types and layer combinations

Prerequisites:
- Canvas Page with Geo Map widget
- Dataset with geographic dimensions
- Multiple data points for visualization

Test Steps:
1. Add Geo Map widget to Canvas Page
2. Configure Bubble Layer with sales data
3. Add Heat Map Layer for density visualization
4. Switch to Responsive Page and verify widget renders correctly
5. Test Choropleth Layer with regional data
6. Verify interactions between layers
7. Test zoom, pan, and filter operations

Expected Results:
- All layer types display correctly (Bubble, Heat Map, Choropleth)
- Widget works on both Canvas and Responsive pages (Source: Page 6)
- Geographic data renders accurately with proper coordinates
```

## UI Features

### Main Interface
- **Chat Area**: Message history with user/assistant distinction
- **Input Box**: Type queries or use Quick Actions
- **Context Display**: Expandable KG context for each response

### Sidebar
- **Temperature Control**: Adjust creativity (0.0-1.0)
- **Show KG Context**: Toggle context visibility
- **Quick Actions**: Pre-built test scenario buttons
- **Example Queries**: Inspiration for questions
- **Clear Chat**: Reset conversation
- **Stats**: Message count

## Customization

### Adjust LLM Temperature

Higher temperature = more creative responses:
```python
chatbot = SACChatbot(temperature=0.9)  # More creative
chatbot = SACChatbot(temperature=0.3)  # More deterministic
```

### Customize System Prompt

Edit `sac_chatbot_service.py`:
```python
self.system_prompt = """Your custom instructions..."""
```

### Modify Context Retrieval

Edit `kg_context_retriever.py`:
```python
def build_context(self, query: str, max_entities: int = 5):  # Increase entities
    # Custom logic...
```

## Troubleshooting

### LLM Connection Issues
```bash
# Test LLM endpoint
curl http://127.0.0.1:1234/v1/models

# Check .env configuration
cat .env | grep LLM
```

### Neo4j Connection Issues
```bash
# Verify Neo4j is running
curl http://localhost:7474

# Test connection
python -c "from kg_context_retriever import KGContextRetriever; r = KGContextRetriever(); r.close()"
```

### No Context Retrieved
- Ensure knowledge graph is loaded: `python load_kg_to_neo4j.py`
- Check entity names in Neo4j Browser: `MATCH (n:Entity) RETURN n.name LIMIT 25`
- Verify keywords match entity names

## Performance Optimization

### Context Retrieval
- Limit entities retrieved: `build_context(query, max_entities=3)`
- Use direct relationships only (faster than multi-hop)

### LLM Response
- Reduce max_tokens for faster responses
- Use lower temperature for deterministic answers
- Limit chat history: `chat_history[-6:]` (last 3 exchanges)

## Future Enhancements

- [ ] Multi-turn conversation with memory
- [ ] Export test scenarios to CSV/Excel
- [ ] Visualization of KG subgraphs used
- [ ] Custom test templates
- [ ] Batch test generation
- [ ] Integration with test management tools
- [ ] Voice input/output
- [ ] Test execution guidance

## License

Part of the SAC PDF Knowledge Graph project.

## Support

For issues or questions, refer to the main project README or create an issue.

---

**Happy Testing!** 🚀
