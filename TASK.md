# TASK.md

Last updated: `2026-04-29`

## Current phase
We are in the **research TODO refinement + paper-facing method strengthening** phase.

## Status snapshot
- baseline implementation for the current main stack is complete
- the current fair no-judge `hypertension` matrix is available for:
  - `NaiveGeneration`
  - `StandardRAG`
  - `HybridRAG`
  - `GraphRAG`
  - `HyperGraphRAG`
  - `SWHC`
- official `GraphRAG` is already integrated into the shared evaluation chain
- `BM25` still only has a partial lower-bound no-judge result after the earlier `402 Insufficient Balance`
  - treat it as a maintenance item, not the current main task
- the current comparison note lives at:
  - `docs/results/hypertension_no_judge_comparison_2026-04-18.md`

## Goal
Use the completed baseline stack to answer the remaining **method-design and paper-story** questions around `SWHC`, instead of continuing baseline plumbing work.

## Stable reference point
- treat the current six-method `hypertension` no-judge table as the default reference snapshot
- keep `SWHC` as a **query-time evidence assembly** method on top of `HyperGraphRAG`
- keep API / model defaults sourced from `api_config.txt`
- current verified remote API base: `https://ai.butel.com/api`
- current verified main chat model: `gpt-5.4-mini-hy`
- by default, judge model follows the same configured chat model unless `HGRAG_JUDGE_MODEL` overrides it
- keep local `Qwen/Qwen3-Embedding-0.6B` as the default embedding
- keep `LLM judge` off for intermediate work unless a task explicitly requires it

If a task changes the `SWHC` formula, semantic weighting, objective, or solver behavior, say explicitly that older `SWHC` results may no longer be directly comparable.

## Active priorities
### P0
1. Formula refinement:
   - decide how to handle baseline methods that do not naturally expose edge confidence `conf` in cross-method comparisons
   - clarify whether `SWHC`-specific confidence should be removed, approximated, or replaced

2. Formula refinement:
   - test replacing token-count cost with the number of retrieved entities
   - or provide a stronger justification for the constant `256` in the current token-cost normalization

3. Method strengthening:
   - prepare a cleaner answer to: why optimize on top of **HyperGraphRAG** instead of standard **GraphRAG**
   - make the method story more defensible in paper writing

4. Method strengthening:
   - discuss how to make the method more genuinely hypergraph-aware
   - especially revisit distance design between entity nodes and hyperedge nodes

### P1
5. Research evaluation expansion:
   - compare against stronger and newer GraphRAG-style baselines only if they are needed for the paper story
   - prioritize targeted comparisons over broad baseline integration work

6. Dataset expansion:
   - finish the remaining planned datasets
   - extend the comparison beyond the current `hypertension` focus
   - move toward:
     - `HotpotQA`
     - `2WikiMultiHopQA`
     - `MuSiQue`
     - `PopQA`

### Maintenance only
7. `BM25` completion:
   - resume the interrupted `BM25` no-judge run only if an official table still needs it
   - do not let this block current research TODO work

## Working rules for this phase
- Do not reopen completed baseline implementation work unless it is necessary for a specific research question
- Prefer analysis, ablation, and targeted reruns over broad expensive reruns
- Keep comparisons fair across methods and datasets
- Do not silently change preprocessing, evaluation definitions, dataset splits, or scoring behavior
- Intermediate experiments should still default to `LLM judge off`
- When a research change may invalidate older results, say so before proceeding

## Working defaults
### Runtime
- API / model defaults: read from `api_config.txt`
- Current verified API base: `https://ai.butel.com/api`
- Current verified main model: `gpt-5.4-mini-hy`
- Judge model: by default follows `api_config.txt`; override with `HGRAG_JUDGE_MODEL` if a separate judge is needed
- Embedding: local `Qwen/Qwen3-Embedding-0.6B`

### Scoring
For intermediate experiments:
- `HGRAG_ENABLE_LLM_JUDGE=false`

### SWHC defaults
Treat the following as the current `SWHC` reference setup:

- $\alpha = 1.0$
- $\beta = 0.15$
- $\gamma = 0.05$
- $\varepsilon = 0.05$
- $c_{\text{hop}} = 0.25$

## Checks
Typical no-judge scoring command:

```powershell
cd /d D:\PythonProjects\HyperGraphRAG\evaluation
set HGRAG_ENABLE_LLM_JUDGE=false
python get_score.py --data_source <dataset> --method <method> --enable_llm_judge false
```

Typical resume-friendly generation command:

```powershell
cd /d D:\PythonProjects\HyperGraphRAG\evaluation
set HGRAG_GENERATION_WORKERS=4
set HGRAG_OPENAI_TIMEOUT_SECONDS=180
python get_generation.py --data_sources <dataset> --methods <method>
```

Behavior note:
- if `results/<Method>/<dataset>/test_generation.json` already exists, `get_generation.py` now skips successful samples and only regenerates missing or `[ERROR]` samples
- Step3 writes `generation_usage` plus flattened consumed-token fields when the backend returns usage
- Step4 writes `avg_consumed_tokens` to `test_score.json`
- because `GraphRAG` now points to the official Microsoft implementation, older internal `GraphRAG-local` style outputs are legacy results and not directly comparable
