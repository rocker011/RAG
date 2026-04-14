import argparse
import json
import os
import traceback
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm

from eval import cal_em, cal_f1
from eval_g import (
    GEN_METRICS,
    aggregate_metric_results,
    build_metric_prompt,
    parse_metric_response,
)
from eval_r import cal_rsim
from inference_backend import (
    InferenceRequest,
    get_backend,
    get_judge_backend_kind,
    get_judge_model,
    get_judge_workers,
)

score_workers = int(os.getenv("HGRAG_SCORE_WORKERS", "1"))
judge_backend_kind = get_judge_backend_kind()
judge_backend = get_backend(judge_backend_kind)
judge_model = get_judge_model()
judge_workers = get_judge_workers()


def extract_answer(generation: str) -> str:
    try:
        return generation.split("<answer>")[1].split("</answer>")[0].strip()
    except Exception:
        return generation


def evaluate_local_metrics(sample: dict) -> dict:
    generation = sample['generation']
    answer = extract_answer(generation)
    em_score = cal_em([sample['golden_answers']], [answer])
    f1_score = cal_f1([sample['golden_answers']], [answer])

    context = []
    for chunk in sample['context']:
        if chunk not in context:
            context.append(chunk)

    rsim_score = cal_rsim(['\n'.join(context)], [sample['knowledge']]) if sample['knowledge'] != "" else 0.0
    sample['em'] = em_score
    sample['f1'] = f1_score
    sample['rsim'] = rsim_score
    return sample


def build_judge_requests(method: str, data_source: str, data: list[dict]) -> list[InferenceRequest]:
    requests = []
    for idx, sample in enumerate(data):
        for metric in GEN_METRICS:
            prompt = build_metric_prompt(metric, sample['question'], sample['golden_answers'], sample['generation'])
            requests.append(
                InferenceRequest(
                    custom_id=f"judge-{method}-{data_source}-{idx}-{metric}",
                    messages=[{"role": "user", "content": prompt}],
                )
            )
    return requests


def apply_judge_results(method: str, data_source: str, data: list[dict], responses) -> None:
    response_map = {response.custom_id: response for response in responses}
    for idx, sample in enumerate(data):
        metric_results = {}
        for metric in GEN_METRICS:
            custom_id = f"judge-{method}-{data_source}-{idx}-{metric}"
            response = response_map.get(custom_id)
            if response is None or response.error:
                content = ""
                if response is not None and response.error:
                    content = f"<score>5</score><explanation>Judge backend error: {response.error}</explanation>"
            else:
                content = response.content
            metric_results[metric] = parse_metric_response(content, sample['f1'])
        gen_score = aggregate_metric_results(metric_results)
        sample['gen'] = gen_score['score']
        sample['gen_exp'] = gen_score['explanation']


def evaluate_method(args):
    method = args.method
    data_source = args.data_source
    success_flag = False

    try:
        print(f"[DEBUG] Evaluating {method} on {data_source}")
        print(f"[DEBUG] judge backend={judge_backend_kind} model={judge_model} workers={judge_workers}")
        data_dir = f"results/{method}/{data_source}/test_generation.json"
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"File not found: {data_dir}")

        with open(data_dir, encoding="utf-8") as f:
            data = json.load(f)

        if score_workers <= 1:
            data = [evaluate_local_metrics(sample) for sample in tqdm(data, desc=f"{method}-local")]
        else:
            with ThreadPoolExecutor(max_workers=score_workers) as executor:
                data = list(tqdm(executor.map(evaluate_local_metrics, data), total=len(data), desc=f"{method}-local"))

        judge_requests = build_judge_requests(method, data_source, data)
        judge_responses = judge_backend.run_requests(
            judge_requests,
            model=judge_model,
            task_name=f"judge-{method}-{data_source}",
            workers=judge_workers,
        )
        apply_judge_results(method, data_source, data, judge_responses)

        overall_em = sum([sample['em'] for sample in data]) / len(data)
        overall_f1 = sum([sample['f1'] for sample in data]) / len(data)
        overall_rsim = sum([sample['rsim'] for sample in data]) / len(data)
        overall_gen = sum([sample['gen'] for sample in data]) / len(data)

        print(f"{method} Overall EM: {overall_em:.4f}")
        print(f"{method} Overall F1: {overall_f1:.4f}")
        print(f"{method} Overall R-Sim: {overall_rsim:.4f}")
        print(f"{method} Overall Gen: {overall_gen:.4f}")

        save_base = f"results/{method}/{data_source}"
        os.makedirs(save_base, exist_ok=True)

        result_path = os.path.join(save_base, "test_result.json")
        with open(result_path, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        score_path = os.path.join(save_base, "test_score.json")
        with open(score_path, 'w', encoding="utf-8") as f:
            json.dump(
                {
                    "overall_em": overall_em,
                    "overall_f1": overall_f1,
                    "overall_rsim": overall_rsim,
                    "overall_gen": overall_gen,
                },
                f,
                indent=4,
                ensure_ascii=False,
            )

        success_flag = True
        print(f"[SAVED] {result_path}")
        print(f"[SAVED] {score_path}")
        print(f"[SUCCESS] {method} finished and saved.")
    except Exception as exc:
        print(f"\n[ERROR] {method} failed due to: {str(exc)}")
        traceback.print_exc()
        raise

    if not success_flag:
        raise RuntimeError(f"{method} did not complete saving.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--method', type=str, default='HyperGraphRAG_wo_ER')
    parser.add_argument('--data_source', type=str, default='hypertension')
    evaluate_method(parser.parse_args())
