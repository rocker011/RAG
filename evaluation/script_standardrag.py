import argparse
import asyncio
import json
import os

from tqdm.asyncio import tqdm_asyncio

from hypergraphrag import HyperGraphRAG, QueryParam
from hypergraphrag.openai_config import is_local_embed_model
from hypergraphrag.utils import list_of_list_to_csv, truncate_list_by_token_size


parser = argparse.ArgumentParser()
parser.add_argument("--data_source", default="hypertension")
parser.add_argument(
    "--chunk_top_k",
    type=int,
    default=None,
    help="Dense chunk retrieval top-k. Defaults to QueryParam.top_k or HGRAG_STANDARDRAG_TOP_K.",
)
parser.add_argument(
    "--token_budget",
    type=int,
    default=None,
    help=(
        "Maximum tokens for retrieved chunk context. "
        "Defaults to the total HyperGraphRAG context budget or HGRAG_STANDARDRAG_TOKEN_BUDGET."
    ),
)
args = parser.parse_args()
data_source = args.data_source


def resolve_context_budget() -> int:
    if args.token_budget is not None:
        return args.token_budget
    env_budget = os.getenv("HGRAG_STANDARDRAG_TOKEN_BUDGET")
    if env_budget:
        return int(env_budget)
    default_param = QueryParam()
    return (
        default_param.max_token_for_text_unit
        + default_param.max_token_for_global_context
        + default_param.max_token_for_local_context
    )


def resolve_chunk_top_k() -> int:
    if args.chunk_top_k is not None:
        return args.chunk_top_k
    env_top_k = os.getenv("HGRAG_STANDARDRAG_TOP_K")
    if env_top_k:
        return int(env_top_k)
    return QueryParam().top_k


def format_sources_context(chunk_items: list[dict]) -> str:
    csv_rows = [["id", "\tcontent"]]
    for idx, item in enumerate(chunk_items, start=1):
        csv_rows.append([str(idx), f"\t{item['content']}"])
    csv_text = list_of_list_to_csv(csv_rows)
    return f"\n-----Sources-----\n```csv\n{csv_text}```\n"


rag_kwargs = {"working_dir": f"expr/{data_source}"}
query_concurrency = int(os.getenv("HGRAG_STANDARDRAG_QUERY_CONCURRENCY", "32"))
if is_local_embed_model():
    rag_kwargs["embedding_func_max_async"] = 1
    query_concurrency = int(os.getenv("HGRAG_STANDARDRAG_QUERY_CONCURRENCY", "2"))
rag = HyperGraphRAG(**rag_kwargs)
chunk_top_k = resolve_chunk_top_k()
token_budget = resolve_context_budget()


async def retrieve_dense_chunks(question: str) -> str:
    chunk_hits = await rag.chunks_vdb.query(question, top_k=chunk_top_k)
    if not chunk_hits:
        return format_sources_context([])

    chunk_ids = [item["id"] for item in chunk_hits]
    chunk_payloads = await rag.text_chunks.get_by_ids(chunk_ids)

    ordered_chunks = []
    for rank, (hit, payload) in enumerate(zip(chunk_hits, chunk_payloads), start=1):
        if payload is None:
            continue
        ordered_chunks.append(
            {
                "id": hit["id"],
                "rank": rank,
                "distance": hit.get("distance", 0.0),
                "content": payload["content"].strip(),
                "tokens": payload.get("tokens", 0),
                "full_doc_id": payload.get("full_doc_id"),
                "chunk_order_index": payload.get("chunk_order_index"),
            }
        )

    truncated_chunks = truncate_list_by_token_size(
        ordered_chunks,
        key=lambda item: item["content"],
        max_token_size=token_budget,
    )
    return format_sources_context(truncated_chunks)


async def query_with_semaphore(sem: asyncio.Semaphore, question: str) -> str:
    async with sem:
        return await retrieve_dense_chunks(question)


async def main():
    with open(f"datasets/{data_source}/questions.json", encoding="utf-8") as f:
        data = json.load(f)
    questions = [item["question"] for item in data]

    print(
        json.dumps(
            {
                "event": "standardrag_dense_chunk_config",
                "data_source": data_source,
                "chunk_top_k": chunk_top_k,
                "token_budget": token_budget,
                "query_concurrency": query_concurrency,
            },
            ensure_ascii=False,
        )
    )

    sem = asyncio.Semaphore(query_concurrency)
    tasks = [query_with_semaphore(sem, question) for question in questions]
    results = await tqdm_asyncio.gather(*tasks)

    for item, knowledge in zip(data, results):
        item["knowledge"] = knowledge

    save_dir = f"results/StandardRAG/{data_source}/test_knowledge.json"
    if os.path.exists(save_dir):
        os.remove(save_dir)
    os.makedirs(os.path.dirname(save_dir), exist_ok=True)

    with open(save_dir, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Results saved to {save_dir}")


if __name__ == "__main__":
    asyncio.run(main())
