# Next Steps: Clean Database and Restart with Fixes

## What Just Happened

The baseline test completed successfully:
- ✅ 92 entities extracted
- ✅ 72 relationships extracted
- ⚠️ Data went to `chunk-entity-relation` (not `sac-kg` as intended)
- ⚠️ [THINK] contamination still present (fixes not applied yet)

## Why Database Separation Didn't Work

LightRAG's Neo4j storage reads database name from environment at import time, not runtime. The fixes we made need the backend to be restarted cleanly.

## Steps to Apply Fixes and Retest

### **Step 1: Stop Current Backend**

```bash
# Kill the running backend
lsof -ti:8000 | xargs kill -9
```

### **Step 2: Clean the Mixed Database**

The current `chunk-entity-relation` database has mixed data. We have two options:

**Option A: Start Fresh (Recommended)**
```bash
# This will clear ALL data from chunk-entity-relation
python clean_database.py
```

**Option B: Keep Old Data, Use New Database**
Just leave the old data in `chunk-entity-relation` and start using `sac-kg` for SAC data.

### **Step 3: Restart Backend with Fixes**

```bash
# Terminal 1 - Backend (with all fixes applied)
source .venv/bin/activate
python -m src.pdf_knowledge_graph.main
```

Look for these log lines to confirm fixes are active:
```
✅ Using Neo4j database: sac-kg
✅ SAC Mode: ENABLED
✅ Workspace: sac-product-docs
```

### **Step 4: Reprocess PDF**

```bash
# Terminal 2 - Frontend
source .venv/bin/activate
streamlit run src/pdf_knowledge_graph/app.py
```

1. Upload the same Metric List PDF again
2. Click "Process PDF"
3. Wait for completion (should take 5-10 minutes)

### **Step 5: Verify in Neo4j Browser**

1. Open http://localhost:7474
2. **Switch database** to `sac-kg` (dropdown at top)
3. Run query:
   ```cypher
   MATCH (n)
   RETURN n
   LIMIT 25
   ```

4. Check for:
   - ✅ Nodes in `sac-kg` database (not `chunk-entity-relation`)
   - ✅ No `[THINK]` in descriptions
   - ⚠️ Relationship types (still might be `DIRECTED`)

### **Step 6: Analyze Baseline Results**

Document the quality:
```cypher
// Count entities and relationships
MATCH (n) RETURN count(n) as entities;
MATCH ()-[r]->() RETURN count(r) as relationships;

// Check for [THINK] contamination
MATCH (n)
WHERE n.description CONTAINS '[THINK]'
RETURN count(n) as think_nodes;

// Check relationship types
MATCH ()-[r]->()
RETURN type(r) as rel_type, count(*) as count
ORDER BY count DESC;

// Sample entities
MATCH (n)
RETURN n.entity_id, n.entity_type, substring(n.description, 0, 100) as desc
LIMIT 10;
```

Save these results as **"Baseline Results - Mistral-Small + nomic-embed"**

## After Baseline is Clean

### **Iteration 1: Switch to DeepSeek-R1**

1. In LM Studio: Load `deepseek-r1-0528-qwen3-8b`
2. Update `.env`:
   ```
   LLM_MODEL_NAME=deepseek-r1-0528-qwen3-8b
   ```
3. Clear `sac-kg` database
4. Clear `working_sac/` directory
5. Reprocess same PDF
6. Compare results with baseline

### **Iteration 2: Switch to Qwen3-Embedding**

1. In LM Studio: Load `Qwen3-Embedding-4B`
2. Update `.env`:
   ```
   LLM_EMBEDDING_MODEL=qwen3-embedding-4b
   ```
3. Clear `sac-kg` database
4. Clear `working_sac/` directory
5. Reprocess same PDF
6. Compare results with Iteration 1

## Comparison Metrics

For each iteration, document:

1. **Entity Quality**
   - Count
   - Diversity (how many different entity_type values)
   - Description quality (presence of [THINK], clarity)
   - Examples of well-extracted vs poorly-extracted entities

2. **Relationship Quality**
   - Count
   - Type diversity (DIRECTED vs specific types like CONTAINS, REQUIRES)
   - Description clarity
   - Examples of well-extracted vs missing relationships

3. **Processing Performance**
   - Time to complete
   - LLM tokens/sec
   - Embedding generation time

4. **GraphRAG Usability**
   - Can you find feature dependencies via Cypher?
   - Are relationships meaningful for test generation?
   - Do descriptions provide sufficient context?

## Files Created

- `IMPROVEMENTS.md` - Summary of issues and fixes
- `NEXT_STEPS.md` - This file (what to do next)
- `check_neo4j.py` - Script to inspect database
- `check_neo4j_detailed.py` - Detailed inspection
- `create_sac_database.py` - Created `sac-kg` database
- `clean_database.py` - (TODO) Clear database script

## Summary

The baseline test gave us data to work with, but the fixes need a clean restart to take effect. Follow the steps above to:
1. Apply database separation fix
2. Apply [THINK] removal fix
3. Test with DeepSeek-R1 for better relationship extraction
4. Compare all three configurations
5. Choose the best setup for production SAC knowledge graph
