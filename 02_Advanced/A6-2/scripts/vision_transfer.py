"""트랙 A: Few-shot 전이 학습 — 데이터 크기(shots) × Layer freezing 전략 비교.

실험 (seed 0, 입력 160px)
  shots 5·10·20장/클래스 × {Linear Probing, 부분 미세 조정(layer4+fc), 전체 Fine-tuning}
  shots 20 × 직접 학습(무작위 초기화)   ← 사전학습의 효용 비교군

20장 조건에서 Validation 정확도(동률이면 Validation 손실)가 가장 좋은 사전학습 모델을 '주 모델'로 정하고,
그 모델의 Test 오분류를 오차 분석에 넘긴다 (results/vision_errors.csv). 30건이 안 되면 다른 모델의 오분류를
더해 30장 이상을 모은다 (analysis_models 참고).

실행: uv run python scripts/vision_transfer.py   (약 35분, CPU 6스레드)
"""
import argparse

import numpy as np
import pandas as pd

from perfdiag.common import REPORTS, RESULTS, Tee, configure_cpu, save_json, utf8_console
from perfdiag.vision.data import FLOWERS, class_names, load_manifest, load_split
from perfdiag.vision.models import STRATEGY_LABELS
from perfdiag.vision.train import VisionConfig, run

SHOTS = (5, 10, 20)
# 사진이 적을수록 epoch당 갱신 횟수가 줄어들므로 epoch을 늘린다
EPOCHS = {"linear_probe": {5: 40, 10: 30, 20: 25}, "partial": {5: 30, 10: 25, 20: 20},
          "full": {5: 30, 10: 25, 20: 20}, "scratch": {5: 30, 10: 30, 20: 30}}
# 학습률: Linear Probing은 분류기 하나라 크게, 몸통까지 학습하면 분류기 1e-3·몸통 1e-4
LR_HEAD = {"linear_probe": 1e-2, "partial": 1e-3, "full": 1e-3, "scratch": 1e-3}
PRETRAINED = ("linear_probe", "partial", "full")


def confusion(targets, preds, n):
    matrix = np.zeros((n, n), dtype=int)
    np.add.at(matrix, (targets, preds), 1)
    return matrix


SHORT = {"linear_probe": "LP", "partial": "부분", "full": "전체", "scratch": "직접"}
MIN_ERRORS = 30   # 미션: 오차 분석표 최소 30건


def run_name(r):
    return f"{r['shots']}장·{SHORT[r['strategy']]}"


def analysis_models(runs, main_run):
    """오차 분석에 넣을 모델들. 주 모델부터 시작해 오분류 이미지가 30장 이상이 될 때까지 추가한다.

    주 모델 하나로 30건이 안 되면 같은 사진 수의 다른 사전학습 모델(Validation 정확도 순),
    그다음 더 적은 사진 수의 모델을 차례로 더한다. 모델 선택이 아니라 '분석할 실패 사례'를 모으는 단계다.
    """
    rest = [r for r in runs if r is not main_run and r["strategy"] in PRETRAINED]
    rest.sort(key=lambda r: (-r["shots"], -r["validation"]["accuracy"], r["validation"]["loss"]))
    chosen, wrong = [], set()
    for r in [main_run, *rest]:
        chosen.append(r)
        wrong |= set(np.flatnonzero(r["test_proba"].argmax(1) != r["test_targets"]))
        if len(wrong) >= MIN_ERRORS:
            break
    return chosen


def error_table(test_set, chosen, names):
    """chosen 모델 중 하나라도 틀린 Test 이미지. 예측·신뢰도는 목록에서 먼저 나온(=주 모델 우선) 틀린 모델의 값이다."""
    targets = test_set.targets
    preds = [r["test_proba"].argmax(1) for r in chosen]
    rows = []
    for i in range(len(targets)):
        wrong = [k for k, p in enumerate(preds) if p[i] != targets[i]]
        if not wrong:
            continue
        r = chosen[wrong[0]]
        proba = r["test_proba"][i]
        order = np.argsort(proba)[::-1]
        rows.append({"file": test_set.files[i], "true": names[targets[i]], "pred": names[order[0]],
                     "confidence": round(float(proba[order[0]]), 4), "true_proba": round(float(proba[targets[i]]), 4),
                     "second": names[order[1]], "second_proba": round(float(proba[order[1]]), 4),
                     "reported_by": run_name(r), "wrong_models": ";".join(run_name(chosen[k]) for k in wrong),
                     "n_wrong_models": len(wrong)})
    return pd.DataFrame(rows).sort_values(["n_wrong_models", "confidence"], ascending=False).reset_index(drop=True)


