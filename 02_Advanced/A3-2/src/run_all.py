"""전체 실험: 추적 성능표 → 규칙 추가 실험 → 파라미터 탐색 → 배경 학습률 → 특징점 → 보너스 → 그림·results.json.

실행:
  python -m src.run_all              # 전체 (8~14분, OpenCV 스레드 2개)
  python -m src.run_all --quick      # 배경 모델 비교와 특징점 곡선을 줄여 약 2분
  python -m src.run_all --threads 1  # 다른 작업과 함께 돌릴 때
  python -m src.run_all --cache .cache   # 검출·정답 마스크를 저장해 두고 재실행 시 재사용

영상이 없으면 먼저 python -m src.synthetic 으로 만든다. 파라미터는 dev 분할에서 고르고 test 분할로 보고한다.
"""
import argparse
import csv
import json
import platform
import sys
import time
from pathlib import Path

import cv2
import matplotlib
import numpy as np

from . import cache as K
from . import evaluate as E
from . import experiments as X
from . import figures as F
from . import synthetic as S
from .features import TargetMatcher, make_view
from .image_io import imread
from .motion import MotionDetector, MotionParams
from .pipeline import VideoAnalyzer
from .tracker import Tracker
from .zone import IntrusionZone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


def log(msg, t0=[time.perf_counter()]):  # noqa: B006 — 시작 시각 공유용
    print(f"[{time.perf_counter() - t0[0]:6.1f}s] {msg}", flush=True)


def strip(obj):
    """JSON에 넣을 수 있게 넘파이 값을 바꾼다."""
    return json.loads(json.dumps(obj, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))


def frames_at(path, indices):
    want = set(indices)
    out = {}
    for i, f in enumerate(E.read_frames(path)):
        if i in want:
            out[i] = f
        if len(out) == len(want):
            break
    return out


def trails_upto(outputs, i, length=40):
    tr = {}
    for k in range(max(0, i - length), i + 1):
        for tid, _, c in outputs[k]:
            tr.setdefault(tid, []).append((int(c[0]), int(c[1])))
    return tr


def write_log_csv(rows, path):
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["영상명", "조건", "프레임 범위", "ID Switch 수", "실패 수", "관찰 메모"])
        for r in rows:
            w.writerow([r["video"], r["condition"], r["frames"], r["id_switch"], r["fail"], r["memo"]])


