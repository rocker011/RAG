import argparse
import json
import os
from pathlib import Path

from tqdm import tqdm

from inference_backend import (
    InferenceRequest,
    get_backend,
    get_generation_backend_kind,
    get_generation_model,
    get_generation_workers,
)

parser = argparse.ArgumentParser()
parser.add_argument('--data_sources', default='hypertension')
parser.add_argument('--methods', default='StandardRAG')
args = parser.parse_args()
methods = args.methods.split(',')
data_sources = args.data_sources.split(',')

backend_kind = get_generation_backend_kind()
backend = get_backend(backend_kind)
generation_model = get_generation_model()
generation_workers = get_generation_workers()
force_regenerate = os.getenv("HGRAG_FORCE_REGENERATE", "").strip().lower() in {"1", "true", "yes", "y", "on"}
GENERATION_PERSIST_FIELDS = (
    'prompt',
    'generation',
    'generation_usage',
    'consumed_prompt_tokens',
    'consumed_completion_tokens',
    'consumed_total_tokens',
)


def build_generation_prompt(sample: dict) -> str:
    return f"""---Role---

You are a helpful assistant responding to questions based on given knowledge.

---Knowledge---

{sample['knowledge']}

---Goal---

Answer the given question.
You must first conduct reasoning inside <think>...</think>.
When you have the final answer, you can output the answer inside <answer>...</answer>.

Output format for answer:
<think>
...
</think>
<answer>
...
</answer>

---Question---

{sample['question']}
"""


def build_requests(data: list[dict], task_name: str, indices: list[int] | None = None) -> list[InferenceRequest]:
    requests = []
    effective_indices = indices if indices is not None else list(range(len(data)))
    for idx, sample in zip(effective_indices, data):
        prompt = build_generation_prompt(sample)
        sample['prompt'] = prompt
        requests.append(
            InferenceRequest(
                custom_id=f"{task_name}-sample-{idx}",
                messages=[{"role": "user", "content": prompt}],
            )
        )
    return requests


def normalize_token_count(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def build_usage_fields(usage: dict | None) -> dict:
    if not isinstance(usage, dict):
        return {
            'generation_usage': None,
            'consumed_prompt_tokens': None,
            'consumed_completion_tokens': None,
            'consumed_total_tokens': None,
        }
    return {
        'generation_usage': usage,
        'consumed_prompt_tokens': normalize_token_count(usage.get('prompt_tokens')),
        'consumed_completion_tokens': normalize_token_count(usage.get('completion_tokens')),
        'consumed_total_tokens': normalize_token_count(usage.get('total_tokens')),
    }


def copy_existing_generation_fields(sample: dict, existing_sample: dict) -> None:
    for field in GENERATION_PERSIST_FIELDS:
        if field in existing_sample:
            sample[field] = existing_sample[field]


def should_regenerate_sample(sample: dict) -> bool:
    if force_regenerate:
        return True
    generation = sample.get('generation')
    if generation is None:
        return True
    if isinstance(generation, str) and generation.strip().startswith("[ERROR]"):
        return True
    return False


def process_method(method: str) -> None:
    for data_source in data_sources:
        print(f"[DEBUG] {method} {data_source}")
        data_dir = Path(f"results/{method}/{data_source}/test_knowledge.json")
        with data_dir.open(encoding='utf-8') as f:
            data = json.load(f)

        task_name = f"generation-{method}-{data_source}"
        generation_path = Path(f"results/{method}/{data_source}/test_generation.json")
        if generation_path.exists():
            with generation_path.open(encoding='utf-8') as f:
                existing_data = json.load(f)
            for sample, existing_sample in zip(data, existing_data):
                copy_existing_generation_fields(sample, existing_sample)

        pending_indices = [idx for idx, sample in enumerate(data) if should_regenerate_sample(sample)]
        pending_samples = [data[idx] for idx in pending_indices]
        print(
            f"[DEBUG] {method} {data_source} pending_generations={len(pending_indices)} "
            f"force_regenerate={force_regenerate}"
        )
        if pending_samples:
            requests = build_requests(pending_samples, task_name, pending_indices)
            responses = backend.run_requests(
                requests,
                model=generation_model,
                task_name=task_name,
                workers=generation_workers,
            )

            response_map = {response.custom_id: response for response in responses}
            for sample_idx, sample in tqdm(zip(pending_indices, pending_samples), total=len(pending_indices), desc=method):
                response = response_map[f"{task_name}-sample-{sample_idx}"]
                if response.error:
                    sample['generation'] = f"[ERROR] {response.error}"
                else:
                    sample['generation'] = response.content
                sample.update(build_usage_fields(response.usage))
                data[sample_idx] = sample

        generation_path.parent.mkdir(parents=True, exist_ok=True)
        generation_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding='utf-8')
        print(f"[{method}] Results saved to {generation_path}")


def main() -> None:
    print(f"[DEBUG] generation backend={backend_kind} model={generation_model} workers={generation_workers}")
    for method in methods:
        print(f"[DEBUG] Processing method: {method}")
        process_method(method)


if __name__ == '__main__':
    main()
