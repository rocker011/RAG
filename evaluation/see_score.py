import os
import argparse
import copy

parse = argparse.ArgumentParser()
parse.add_argument('--method', default='NaiveGeneration')
parse.add_argument('--data_source', default='hypertension')
args = parse.parse_args()
method = args.method
data_source = args.data_source
import json

print(f"Data Source: {data_source}, Method: {method}")

with open(f"results/{method}/{data_source}/test_score.json", encoding="utf-8") as f:
    config = json.load(f)
    
with open(f"results/{method}/{data_source}/test_result.json", encoding="utf-8") as f:
    data = json.load(f)

score_dictr1 = {
    "b": [],
    "n": [],
}

score_dictr ={
    # "em": copy.deepcopy(score_dictr1),
    "f1": copy.deepcopy(score_dictr1),
    "rsim": copy.deepcopy(score_dictr1),
    "gen": copy.deepcopy(score_dictr1)
}


def is_metric_available(metric_name: str) -> bool:
    if metric_name == "gen":
        return config.get("llm_judge_enabled", config.get("overall_gen") is not None)
    return True


def format_percent(value):
    if value is None:
        return "N/A"
    return round(value * 100, 2)
    
for d in data:
    if d["nary"] == 2:
        for key in score_dictr.keys():
            if is_metric_available(key) and d.get(key) is not None:
                score_dictr[key]["b"].append(d[key])
    elif d["nary"] > 2:
        for key in score_dictr.keys():
            if is_metric_available(key) and d.get(key) is not None:
                score_dictr[key]["n"].append(d[key])
            
for key in score_dictr.keys():
    for k in score_dictr[key].keys():
        if len(score_dictr[key][k]) == 0:
            score_dictr[key][k] = None
        else:
            score_dictr[key][k] = sum(score_dictr[key][k]) / len(score_dictr[key][k])
print("Score Dictionary:")

for key in score_dictr1:
    print(key)
    for k in score_dictr.keys():
        print(k, format_percent(score_dictr[k][key]))
    print("=====================================")

print("overall")
for key in config.keys():
    if key != "overall_em":
        if key in {"llm_judge_enabled", "judge_backend", "judge_model"}:
            print(key, config[key])
        else:
            print(key, format_percent(config[key]))
print("=====================================")

    
