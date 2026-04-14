import json
import argparse
import os
import asyncio
from hypergraphrag import HyperGraphRAG, QueryParam
from hypergraphrag.openai_config import ensure_openai_api_key, is_local_embed_model
from tqdm.asyncio import tqdm_asyncio

ensure_openai_api_key()

parser = argparse.ArgumentParser()
parser.add_argument("--data_source", default="hypertension")
args = parser.parse_args()
data_source = args.data_source

rag_kwargs = {"working_dir": f"expr/{data_source}"}
query_concurrency = int(os.getenv("HGRAG_QUERY_CONCURRENCY", "32"))
if is_local_embed_model():
    rag_kwargs["embedding_func_max_async"] = 1
    query_concurrency = int(os.getenv("HGRAG_QUERY_CONCURRENCY", "2"))
rag = HyperGraphRAG(**rag_kwargs)


async def query_with_semaphore(sem, q):
    async with sem:
        return await rag.aquery(
            q,
            QueryParam(only_need_context=True, subgraph_selector="swhc"),
        )


async def main():
    with open(f"datasets/{data_source}/questions.json", encoding="utf-8") as f:
        data = json.load(f)
    questions = [item["question"] for item in data]

    sem = asyncio.Semaphore(query_concurrency)
    tasks = [query_with_semaphore(sem, q) for q in questions]
    results = await tqdm_asyncio.gather(*tasks)

    for d, res in zip(data, results):
        d["knowledge"] = res

    save_dir = f"results/SWHC/{data_source}/test_knowledge.json"
    if os.path.exists(save_dir):
        os.remove(save_dir)
    if not os.path.exists(os.path.dirname(save_dir)):
        os.makedirs(os.path.dirname(save_dir))

    with open(save_dir, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"Results saved to {save_dir}")


if __name__ == "__main__":
    asyncio.run(main())