def main():
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", type=int, nargs="*", default=list(SHOTS))
    parser.add_argument("--epochs-scale", type=float, default=1.0, help="빠른 점검용 (예: 0.2)")
    args = parser.parse_args()
    threads = configure_cpu()
    names = class_names()
    df = load_manifest()
    validation, test = load_split(df, "validation"), load_split(df, "test")
    runs = []
    with Tee(REPORTS / "logs" / "vision_transfer.log"):
        print(f"CPU 스레드 {threads}개, 클래스 {len(names)}개, Validation {len(validation.targets)}장, "
              f"Test {len(test.targets)}장")
        for shots in args.shots:
            train = load_split(df, "train", shots)
            strategies = PRETRAINED + (("scratch",) if shots == max(args.shots) else ())
            for strategy in strategies:
                epochs = max(1, round(EPOCHS[strategy][shots] * args.epochs_scale))
                cfg = VisionConfig(strategy=strategy, epochs=epochs, lr_head=LR_HEAD[strategy])
                print(f"\n[shots {shots}] {STRATEGY_LABELS[strategy]} — Train {len(train.targets)}장, {epochs} epoch")
                model, result = run(train, validation, test, cfg, len(names))
                result.update(shots=shots, strategy=strategy, label=STRATEGY_LABELS[strategy], test_targets=test.targets)
                d = result["diagnosis"]
                print(f"  → Train 정확도 {result['train']['accuracy']:.3f}, Validation {result['validation']['accuracy']:.3f}, "
                      f"Test {result['test']['accuracy']:.3f} | 학습 파라미터 {result['trainable_parameters']:,} | "
                      f"{d['label']} ({result['history']['seconds']:.0f}초)")
                runs.append(result)
        top = max(args.shots)
        candidates = [r for r in runs if r["shots"] == top and r["strategy"] in PRETRAINED]
        main_run = max(candidates, key=lambda r: (r["validation"]["accuracy"], -r["validation"]["loss"]))
        proba = main_run["test_proba"]
        chosen = analysis_models(runs, main_run)
        errors = error_table(test, chosen, names)
        errors.to_csv(RESULTS / "vision_errors.csv", index=False, lineterminator="\n")
        main_errors = int((proba.argmax(1) != test.targets).sum())
        print(f"\n주 모델: shots {top} {main_run['label']} — Test 정확도 {main_run['test']['accuracy']:.3f}, "
              f"오분류 {main_errors}건")
        print(f"오차 분석 대상 모델: {', '.join(run_name(r) for r in chosen)} → 오분류 이미지 {len(errors)}장 "
              f"→ results/vision_errors.csv")
    for r in runs:
        r["is_main"] = r is main_run
        r["in_error_analysis"] = any(r is c for c in chosen)
        r["name"] = run_name(r)
        r.pop("test_targets")
        r["test_proba"] = np.round(r["test_proba"], 4)
        r["test_pred"] = r["test_proba"].argmax(1)
    save_json(RESULTS / "vision_transfer.json", {
        "classes": names, "image_root": FLOWERS, "test_files": test.files, "test_targets": test.targets,
        "validation_size": len(validation.targets), "runs": runs,
        "main": {"shots": main_run["shots"], "strategy": main_run["strategy"], "name": run_name(main_run),
                 "errors": main_errors, "confusion": confusion(test.targets, proba.argmax(1), len(names))},
        "error_analysis_models": [run_name(r) for r in chosen], "error_analysis_images": len(errors),
    })


if __name__ == "__main__":
    main()
