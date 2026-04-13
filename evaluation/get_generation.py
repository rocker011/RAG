import json
import os
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from hypergraphrag.openai_config import (
    ensure_openai_api_key,
    get_openai_base_url,
    get_openai_model,
)
parser = argparse.ArgumentParser()
parser.add_argument('--data_sources', default='hypertension')
parser.add_argument('--methods', default='StandardRAG')
args = parser.parse_args()
methods = args.methods.split(',')
data_sources = args.data_sources.split(',')
generation_workers = int(os.getenv("HGRAG_GENERATION_WORKERS", "2"))

api_key = ensure_openai_api_key()
base_url = get_openai_base_url(default="https://vip.apiyi.com/v1")
chat_model = get_openai_model(default="gpt-4o-mini")

client_kwargs = {"api_key": api_key}
if base_url is not None:
    client_kwargs["base_url"] = base_url
client = OpenAI(**client_kwargs)

def generate_response(d):
    # d['knowledge'] = ' '.join(d['knowledge'].split(' ')[:1200])
    prompt = f"""---Role---

You are a helpful assistant responding to questions based on given knowledge.

---Knowledge---

{d['knowledge']}

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

{d['question']}
"""
    d['prompt'] = prompt
    try:
        response = client.chat.completions.create(
            model=chat_model,
            messages=[{"role": "user", "content": prompt}]
        )
        d['generation'] = response.choices[0].message.content
    except Exception as e:
        d['generation'] = f"[ERROR] {str(e)}"
    return d

def process_method(method):
    for data_source in data_sources:
        print(f"[DEBUG] {method} {data_source}")
        data_dir = f"results/{method}/{data_source}/test_knowledge.json"
        with open(data_dir, encoding="utf-8") as f:
            data = json.load(f)

        results = []
        with ThreadPoolExecutor(max_workers=generation_workers) as executor:
            futures = [executor.submit(generate_response, d) for d in data]
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"{method}"):
                results.append(future.result())

        save_dir = f"results/{method}/{data_source}/test_generation.json"
        os.makedirs(os.path.dirname(save_dir), exist_ok=True)
        with open(save_dir, 'w', encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        print(f"[{method}] Results saved to {save_dir}")

def main():
    for method in methods:
        print(f"[DEBUG] Processing method: {method}")
        process_method(method)

if __name__ == "__main__":
    main()
            
            
