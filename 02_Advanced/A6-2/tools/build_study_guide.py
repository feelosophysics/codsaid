"""study/a6-2.template.html에 현재 결과·소스를 넣어 study/a6-2.html(단일 파일)을 만든다.

넣는 것: 결과 JSON에서 고른 수치와 곡선, 시계열 원자료(위젯 계산용), 오분류 썸네일, 축소한 결과 그림,
원본 Python 발췌(줄 번호 포함). 본문 숫자는 data-v 속성으로 DATA에서 읽어 오므로 실험을 다시 돌려도 어긋나지 않는다.

실행: uv run python tools/build_study_guide.py   (먼저 scripts/run_all.py)
"""
import ast
import base64
import hashlib
import io
import json

import numpy as np
import pandas as pd
from PIL import Image

from perfdiag.common import FIGURES, RESULTS, ROOT, load_json, utf8_console
from perfdiag.timeseries.data import SERIES, load_frame, prepare
from perfdiag.vision.data import CLASS_KO, FLOWERS
from perfdiag.vision.models import BLOCKS, TransferNet

STUDY = ROOT / "study"
TEMPLATE = STUDY / "a6-2.template.html"
OUTPUT = STUDY / "a6-2.html"
MANIFEST = STUDY / "source-manifest.json"

EXCERPTS = {
    "data.build_features": ("src/perfdiag/timeseries/data.py", "build_features"),
    "data.chronological_split": ("src/perfdiag/timeseries/data.py", "chronological_split"),
    "data.Prepared.train_rows": ("src/perfdiag/timeseries/data.py", "Prepared.train_rows"),
    "data.window_indices": ("src/perfdiag/timeseries/data.py", "window_indices"),
    "data.make_dataset": ("src/perfdiag/timeseries/data.py", "make_dataset"),
    "baselines.sma": ("src/perfdiag/timeseries/baselines.py", "sma"),
    "baselines.ema_path": ("src/perfdiag/timeseries/baselines.py", "ema_path"),
    "baselines.linear_lag": ("src/perfdiag/timeseries/baselines.py", "linear_lag"),
    "models.RNNForecaster": ("src/perfdiag/timeseries/models.py", "RNNForecaster"),
    "train.fit": ("src/perfdiag/timeseries/train.py", "fit"),
    "diagnosis.diagnose_forecast": ("src/perfdiag/diagnosis.py", "diagnose_forecast"),
    "diagnosis.diagnose_classification": ("src/perfdiag/diagnosis.py", "diagnose_classification"),
    "metrics.diebold_mariano": ("src/perfdiag/metrics.py", "diebold_mariano"),
    "vmodels.TransferNet": ("src/perfdiag/vision/models.py", "TransferNet"),
    "vtrain.AUGMENTATIONS": ("src/perfdiag/vision/train.py", "AUGMENTATIONS"),
    "transfer.analysis_models": ("scripts/vision_transfer.py", "analysis_models"),
    "deep.require_baselines": ("scripts/ts_deep.py", "require_baselines"),
    "hp.narrow": ("scripts/bonus_hparam_search.py", "narrow"),
    "hp.importance": ("scripts/bonus_hparam_search.py", "importance"),
}
FIGURE_FILES = {
    "ts_aapl_loss_curves": "AAPL: 실험 7개의 Train/Validation 손실 곡선",
    "ts_seoul_loss_curves": "서울 기온: 실험 7개의 Train/Validation 손실 곡선",
    "ts_aapl_prediction": "AAPL Test 구간 예측 vs 실제",
    "ts_seoul_prediction": "서울 기온 Test 구간 예측 vs 실제",
    "ts_aapl_baseline_bars": "AAPL 베이스라인 vs 딥러닝 Test MAE·RMSE",
    "ts_seoul_baseline_bars": "서울 기온 베이스라인 vs 딥러닝 Test MAE·RMSE",
    "ts_leakage_demo": "누수 체크포인트를 어긴 설정의 Test MAE",
    "vision_loss_curves": "Few-shot 전이 학습 Train/Validation 손실 곡선",
    "vision_shots_strategy": "사진 수별 전략 비교",
    "vision_confusion": "주 모델 혼동 행렬",
    "vision_error_tags": "오분류 원인 태그 통계",
    "bonus_hparam_search": "Random Search → Coarse-to-Fine 탐색",
    "bonus_attention": "LSTM·Attention·Transformer 비교와 Attention 가중치",
}


