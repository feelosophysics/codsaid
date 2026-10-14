"""4단계(이미지): 오차 분석에서 가장 많은 원인 태그에 맞춘 처방을 적용하고 효과를 정량화한다.

처방 선택 (results/vision_error_stats.json의 dominant 태그)
  데이터 품질 / 배경·잡음  → photometric 증강 (밝기·대비·색, 회전, 더 넓은 크롭 범위)
  클래스 유사성 / 모델 한계 → 미세 조정 범위 한 단계 확대 + 224px 입력 (세밀한 무늬·꽃판 구조를 더 보게)
  라벨 오류                → 학습 데이터 정제가 처방이라 모델 실험 대신 해당 이미지 목록만 남긴다

처방 전·후를 seed 0·1·2로 학습해 Test 정확도 평균±표준편차를 재고, 태그를 단 오분류 사진을 처방 전·후 모델이
각각 몇 장 맞혔는지 태그별로 센다.

실행: uv run python scripts/vision_improve.py [--prescription photometric|deeper]
"""
import argparse
from dataclasses import asdict, replace

import numpy as np
import pandas as pd

from perfdiag.common import REPORTS, RESULTS, ROOT, Tee, configure_cpu, load_json, save_json, utf8_console
from perfdiag.vision.data import class_names, load_manifest, load_split
from perfdiag.vision.train import VisionConfig, run

DEEPER = {"linear_probe": "partial", "partial": "full", "full": "full"}
SEEDS = (0, 1, 2)


def prescription_for(tag):
    if tag in ("데이터 품질", "배경/잡음"):
        return "photometric"
    if tag in ("클래스 유사성", "모델 한계"):
        return "deeper"
    return None


def main():
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prescription", choices=["photometric", "deeper"])
    args = parser.parse_args()
    configure_cpu()
    transfer = load_json(RESULTS / "vision_transfer.json")
    stats = load_json(RESULTS / "vision_error_stats.json")
    main_run = next(r for r in transfer["runs"] if r["is_main"])
    before_cfg = VisionConfig(**main_run["config"])
    choice = args.prescription or prescription_for(stats["dominant"])
    if choice is None:
        raise SystemExit("주 원인이 라벨 오류다. 모델 실험보다 데이터 정제가 먼저다")
    if choice == "photometric":
        after_cfg = replace(before_cfg, augmentation="photometric")
    else:
        after_cfg = replace(before_cfg, strategy=DEEPER[before_cfg.strategy], image_size=224,
                            lr_head=1e-3 if before_cfg.strategy == "linear_probe" else before_cfg.lr_head)
    names = class_names()
    df = load_manifest()
    train = load_split(df, "train", main_run["shots"])
    validation, test = load_split(df, "validation"), load_split(df, "test")
    tags = pd.read_csv(ROOT / "annotations" / "error_tags.csv", dtype=str, encoding="utf-8-sig").fillna("")
    tag_of = dict(zip(tags["file"], tags["primary_tag"]))
    out = {"dominant_tag": stats["dominant"], "prescription": choice, "before": asdict(before_cfg),
           "after": asdict(after_cfg), "runs": {"before": [], "after": []}}
    with Tee(REPORTS / "logs" / "vision_improve.log"):
        print(f"주 원인 '{stats['dominant']}' → 처방 '{choice}'")
        for label, cfg in (("before", before_cfg), ("after", after_cfg)):
            for seed in SEEDS:
                _, result = run(train, validation, test, replace(cfg, seed=seed), len(names), log=lambda *_: None)
                pred = result.pop("test_proba").argmax(1)
                out["runs"][label].append({"seed": seed, "train": result["train"], "validation": result["validation"],
                                           "test": result["test"], "diagnosis": result["diagnosis"],
                                           "seconds": result["history"]["seconds"], "test_pred": pred})
                print(f"  {label:<6} seed {seed}: Train {result['train']['accuracy']:.3f}  Validation "
                      f"{result['validation']['accuracy']:.3f}  Test {result['test']['accuracy']:.3f}  "
                      f"({result['history']['seconds']:.0f}초)")
        for label in ("before", "after"):
            acc = [r["test"]["accuracy"] for r in out["runs"][label]]
            out[f"{label}_test_accuracy"] = {"mean": float(np.mean(acc)), "std": float(np.std(acc))}
        gain = out["after_test_accuracy"]["mean"] - out["before_test_accuracy"]["mean"]
        out["gain_points"] = gain * 100
        # 태그를 단 오분류 사진(분석 대상)을 처방 전·후 모델(seed 0)이 각각 몇 장 맞혔는가
        before_pred = out["runs"]["before"][0]["test_pred"]
        after_pred = out["runs"]["after"][0]["test_pred"]
        index = {f: i for i, f in enumerate(test.files)}
        by_tag = {}
        for file, tag in tag_of.items():
            i = index[file]
            row = by_tag.setdefault(tag, {"total": 0, "before_correct": 0, "after_correct": 0})
            row["total"] += 1
            row["before_correct"] += int(before_pred[i] == test.targets[i])
            row["after_correct"] += int(after_pred[i] == test.targets[i])
        out["fixed_by_tag"] = by_tag
        print(f"Test 정확도 {out['before_test_accuracy']['mean']:.3f}±{out['before_test_accuracy']['std']:.3f} → "
              f"{out['after_test_accuracy']['mean']:.3f}±{out['after_test_accuracy']['std']:.3f} ({gain * 100:+.1f}%p)")
        for t, v in out["fixed_by_tag"].items():
            print(f"  분석 대상 오분류 사진 중 맞힌 수 — {t}: 처방 전 {v['before_correct']}/{v['total']}, "
                  f"처방 후 {v['after_correct']}/{v['total']}")
    save_json(RESULTS / "vision_improve.json", out)


if __name__ == "__main__":
    main()
