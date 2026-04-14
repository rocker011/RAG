# Evaluation Structure

This folder is the experiment workspace for all baselines and the proposed method.

## Current structure

```text
evaluation/
├─ logs/                       # historical run logs by dataset and method
├─ debug/                      # one-off debug and recovery scripts
├─ methods/                    # method implementations used by wrapper scripts
│  ├─ common.py
│  ├─ hypergraphrag.py
│  ├─ swhc.py
│  ├─ graphrag.py
│  ├─ standardrag.py
│  ├─ naivegeneration.py
│  └─ README.md
├─ hypergraphrag/              # evaluation-time package fork / patched baseline code
├─ contexts/                   # raw corpora for graph construction (gitignored)
├─ datasets/                   # QA benchmark files (gitignored)
├─ expr/                       # built indexes / graph caches (gitignored)
├─ results/                    # method outputs and scores (gitignored)
├─ get_generation.py           # Step3
├─ get_score.py                # Step4
├─ see_score.py                # Step5
├─ inference_backend.py        # realtime / batch dual backend
└─ script_*.py                 # compatibility wrappers
```

## Dataset convention

Use this convention for every dataset:

```text
evaluation/
├─ contexts/
│  ├─ hypertension_contexts.json
│  ├─ agriculture_contexts.json
│  └─ <dataset>_contexts.json
├─ datasets/
│  ├─ hypertension/
│  │  └─ questions.json
│  ├─ agriculture/
│  │  └─ questions.json
│  └─ <dataset>/
│     └─ questions.json
```

### Questions format

Each `questions.json` item should keep the current schema:

- `question`
- `golden_answers`
- `context`
- `nary`
- `nhop`

## Method result convention

Each method writes to:

```text
evaluation/results/<Method>/<dataset>/
├─ test_knowledge.json
├─ test_generation.json
├─ test_result.json
└─ test_score.json
```

Recommended method names:

- `NaiveGeneration`
- `BM25`
- `StandardRAG`
- `HybridRAG`
- `GraphRAG`
- `LightRAG`
- `PathRAG`
- `HyperGraphRAG`
- `SWHC`

## Planned method file convention

For every new baseline, add:

1. implementation file under `evaluation/methods/`
2. optional compatibility wrapper `evaluation/script_<method>.py`
3. results under `evaluation/results/<Method>/`

Recommended future filenames:

- `evaluation/methods/bm25.py`
- `evaluation/methods/hybrid_rag.py`
- `evaluation/methods/lightrag.py`
- `evaluation/methods/pathrag.py`

## Logs and runs

Current historical logs are now archived under dataset/method folders.
Recommended layout for run artifacts:

```text
evaluation/logs/
└─ <dataset>/
   └─ <method>/
      ├─ step2.out.log
      ├─ step3.out.log
      └─ step4.out.log
```

Example used in this repo:

```text
evaluation/logs/hypertension/HyperGraphRAG/
├─ step1_20260329_1202.out.log
├─ step1_20260329_1202.err.log
├─ step2_20260408_01.out.log
└─ ...
```

## Debug scripts

One-off debugging or recovery scripts should not live in `evaluation/` root anymore.
Use:

```text
evaluation/debug/
└─ <dataset>/
   └─ <script>.py
```

Example:

```text
evaluation/debug/hypertension/run_step1_debug.py
```