def read_text(path):
    return (ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def text_hash(path):
    return hashlib.sha256(read_text(path).encode("utf-8")).hexdigest()


def binary_hash(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def find_node(tree, qualname):
    nodes, node = tree.body, None
    for part in qualname.split("."):
        node = next(n for n in nodes if (isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == part)
                    or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) == part for t in n.targets)))
        nodes = getattr(node, "body", [])
    return node


def excerpt(path, qualname):
    source = read_text(path)
    node = find_node(ast.parse(source), qualname)
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    lines = source.split("\n")[start - 1:node.end_lineno]
    return {"file": path, "name": qualname, "start": start, "end": node.end_lineno, "text": "\n".join(lines)}


def shrink(path, width=1100):
    """그래프를 폭 1100px 이하, 256색 PNG로 줄인다 (선·글자는 색 수가 적어 거의 손실이 없다)."""
    image = Image.open(path).convert("RGB")
    if image.width > width:
        image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    image.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def thumb(path, size=132):
    image = Image.open(path).convert("RGB")
    w, h = image.size
    s = min(w, h)
    image = image.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((size, size), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=78)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def r(values, digits=5):
    return np.round(np.asarray(values, dtype=float), digits).tolist()


# ----------------------------------------------------------------------------- 시계열
def timeseries():
    out = {}
    for name, cfg in SERIES.items():
        prep = prepare(name)
        base = load_json(RESULTS / f"ts_baselines_{name}.json")
        deep = load_json(RESULTS / f"ts_deep_{name}.json")
        experiments = {}
        for key, e in deep["experiments"].items():
            best = next(s for s in e["seeds"] if s["seed"] == e["best_seed"])
            experiments[key] = {
                "label": e["label"], "role": e["role"], "mode": e["mode"], "arch": e["arch"],
                "model_kwargs": e["model_kwargs"], "parameters": e["parameters"], "seeds": len(e["seeds"]),
                "early_stopping": e["train_config"]["early_stopping"], "test_summary": e["test_summary"],
                "diagnosis": e["diagnosis"],
                "history": {"train": r(best["history"]["train_loss"]), "validation": r(best["history"]["validation_loss"]),
                            "best_epoch": best["history"]["best_epoch"]},
                "naive": {"train": best["metrics"]["train"]["naive_mse_scaled"],
                          "validation": best["metrics"]["validation"]["naive_mse_scaled"]},
                "validation_mae": best["metrics"]["validation"]["MAE"],
            }
        out[name] = {
            "title": cfg.title, "unit": cfg.unit, "with_mape": cfg.with_mape,
            "dates": [str(d) for d in prep.dates], "y": r(prep.y, 4),
            "splits": {k: [int(v[0]), int(v[-1])] for k, v in prep.splits.items()}, "split_info": prep.info,
            "first_target": prep.first_target, "feature_names": prep.feature_names,
            "baselines": base["metrics"], "best_baseline": base["best_by_validation"],
            "experiments": experiments, "final": deep["final"], "final_test": deep["final_test"],
            "improvement": deep["improvement_vs_baselines"], "dm": deep["diebold_mariano"],
            "test_pred_final": r(deep["experiments"][deep["final"]]["test_prediction"], 4),
            "test_pred_level": r(deep["experiments"]["lstm_level"]["test_prediction"], 4),
            "train_max": float(prep.y[prep.train_rows()].max()), "train_min": float(prep.y[prep.train_rows()].min()),
        }
    return out


