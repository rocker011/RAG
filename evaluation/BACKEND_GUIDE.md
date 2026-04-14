# Evaluation Backends

This repository now supports two inference backends for evaluation-time LLM calls:

- `realtime`: OpenAI-compatible online requests
- `batch`: Qiniu AI Token batch inference jobs

## Scope

The dual backend currently applies to:

- `Step3`: `evaluation/get_generation.py`
- `Step4`: `evaluation/get_score.py` (`Gen` metric judge only)

`Step1` and `Step2` are unchanged and still use the existing realtime query/indexing path.

## Why split by stage

- `Step3` answer generation benefits from a stable chat model.
- `Step4` judge scoring is the slowest part and is the best candidate for batch submission.

To keep experiments persuasive, the code separates **generation model** and **judge model** from the transport backend.
That means we can keep the same model choice whether we use realtime or batch.

## Recommended model policy

Default models are:

- generation: `deepseek-v3`
- judge: `deepseek-r1`

Rationale:

- `deepseek-v3` is a strong general chat model and is supported by Qiniu batch inference.
- `deepseek-r1` is stronger for rubric-based judging and is also supported by batch inference.

If you want maximum comparability across runs, keep these model settings fixed for **all** methods.

## Runtime configuration

### Global backend switch

- `HGRAG_INFERENCE_BACKEND=realtime|batch`

### Per-stage backend override

- `HGRAG_GENERATION_BACKEND=realtime|batch`
- `HGRAG_JUDGE_BACKEND=realtime|batch`

### Model selection

- `HGRAG_GENERATION_MODEL=deepseek-v3`
- `HGRAG_JUDGE_MODEL=deepseek-r1`

### Realtime worker knobs

- `HGRAG_GENERATION_WORKERS`
- `HGRAG_SCORE_WORKERS`

### Batch worker knobs

- `HGRAG_BATCH_POLL_INTERVAL_SECONDS`
- `HGRAG_BATCH_TIMEOUT_SECONDS`

## Batch-specific requirement

Qiniu batch inference requires `input_files_url` to be a **publicly accessible JSONL URL**.

The code supports this with:

- `HGRAG_BATCH_INPUT_URL_TEMPLATE`
- optional `HGRAG_BATCH_PUBLIC_ROOT`

### Required

`HGRAG_BATCH_INPUT_URL_TEMPLATE` example:

```powershell
$env:HGRAG_BATCH_INPUT_URL_TEMPLATE='https://your-public-host/hgrag-batch/{task_name}/{filename}'
```

Supported placeholders:

- `{task_name}`
- `{filename}`
- `{relative_path}`

### Optional

`HGRAG_BATCH_PUBLIC_ROOT` example:

```powershell
$env:HGRAG_BATCH_PUBLIC_ROOT='D:\public\hgrag-batch'
```

If this is set, the batch input JSONL file will be copied to:

- `{HGRAG_BATCH_PUBLIC_ROOT}\{task_name}\input.jsonl`

This is useful when that folder is already served or synced to your public URL host.

## Example usage

### Fully realtime

```powershell
$env:HGRAG_INFERENCE_BACKEND='realtime'
$env:HGRAG_GENERATION_MODEL='deepseek-v3'
$env:HGRAG_JUDGE_MODEL='deepseek-r1'
python get_generation.py --data_sources hypertension --methods HyperGraphRAG,SWHC
python get_score.py --data_source hypertension --method HyperGraphRAG
```

### Realtime generation + batch judge

```powershell
$env:HGRAG_GENERATION_BACKEND='realtime'
$env:HGRAG_JUDGE_BACKEND='batch'
$env:HGRAG_GENERATION_MODEL='deepseek-v3'
$env:HGRAG_JUDGE_MODEL='deepseek-r1'
$env:HGRAG_BATCH_INPUT_URL_TEMPLATE='https://your-public-host/hgrag-batch/{task_name}/{filename}'
python get_generation.py --data_sources hypertension --methods GraphRAG
python get_score.py --data_source hypertension --method GraphRAG
```

### Fully batch for Step3 and Step4

```powershell
$env:HGRAG_INFERENCE_BACKEND='batch'
$env:HGRAG_GENERATION_MODEL='deepseek-v3'
$env:HGRAG_JUDGE_MODEL='deepseek-r1'
$env:HGRAG_BATCH_INPUT_URL_TEMPLATE='https://your-public-host/hgrag-batch/{task_name}/{filename}'
python get_generation.py --data_sources hypertension --methods StandardRAG
python get_score.py --data_source hypertension --method StandardRAG
```

## Output layout

Batch jobs are staged under:

- `evaluation/batch_jobs/<timestamp>_<task_name>/`

Typical files:

- `input.jsonl`
- `output.jsonl`
- `job_detail.json`

These files help debug failed jobs and preserve exact prompts used for batch submission.

## Current limitation

The batch backend assumes you already have a way to expose the staged JSONL file as a public URL.
The code prepares the file and submits the job, but it does not include a cloud uploader yet.

If later needed, the next extension is straightforward:

- add a Qiniu object-storage uploader
- return `input_files_url` automatically
- keep the rest of the evaluation pipeline unchanged