def score(rows_or_rec):
    r = rows_or_rec
    return (r["crossing"]["switches"] + r["crossing_same"]["switches"]
            + sum(r[s]["fails"] for s in ("single", "pause", "lighting", "crossing")) + sum(r[s]["false_ids"] for s in
                                                                                           ("single", "pause", "lighting")))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--cache", default="", help="중간 결과 캐시 폴더 (영상·파라미터·소스가 같으면 재사용)")
    args = ap.parse_args(argv)
    K.configure(args.cache)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cv2.setNumThreads(max(1, args.threads))
    OUT.mkdir(exist_ok=True)
    missing = [(sc, sp) for sp in S.SPLITS for sc in S.SCENARIOS if not (S.DATA / f"{sc}_{sp}.mp4").exists()]
    if missing:
        log(f"없는 합성 영상 {len(missing)}개를 생성한다")
        S.main(["--only", *sorted({sc for sc, _ in missing}), "--split", *sorted({sp for _, sp in missing})])
    res = {"environment": {"python": platform.python_version(), "opencv": cv2.__version__, "numpy": np.__version__,
                           "matplotlib": matplotlib.__version__, "platform": platform.platform(),
                           "processor": platform.processor(), "threads": args.threads, "quick": args.quick},
           "criteria": {"match_iou": E.MATCH_IOU, "switch_persist": E.SWITCH_PERSIST, "fail_frames": E.FAIL_FRAMES,
                        "visible": E.VISIBLE, "merge_cover": E.MERGE_COVER},
           "params": {"motion": vars(MotionParams()), "tracker": {"max_distance": 60.0, "max_missed": 20,
                                                                  "matcher": "greedy", "cost": "centroid"}}}

    # 1 검출 캐시 (추적기 비교는 같은 검출을 재사용한다)
    log("검출: dev·test 분할의 추적 시나리오 5개")
    cache = {sp: X.detection_cache(sp) for sp in ("dev", "test")}
    res["videos"] = {sp: {sc: {"video": c[0]["video"], "frames": c[0]["frames"], "events": len(c[0]["events"]),
                               "objects": c[0]["objects"]} for sc, c in cache[sp].items()} for sp in cache}

    # 2 미션 표 1 (기본 추적기, test)
    log("추적 성능표")
    rows, logs, full = X.tracking_table(cache["test"])
    res["table"] = rows
    res["events"] = {sc: r["events"] for sc, r in full.items()}
    res["objects"] = {sc: r["objects"] for sc, r in full.items()}
    write_log_csv(logs, OUT / "measurement_log.csv")
    res["log"] = logs

    # 3 규칙 추가 실험 (모든 변형 × 시나리오)
    log("규칙 추가 실험 (추적기 변형 8개)")
    res["variants"] = {sp: X.variant_experiment(cache[sp]) for sp in ("dev", "test")}

    # 4 파라미터 탐색: dev에서 고르고 test로 확인
    log("거리 임계값·기억 길이 탐색")
    sweeps = {}
    for sp in ("dev", "test"):
        sweeps[("max_distance", sp)] = X.param_sweep(cache[sp], "max_distance", [20, 30, 45, 60, 90, 120, 160])
        sweeps[("max_missed", sp)] = X.param_sweep(cache[sp], "max_missed", [5, 10, 20, 40, 80, 160])
    best = {p: min(sweeps[(p, "dev")], key=score)["value"] for p in ("max_distance", "max_missed")}
    tuned = X.tracking_table(cache["test"], max_distance=best["max_distance"], max_missed=best["max_missed"])[0]
    res["sweeps"] = {f"{p}|{sp}": rows for (p, sp), rows in sweeps.items()}
    res["tuned"] = {"chosen_on_dev": best, "test_table": tuned,
                    "dev_scores": {p: [{"value": r["value"], "score": score(r)} for r in sweeps[(p, "dev")]]
                                   for p in ("max_distance", "max_missed")}}

    # 5 보너스 1: Hungarian
    log("보너스 1: Hungarian vs 탐욕")
    res["hungarian"] = X.hungarian_random()
    res["hungarian"]["tracking_disagreement"] = X.assignment_disagreement(cache["test"])

    # 6 보너스 2: 침입 구역
    log("보너스 2: 침입 구역")
    res["zone"] = X.zone_experiment(cache["test"])

    # 7 배경 학습률과 배경 모델 비교
    log("배경 모델: 학습률 4가지 + 그림자 + 이동평균 3가지 + 프레임 차분 (프레임마다 정답 마스크 생성)")
    configs = X.bg_configs()
    if args.quick:
        configs = {k: v for k, v in configs.items() if k.startswith("mog2_") and "noshadow" not in k}
    pg, lg = S.load_gt("pause", "test"), S.load_gt("lighting", "test")
    stop5 = next(e for e in pg["events"] if e.get("resume") and e["resume"] - e["start"] >= 150)
    stop3 = next(e for e in pg["events"] if e.get("resume") and 80 <= e["resume"] - e["start"] < 150)
    on = next(e for e in lg["events"] if e["kind"] == "on")
    lamp = next(e for e in lg["events"] if e["kind"] == "lamp")
    sample_frames = {"pause": [stop5["start"] + 100, stop3["resume"] + 12],
                     "lighting": [on["start"] + 8, on["start"] + 45, lamp["start"] + 20]}
    scen = ("pause", "lighting") if args.quick else ("pause", "lighting", "single")
    bg = X.background_experiment("test", scen, configs, sample_frames)
    res["background"] = X.background_summary(bg, configs)

    # 8 특징점 매칭
    log("특징점 매칭: 조건표, 곡선, 일반화, 영상")
    texture = imread(S.TARGET_DIR / "target.png")
    res["features"] = {"table": X.feature_conditions(texture, trials=6 if args.quick else 10)}
    if not args.quick:
        res["features"]["sweeps"] = X.feature_sweeps(texture)
    res["features"]["generalization"] = X.generalization(texture)
    tv = X.target_video("test")
    res["features"]["video"] = {k: v for k, v in tv.items() if k != "poses"}

    # 9 속도
    log("처리 속도")
    res["speed"] = X.speed_benchmark()

    # 10 그림
    log("그림")
    make_figures(res, cache, bg, tv, texture, sample_frames, stop5, stop3, on, lamp, configs)
    (OUT / "results.json").write_text(json.dumps(strip(res), ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"완료 → {OUT.relative_to(ROOT)}")
    for r in rows:
        print(f"  {r['name']}: 테스트 {r['tests']}, ID Switch {r['switch_events']}건({r['switches']}회), "
              f"추적 실패 {r['fail_events']}건, 유령 ID {r['false_ids']}")


def make_figures(res, cache, bg, tv, texture, sample_frames, stop5, stop3, on, lamp, configs):
    test = cache["test"]
    # 01 시나리오
    picks = [("single", 260), ("crossing", 300), ("crossing_same", 300), ("pause", 500), ("lighting", 560), ("target", 290)]
    items = []
    for sc, i in picks:
        gt = S.load_gt(sc, "test")
        items.append((sc, frames_at(S.DATA / gt["video"], [i])[i], gt["gt"][i]))
    F.scenarios_overview(items, OUT / "01_scenarios.png")

    # 02 파이프라인 단계
    gt = test["crossing"][0]
    an = VideoAnalyzer(MotionParams(), Tracker())
    target_i = 95
    for i, f in enumerate(E.read_frames(S.DATA / gt["video"])):
        r = an.process(f)
        if i == target_i:
            F.pipeline_stages(f, r.raw_mask, r.mask, an.draw(f, r, 30.0), OUT / "02_pipeline.png")
            break

    # 03 ID 타임라인, 04 교차 장면, 05 x-t
    outs = {k: E.track_detections(test["crossing"][1], Tracker(**X.VARIANTS[k][1]))
            for k in ("baseline", "kalman", "kalman_appearance")}
    seqs = [(F.VAR_EN[k], E.sequences(gt, o)[0]) for k, o in outs.items()]
    F.id_timeline(gt, seqs, OUT / "03_id_timeline.png")
    ev = {e["kind"]: e for e in gt["events"]}
    want = []
    for kind in ("pass", "bounce"):
        e = ev[kind]
        mid = _merge_mid(gt, e)
        want += [max(e["start"], mid - 22), mid, min(e["end"], mid + 26)]
    fr = frames_at(S.DATA / gt["video"], want)
    panels = []
    for k in ("baseline", "kalman"):
        for n, kind in enumerate(("pass", "bounce")):
            row = []
            for j, lab in enumerate(("before", "merged", "after")):
                i = want[n * 3 + j]
                row.append((f"{F.KIND_EN[kind]} {lab} (f{i})", F.draw_tracks(fr[i], outs[k][i], trails_upto(outs[k], i))))
            panels.append((f"{F.VAR_EN[k]}\n{F.KIND_EN[kind]}", row))
    F.crossing_frames(panels, OUT / "04_crossing_frames.png")
    F.xt_plot(gt, [("pass", ev["pass"], {k: outs[k] for k in ("baseline", "kalman")}),
                   ("bounce", ev["bounce"], {k: outs[k] for k in ("baseline", "kalman")})], OUT / "05_xt_pass_bounce.png")

    # 06 규칙 히트맵, 07 파라미터 탐색
    F.rules_heatmap(res["variants"]["test"], OUT / "06_rules_heatmap.png")
    sw = {tuple(k.split("|")): v for k, v in res["sweeps"].items()}
    F.param_sweeps(sw, OUT / "07_param_sweep.png")

    # 08 학습률, 09 배경 마스크
    F.learning_rate(res["background"], bg["pause"]["gt"], bg["lighting"]["gt"], OUT / "08_learning_rate.png")
    cols = [(k, lab) for k, lab in (("mog2_0.0005", "MOG2 lr=0.0005"), ("mog2_0.002", "MOG2 lr=0.002"),
                                    ("mog2_0.05", "MOG2 lr=0.05"), ("mog2_0.002_noshadow", "MOG2 no shadow"),
                                    ("ravg_0.01", "running avg 0.01"), ("framediff", "frame diff")) if k in configs]
    rows = [(f"5 s stop +100f", bg["pause"]["samples"][sample_frames["pause"][0]]),
            (f"3 s stop, resume +12f", bg["pause"]["samples"][sample_frames["pause"][1]]),
            (f"light on +8f", bg["lighting"]["samples"][sample_frames["lighting"][0]]),
            (f"light on +45f", bg["lighting"]["samples"][sample_frames["lighting"][1]]),
            (f"local lamp +20f", bg["lighting"]["samples"][sample_frames["lighting"][2]])]
    F.bg_masks(rows, cols, OUT / "09_bg_masks.png")

    # 10~13 특징점
    if "sweeps" in res["features"]:
        F.feature_curves(res["features"]["sweeps"], OUT / "10_feature_curves.png")
    m = TargetMatcher(texture, "orb")
    ex = []
    for title, cond in (("ORB frontal", {}), ("ORB in-plane rotation 60 deg", {"roll": 60}),
                        ("ORB 3D tilt 60 deg", {"yaw": 60}), ("ORB 50% occluded", {"occlusion": 0.5})):
        img, c, H = next(X._views(texture, cond, 1, seed=5))
        r = m.match(img)
        good = [cv2.DMatch(i, i, 0) for i in range(r.n_good)]
        kp1 = [cv2.KeyPoint(float(x), float(y), 5) for x, y in (r.ref_pts if r.n_good else [])]
        kp2 = [cv2.KeyPoint(float(x), float(y), 5) for x, y in (r.scene_pts if r.n_good else [])]
        mask = r.inlier_mask.astype(np.uint8).tolist() if r.inlier_mask is not None else None
        vis = cv2.drawMatches(texture, kp1, img, kp2, good, None, matchColor=(0, 200, 0), singlePointColor=(0, 0, 255),
                              matchesMask=mask, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        ex.append((f"{title}: ratio-test {r.n_good}, inliers {r.n_inliers}, "
                   f"{'TARGET DETECTED' if r.found else 'not found'}", vis))
    F.feature_examples(ex, OUT / "11_feature_matches.png")
    same, other = imread(S.TARGET_DIR / "same_series.png"), imread(S.TARGET_DIR / "other.png")
    gray = cv2.cvtColor(texture, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 60, 160)
    sketch = cv2.cvtColor(255 - cv2.dilate(edges, np.ones((2, 2), np.uint8)), cv2.COLOR_GRAY2BGR)
    thumbs = [("1 registered", texture), ("2 same series", same), ("3 unrelated", other), ("4 negative", 255 - texture),
              ("5 line drawing", sketch)]
    F.generalization(res["features"]["generalization"], thumbs, OUT / "12_generalization.png")
    F.target_timeline(tv, S.load_gt("target", "test"), OUT / "13_target_video.png")

    # 14 Hungarian, 15 침입 구역
    F.hungarian_fig(res["hungarian"], OUT / "14_hungarian.png")
    z = res["zone"]
    gs = test["single"][0]
    first = z["truth"][0][0] + 8 if z["truth"] else 300
    zone = IntrusionZone(tuple(z["rect"]), echo=False)
    an = VideoAnalyzer(MotionParams(), Tracker(), zone=zone)
    for i, f in enumerate(E.read_frames(S.DATA / gs["video"])):
        r = an.process(f)
        if i == first:
            F.zone_fig(an.draw(f, r, 30.0), z, gs["frames"], OUT / "15_zone.png")
            break


def _merge_mid(gt, e):
    """이벤트 안에서 두 사람의 정답 박스가 가장 많이 겹친 프레임."""
    from .tracker import iou
    best, arg = -1.0, (e["start"] + e["end"]) // 2
    for i in range(e["start"], e["end"] + 1):
        boxes = {o["id"]: o["bbox"] for o in gt["gt"][i] if o.get("bbox")}
        if "A" in boxes and "B" in boxes:
            v = iou(boxes["A"], boxes["B"])
            if v > best:
                best, arg = v, i
    return arg


if __name__ == "__main__":
    main()