# ----------------------------------------------------------------------------- 이미지
def vision():
    transfer = load_json(RESULTS / "vision_transfer.json")
    stats = load_json(RESULTS / "vision_error_stats.json")
    improve = load_json(RESULTS / "vision_improve.json") if (RESULTS / "vision_improve.json").exists() else None
    errors = pd.read_csv(RESULTS / "vision_errors.csv")
    extra = errors.set_index("file")[["wrong_models", "n_wrong_models", "reported_by", "second"]].to_dict("index")
    table = []
    for row in stats["table"]:
        row = {**row, **extra[row["file"]], "thumb": thumb(FLOWERS / row["file"])}
        table.append(row)
    runs = [{"name": x["name"], "shots": x["shots"], "strategy": x["strategy"], "label": x["label"],
             "train": x["train"]["accuracy"], "validation": x["validation"]["accuracy"], "test": x["test"]["accuracy"],
             "train_loss": x["train"]["loss"], "validation_loss": x["validation"]["loss"],
             "diagnosis": x["diagnosis"], "trainable": x["trainable_parameters"], "total": x["total_parameters"],
             "is_main": x["is_main"], "in_error_analysis": x["in_error_analysis"], "epochs": x["config"]["epochs"],
             "seconds": x["history"]["seconds"],
             "history": {"train": r(x["history"]["train_loss"], 4), "validation": r(x["history"]["validation_loss"], 4),
                         "best_epoch": x["history"]["best_epoch"]}} for x in transfer["runs"]]
    net = TransferNet(8, "full")
    blocks = {b: sum(p.numel() for p in getattr(net.net, b).parameters()) for b in BLOCKS}
    if improve:
        improve = {k: v for k, v in improve.items() if k != "runs"} | {
            "runs": {k: [{"seed": x["seed"], "train": x["train"]["accuracy"], "validation": x["validation"]["accuracy"],
                          "test": x["test"]["accuracy"], "diagnosis": x["diagnosis"]["label"]} for x in v]
                     for k, v in improve["runs"].items()}}
    return {"classes": transfer["classes"], "ko": CLASS_KO, "runs": runs, "blocks": blocks,
            "main": transfer["main"], "analysis_models": transfer["error_analysis_models"],
            "test_size": len(transfer["test_targets"]), "validation_size": transfer["validation_size"],
            "errors": table, "stats": {k: v for k, v in stats.items() if k != "table"}, "improve": improve}


def bonus():
    out = {}
    if (RESULTS / "bonus_hparam_search.json").exists():
        out["hparam"] = load_json(RESULTS / "bonus_hparam_search.json")
    if (RESULTS / "bonus_attention.json").exists():
        att = load_json(RESULTS / "bonus_attention.json")
        out["attention"] = {s: {k: {kk: vv for kk, vv in v.items() if kk != "attention_examples"} for k, v in d.items()}
                            for s, d in att.items()}
    return out


def build():
    data = {
        "code": {key: excerpt(path, name) for key, (path, name) in EXCERPTS.items()},
        "fig": {key: {"src": shrink(FIGURES / f"{key}.png"), "caption": caption, "file": f"figures/{key}.png"}
                for key, caption in FIGURE_FILES.items() if (FIGURES / f"{key}.png").exists()},
        "ts": timeseries(), "leakage": load_json(RESULTS / "ts_leakage.json"),
        "vision": vision(), "bonus": bonus(),
    }
    template = read_text("study/a6-2.template.html")
    marker = "/*__DATA__*/null"
    if template.count(marker) != 1:
        raise SystemExit("템플릿에 DATA 자리표시자가 정확히 하나 있어야 한다")
    html = template.replace(marker, json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    OUTPUT.write_text(html, encoding="utf-8", newline="\n")
    sources = sorted({p for p, _ in EXCERPTS.values()} | {"study/a6-2.template.html"}
                     | {p.relative_to(ROOT).as_posix() for p in RESULTS.glob("*.json")}
                     | {"results/vision_errors.csv", "annotations/error_tags.csv"}
                     | {SERIES[s].csv.relative_to(ROOT).as_posix() for s in SERIES})
    manifest = {
        "hash_mode": "UTF-8 텍스트는 CRLF를 LF로 바꾼 뒤 SHA-256, 그림은 원래 바이트의 SHA-256",
        "text": {path: text_hash(path) for path in sources},
        "binary": {f["file"]: binary_hash(f["file"]) for f in data["fig"].values()},
        "excerpts": {key: {k: v for k, v in e.items() if k != "text"} for key, e in data["code"].items()},
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"생성: {OUTPUT.relative_to(ROOT).as_posix()} ({OUTPUT.stat().st_size / 1024:.0f} KB), "
          f"발췌 {len(data['code'])}개, 그림 {len(data['fig'])}개, 오분류 썸네일 {len(data['vision']['errors'])}개")


if __name__ == "__main__":
    utf8_console()
    build()
