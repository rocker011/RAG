import json
import os
import sys
import traceback

ROOT = r"D:\PythonProjects\HyperGraphRAG\evaluation"
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from hypergraphrag import HyperGraphRAG
from hypergraphrag.openai_config import ensure_openai_api_key, is_local_embed_model

ensure_openai_api_key()

cls = 'hypertension'
workdir = os.path.join('expr', cls)
with open(os.path.join('contexts', f'{cls}_contexts.json'), 'r', encoding='utf-8') as f:
    unique_contexts = json.load(f)

local_llm_max_async = int(os.getenv('HGRAG_INSERT_LLM_MAX_ASYNC', '8'))
remote_llm_max_async = int(os.getenv('HGRAG_INSERT_LLM_MAX_ASYNC', '32'))
entity_summary_llm_max_async = int(os.getenv('HGRAG_ENTITY_SUMMARY_LLM_MAX_ASYNC', '1'))
rag_kwargs = {
    "working_dir": workdir,
    "llm_model_max_async": remote_llm_max_async,
    "entity_summary_llm_max_async": entity_summary_llm_max_async,
}
if is_local_embed_model():
    rag_kwargs["embedding_func_max_async"] = 1
    rag_kwargs["embedding_batch_num"] = 8
    rag_kwargs["llm_model_max_async"] = local_llm_max_async
else:
    rag_kwargs["embedding_func_max_async"] = 32

print('RAG_KWARGS', rag_kwargs, flush=True)
print('DOCS', len(unique_contexts), flush=True)
rag = HyperGraphRAG(**rag_kwargs)

try:
    rag.insert(unique_contexts)
    print('STEP1_OK', flush=True)
except Exception as e:
    print('STEP1_ERR', repr(e), flush=True)
    traceback.print_exc()
    raise
