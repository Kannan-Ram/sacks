# Knowledge Graph Quality Improvements

## Issues Fixed

### 1. Database Separation ✅

**Problem:** SAC entities mixed with old test data in `chunk-entity-relation` database.

**Solution:**
- Created separate `sac-kg` Neo4j database for SAC knowledge graph
- Updated configuration to use `settings.active_neo4j_database`
- SAC mode now automatically uses `sac-kg` database
- General mode uses `chunk-entity-relation` database

**Configuration:**
```env
SAC_NEO4J_DATABASE=sac-kg  # Separate database for SAC
```

### 2. [THINK] Reasoning Contamination ✅

**Problem:** Model reasoning steps appearing in entity descriptions:
```
Description: [THINK]Okay, I need to synthesize a list of descriptions...
```

**Solution:**
- Added regex filters in LLM function to remove [THINK] tags
- Filters both `[THINK]...[/THINK]` blocks and standalone `[THINK]` paragraphs
- Cleans up extra whitespace after removal

**Impact:** Clean, professional entity descriptions without reasoning artifacts.

### 3. Generic Relationship Types ⚠️

**Problem:** All relationships showing as `DIRECTED` instead of meaningful types like `CONTAINS`, `REQUIRES`, `DEPENDS_ON`.

**Root Cause:** Mistral-Small's output format may not match LightRAG's expected entity/relationship extraction format precisely.

**Planned Solutions:**
1. **Test DeepSeek-R1** (Iteration 1): Better reasoning → better structured output
2. **Post-processing**: Add script to infer relationship types from descriptions
3. **Custom prompts**: Fine-tune extraction prompts for SAC domain

## Testing Plan

### Baseline (Current - Mistral-Small + nomic-embed)
- Model: mistralai/magistral-small-2509
- Embeddings: text-embedding-nomic-embed-text-v1.5
- Database: sac-kg
- **Expected**: Mixed quality, generic relationships

### Iteration 1 (DeepSeek-R1 + nomic-embed)
- Model: deepseek-r1-0528-qwen3-8b (reasoning model)
- Embeddings: text-embedding-nomic-embed-text-v1.5
- Database: sac-kg (will clear and rebuild)
- **Expected**: Better entity extraction, more specific relationships

### Iteration 2 (DeepSeek-R1 + Qwen3-Embedding)
- Model: deepseek-r1-0528-qwen3-8b
- Embeddings: Qwen3-Embedding-4B
- Database: sac-kg (will clear and rebuild)
- **Expected**: Best semantic understanding and embedding quality

## Usage After Fixes

### Query SAC Database Directly

```cypher
// All SAC entities
MATCH (n)
RETURN n.entity_id, n.entity_type, n.description
LIMIT 25

// Find feature dependencies
MATCH (f {entity_id: 'metric_list'})-[r]->(dep)
RETURN f.entity_id, type(r), r.description, dep.entity_id

// Feature relationship chains
MATCH path = (f {entity_id: 'metric_list'})-[*1..3]->(deps)
RETURN path
```

### Check Relationship Types

```cypher
// Count relationship types
MATCH ()-[r]->()
RETURN type(r) as rel_type, count(*) as count
ORDER BY count DESC

// If still seeing DIRECTED, check relationship descriptions
MATCH ()-[r:DIRECTED]->()
RETURN r.description
LIMIT 10
```

## Recommendations for GraphRAG Test Generation

1. **Use Cypher queries** directly on Neo4j for precise dependency extraction
2. **Relationship descriptions** contain valuable info even if type is generic
3. **Combine multiple relationship types** to build complete dependency picture
4. **Validate with Neo4j Browser** before using in test generation

Example test generation query:
```python
# Get all requirements for Metric List feature
cypher = """
MATCH (f {entity_id: 'metric_list'})-[r]->(req)
WHERE type(r) IN ['DIRECTED', 'REQUIRES', 'DEPENDS_ON']
  AND r.description CONTAINS 'require'
  OR r.description CONTAINS 'need'
  OR r.description CONTAINS 'must'
RETURN req.entity_id, req.description, r.description
"""
```

## Next Steps After Baseline Test

1. Clear sac-kg database
2. Switch to DeepSeek-R1 in LM Studio
3. Re-process same Metric List PDF
4. Compare entity/relationship quality
5. Document differences
6. Repeat with Qwen3-Embedding
7. Choose optimal configuration for production use
