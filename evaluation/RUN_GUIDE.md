# HyperGraphRAG Evaluation Run Guide

## Environment
- Activate env: `conda activate hypergraphrag`
- Working directory: `D:\PythonProjects\HyperGraphRAG\evaluation`
- API config file: `D:\PythonProjects\HyperGraphRAG\api_config.txt`
- Current stable mode: remote LLM + local embedding (`local:Qwen/Qwen3-Embedding-0.6B`)

## Recommended Safe Concurrency
- Step1 build graph:
  - `HGRAG_INSERT_LLM_MAX_ASYNC=8`
  - `HGRAG_ENTITY_SUMMARY_LLM_MAX_ASYNC=1`
- Step2 retrieve knowledge:
  - `HGRAG_QUERY_CONCURRENCY=2`
- Step3 generation:
  - `HGRAG_GENERATION_WORKERS=2`
- Step4 scoring:
  - `HGRAG_SCORE_WORKERS=2`
  - `HGRAG_GEN_METRIC_WORKERS=1`

## Step1 Build Graph
```powershell
conda activate hypergraphrag
cd /d D:\PythonProjects\HyperGraphRAG\evaluation
set PYTHONIOENCODING=utf-8
set HGRAG_INSERT_LLM_MAX_ASYNC=8
set HGRAG_ENTITY_SUMMARY_LLM_MAX_ASYNC=1
python script_insert.py --cls hypertension
```
Expected outputs in `expr/hypertension`:
- `graph_chunk_entity_relation.graphml`
- `kv_store_full_docs.json`
- `kv_store_text_chunks.json`
- `vdb_chunks.json`
- `vdb_entities.json`
- `vdb_hyperedges.json`

## Step2 Retrieve Knowledge
```powershell
set HGRAG_QUERY_CONCURRENCY=2
python script_hypergraphrag.py --data_source hypertension
```
Expected output:
- `results/HyperGraphRAG/hypertension/test_knowledge.json`

## Step3 Generate Answers
```powershell
set HGRAG_GENERATION_WORKERS=2
python get_generation.py --data_sources hypertension --methods HyperGraphRAG
```
Expected output:
- `results/HyperGraphRAG/hypertension/test_generation.json`

## Step4 Score
```powershell
set HGRAG_SCORE_WORKERS=2
set HGRAG_GEN_METRIC_WORKERS=1
python get_score.py --data_source hypertension --method HyperGraphRAG
```
Expected outputs:
- `results/HyperGraphRAG/hypertension/test_result.json`
- `results/HyperGraphRAG/hypertension/test_score.json`

## Step5 Split Report
```powershell
python see_score.py --data_source hypertension --method HyperGraphRAG
```
Expected console output:
- binary / n-ary / overall score table

## Common Failure Modes
- `429 Too Many Requests`:
  - lower `HGRAG_QUERY_CONCURRENCY`, `HGRAG_GENERATION_WORKERS`, or `HGRAG_SCORE_WORKERS`
  - keep `HGRAG_ENTITY_SUMMARY_LLM_MAX_ASYNC=1`
- Empty graph or empty vdb files:
  - check `api_config.txt`
  - inspect `hypergraphrag.log`
- Slow first run of Step4:
  - `sup-simcse-roberta-large` downloads on first use
- Windows encoding issues:
  - keep `PYTHONIOENCODING=utf-8`

## What To Check After Each Step
- Step1: graph and vdb files are non-empty
- Step2: `test_knowledge.json` has 512 rows and every row has non-empty `knowledge`
- Step3: `test_generation.json` has 512 rows and no `[ERROR]` generation
- Step4: `test_score.json` exists and prints overall metrics
