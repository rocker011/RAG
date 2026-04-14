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


def build_requests(data: list[dict], task_name: str) -> list[InferenceRequest]:
    requests = []
    for idx, sample in enumerate(data):
        prompt = build_generation_prompt(sample)
        sample['prompt'] = prompt
        requests.append(
            InferenceRequest(
                custom_id=f"{task_name}-sample-{idx}",
                messages=[{"role": "user", "content": prompt}],
            )
        )
    return requests


def process_method(method: str) -> None:
    for data_source in data_sources:
        print(f"[DEBUG] {method} {data_source}")
        data_dir = Path(f"results/{method}/{data_source}/test_knowledge.json")
        with data_dir.open(encoding='utf-8') as f:
            data = json.load(f)

        task_name = f"generation-{method}-{data_source}"
        requests = build_requests(data, task_name)
        responses = backend.run_requests(
            requests,
            model=generation_model,
            task_name=task_name,
            workers=generation_workers,
        )

        response_map = {response.custom_id: response for response in responses}
        for idx, sample in enumerate(tqdm(data, desc=method)):
            response = response_map[f"{task_name}-sample-{idx}"]
            if response.error:
                sample['generation'] = f"[ERROR] {response.error}"
            else:
                sample['generation'] = response.content

        save_dir = Path(f"results/{method}/{data_source}/test_generation.json")
        save_dir.parent.mkdir(parents=True, exist_ok=True)
        save_dir.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding='utf-8')
        print(f"[{method}] Results saved to {save_dir}")


def main() -> None:
    print(f"[DEBUG] generation backend={backend_kind} model={generation_model} workers={generation_workers}")
    for method in methods:
        print(f"[DEBUG] Processing method: {method}")
        process_method(method)


if __name__ == '__main__':
    main()
