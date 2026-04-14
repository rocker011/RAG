from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Callable

from tqdm.asyncio import tqdm_asyncio

from hypergraphrag import HyperGraphRAG, QueryParam
from hypergraphrag.openai_config import ensure_openai_api_key, is_local_embed_model


BASE_DIR = Path(__file__).resolve().parents[1]


def resolve_query_concurrency(env_name: str = "HGRAG_QUERY_CONCURRENCY") -> tuple[dict, int]:
    rag_kwargs = {"working_dir": None}
    query_concurrency = int(os.getenv(env_name, "32"))
    if is_local_embed_model():
        rag_kwargs["embedding_func_max_async"] = 1
        query_concurrency = int(os.getenv(env_name, "2"))
    return rag_kwargs, query_concurrency


def build_rag(data_source: str, env_name: str = "HGRAG_QUERY_CONCURRENCY") -> tuple[HyperGraphRAG, int]:
    ensure_openai_api_key()
    rag_kwargs, query_concurrency = resolve_query_concurrency(env_name)
    rag_kwargs["working_dir"] = f"expr/{data_source}"
    return HyperGraphRAG(**rag_kwargs), query_concurrency


def load_question_data(data_source: str) -> tuple[list[dict], list[str]]:
    dataset_path = BASE_DIR / "datasets" / data_source / "questions.json"
    with dataset_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data, [item["question"] for item in data]


def save_knowledge_results(method_name: str, data_source: str, data: list[dict]) -> Path:
    save_path = BASE_DIR / "results" / method_name / data_source / "test_knowledge.json"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if save_path.exists():
        save_path.unlink()
    save_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    return save_path


async def run_query_method(
    *,
    data_source: str,
    method_name: str,
    query_param_factory: Callable[[], QueryParam],
    env_name: str = "HGRAG_QUERY_CONCURRENCY",
) -> Path:
    rag, query_concurrency = build_rag(data_source, env_name=env_name)
    data, questions = load_question_data(data_source)
    sem = asyncio.Semaphore(query_concurrency)

    async def query_with_semaphore(question: str) -> str:
        async with sem:
            return await rag.aquery(question, query_param_factory())

    tasks = [query_with_semaphore(question) for question in questions]
    results = await tqdm_asyncio.gather(*tasks)

    for item, knowledge in zip(data, results):
        item["knowledge"] = knowledge

    save_path = save_knowledge_results(method_name, data_source, data)
    print(f"Results saved to {save_path.as_posix()}")
    return save_path
