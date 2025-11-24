# SAP Analytics Cloud (SAC) Knowledge Graph

This branch is configured for extracting knowledge graphs from SAP Analytics Cloud product documentation.

## Setup for SAC Mode

### 1. Configuration

The `.env` file has been configured with `USE_SAC_MODE=true` to enable SAC-specific optimizations:

```bash
# SAC Mode enabled
USE_SAC_MODE=true
SAC_WORKING_DIR=./working_sac
SAC_WORKSPACE=sac-product-docs
```

### 2. Optimizations for Product Documentation

**Smaller, Focused Chunks:**
- Chunk size: 600 tokens (vs 800 for general docs)
- Overlap: 100 tokens (vs 50 for general docs)
- Better for extracting precise feature definitions and relationships

**Separate Storage:**
- Working directory: `./working_sac/`
- Workspace namespace: `sac-product-docs`
- Keeps SAC data isolated from general knowledge graphs

### 3. Document Organization

Place your SAC documentation PDFs in:
```
sac_docs/
└── metric_list/          # Metric List feature documentation
    ├── public/           # Public SAP documentation (optional)
    └── internal/         # Internal dev documentation (optional)
```

## Usage

### Processing SAC Documentation

1. **Start the application:**
   ```bash
   # Terminal 1 - Backend
   source .venv/bin/activate
   python -m src.pdf_knowledge_graph.main

   # Terminal 2 - Frontend
   source .venv/bin/activate
   streamlit run src/pdf_knowledge_graph/app.py
   ```

2. **Upload PDFs via Streamlit UI** (http://localhost:8501)
   - Upload Metric List user guides
   - Upload developer documentation
   - Upload API documentation

3. **View Knowledge Graph in Neo4j Browser** (http://localhost:7474)
   - Database: `chunk-entity-relation`
   - Data is namespaced under workspace: `sac-product-docs`

### Expected Entity Types for SAC

- **Feature**: Metric List, Watchlist, Stories, Dashboards
- **Component**: Metrics, KPIs, Widgets, Charts, Filters
- **DataSource**: Models, Live Connections, Import Models
- **Function**: Calculations, Formulas, Scripts, APIs
- **Permission**: User roles, Sharing settings, Access levels
- **Integration**: SAP BW, SAP S/4HANA, Excel, APIs

### Expected Relationship Types

- **contains**: Feature contains Components
- **requires**: Feature A requires Feature B
- **supports**: Feature supports DataSource
- **integrates_with**: Integration relationships
- **replaced**: Legacy feature replaced by new feature
- **depends_on**: Dependencies between features

## Querying SAC Knowledge Graph

### Find all features:
```cypher
MATCH (n)
WHERE n.entity_type = 'feature' OR toLower(n.entity_id) CONTAINS 'metric list'
RETURN n.entity_id, n.description
```

### Find Metric List and its components:
```cypher
MATCH (ml)
WHERE toLower(ml.entity_id) CONTAINS 'metric list'
OPTIONAL MATCH (ml)-[r]-(related)
RETURN ml, r, related
LIMIT 50
```

### Find feature dependencies:
```cypher
MATCH (f1)-[r]->(f2)
WHERE r.description CONTAINS 'require' OR r.description CONTAINS 'depend'
RETURN f1.entity_id as from,
       type(r) as relationship,
       r.description as details,
       f2.entity_id as to
```

## Tips for SAC Documentation

**Best Practices:**
- ✅ Include both user guides and developer documentation
- ✅ Process related features together (e.g., Metric List + Dashboard + Story)
- ✅ Include API documentation for integration details
- ✅ Mix public and internal docs for complete picture

**What Extracts Well:**
- ✅ Feature descriptions and capabilities
- ✅ Component lists and hierarchies
- ✅ Integration points and data sources
- ✅ Requirements and dependencies
- ✅ Workflow sequences

**May Need Review:**
- ⚠️ Exact UI navigation steps
- ⚠️ Screenshot-heavy documentation (text extraction only)
- ⚠️ Version-specific details (may mix versions)

## Switching Between General and SAC Mode

To switch back to general mode:
```bash
# In .env file
USE_SAC_MODE=false
```

Restart the backend for changes to take effect.

## Privacy Note

All processing happens locally:
- ✅ PDFs processed on your machine
- ✅ LLM runs via local LM Studio
- ✅ Data stored in local Neo4j
- ✅ **No data sent to external services**

Perfect for internal/confidential SAC documentation!
