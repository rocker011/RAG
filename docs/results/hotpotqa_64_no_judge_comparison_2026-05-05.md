# HotPotQA_64 No-Judge Baseline Comparison

Updated: `2026-05-05`

## Scope

- Dataset: `hotpotqa_64`
- Source: Hugging Face `hotpotqa/hotpot_qa`
- Config / split: `distractor / validation`
- Sample: first `64` rows
- Context conversion: `bundle`
  - one document per QA sample
  - each document contains the sample's provided distractor paragraphs
- Scoring mode: `LLM judge off`
- Shared generation model: `gpt-5.4-mini-hy` via current `api_config.txt`
- HyperGraphRAG embedding: local `Qwen/Qwen3-Embedding-0.6B`
- Official GraphRAG embedding: Ollama OpenAI-compatible `qwen3-embedding:0.6b`
- `GraphRAG` refers to the Microsoft official GraphRAG implementation.

## Fairness Check

All six rows satisfy the current no-judge comparability requirements:

- `64 / 64` generations completed
- `0 / 64` final generation errors
- `64 / 64` generation token-usage records
- shared Step3 / Step4 pipeline
- `LLM judge` disabled

One `NaiveGeneration` sample initially triggered provider `invalid_prompt` filtering. It was regenerated with an explicit benign-benchmark safety preface, and token usage was recorded for the regenerated sample.

## Overall Results

| Method | EM | F1 | R-Sim | Avg Context Tokens | Avg Consumed Tokens | Generation Errors | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| NaiveGeneration | 14.06 | 32.34 | 0.00 | 0.00 | 189.17 | 0 | Retrieval-free floor; one policy false positive regenerated with safety preface |
| StandardRAG | 40.62 | 62.07 | 61.57 | 11467.70 | 11656.72 | 0 | Dense chunk retrieval |
| HybridRAG | 37.50 | 60.94 | 60.28 | 11473.00 | 11661.14 | 0 | `BM25 + Dense` flat retrieval |
| GraphRAG | 35.94 | 55.10 | 68.01 | 5121.73 | 5311.81 | 0 | Microsoft official GraphRAG, standard indexing, local context |
| HyperGraphRAG | 43.75 | 66.56 | 68.38 | 17347.72 | 17531.95 | 0 | Highest EM/F1, highest answer-generation token use |
| SWHC | 39.06 | 61.20 | 67.30 | 2844.41 | 3036.39 | 0 | Most compact structured method; not the top F1 row on this pilot |

## Build / Index Notes

HyperGraphRAG Step1 completed under `gpt-5.4-mini-hy` without using a fallback model:

- documents: `64`
- chunks: `120`
- graph nodes: `10433`
- graph edges: `10195`

Official GraphRAG indexing completed after adding a content-filter robustness patch in the integration layer:

- documents: `64`
- text units: `110`
- entities: `4158`
- relationships: `4204`
- communities: `571`
- community reports: `571`
- successful final workflow set: `create_base_text_units`, `create_final_documents`, `extract_graph`, `finalize_graph`, `extract_covariates`, `create_communities`, `create_final_text_units`, `create_community_reports`, `generate_text_embeddings`

The unpatched official GraphRAG run failed during `extract_graph` because one `gpt-5.4-mini-hy` description-summary prompt was rejected by provider content filtering. The patch keeps normal model calls unchanged and only falls back to deterministic local description concatenation/truncation for the filtered summary.

Recorded successful official GraphRAG indexing usage:

- chat model responses: `2046`
- chat cache hits: `1079`
- chat total tokens: about `3,872,004`
- local embedding responses: `333`
- local embedding prompt tokens: about `773,009`

## Main Findings

1. `HyperGraphRAG` is the strongest exact-answer row on this pilot.
   - It leads on EM and F1: `43.75 / 66.56`.
   - The cost is high: `17531.95` average consumed tokens, the largest in the table.

2. `SWHC` is very token efficient but not the top answer-quality row here.
   - It reaches `61.20` F1 and `67.30` R-Sim with only `3036.39` average consumed tokens.
   - Compared with `HyperGraphRAG`, it loses `5.36` F1 but uses about `17%` of the answer-generation tokens.
   - This differs from the `hypertension` table, where `SWHC` is the best overall row.

3. Flat retrieval is unusually competitive under `bundle` conversion.
   - `StandardRAG` and `HybridRAG` both exceed `60` F1.
   - In `bundle` mode, each QA sample's distractor context is kept together as one document, so dense retrieval can often retrieve a near-complete evidence bundle.
   - This setting is useful as a smoke test, but may be generous to flat chunk retrieval.

4. Official `GraphRAG` is compact and semantically strong, but lower on exact answers.
   - It has `68.01` R-Sim with much lower answer-generation tokens than `HyperGraphRAG`.
   - Its F1 is lower than `StandardRAG`, `HybridRAG`, `HyperGraphRAG`, and `SWHC`.

5. `NaiveGeneration` is not a trivial baseline on HotPotQA_64.
   - It gets `32.34` F1 from model prior alone.
   - Retrieval still matters substantially: every retrieval method improves over it by at least `22.76` F1 points.

## Practical Reading

For this pilot:

`HyperGraphRAG` > `StandardRAG` > `SWHC` > `HybridRAG` > `GraphRAG` > `NaiveGeneration` on F1.

The main research signal is not the same as the `hypertension` snapshot. `SWHC` remains the most compact structured method, but `HyperGraphRAG` wins raw EM/F1 on this small `bundle` HotPotQA setting. Before treating this as a paper-level result, run either a larger `HotPotQA` sample or a stricter title-level corpus construction.

## Caveats

1. This is a `64`-sample pilot, not a final HotPotQA result.
2. The `bundle` corpus construction is intentionally compact and may be easier than title-level retrieval.
3. Results use `gpt-5.4-mini-hy`; they should not be mixed with the `2026-04-18` `hypertension` table, which used DeepSeek official API / `deepseek-chat`.
4. The official GraphRAG content-filter patch changes robustness behavior for rejected summary prompts. It does not change the model or use a fallback model, but it should be reported with this run.
5. No `SWHC` formula, semantic weighting, objective, or solver behavior was changed.
