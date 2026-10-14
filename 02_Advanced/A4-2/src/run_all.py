"""모든 평가와 보너스 실험을 실행하고 outputs/에 저장한다.

    uv run python -m src.run_all              # 1~2분 (보너스 2 학습 곡선이 대부분)
    uv run python -m src.run_all --quick      # 보너스 2를 n ≤ 1000까지만

BLAS 스레드를 2개로 묶는다(다른 작업과 함께 돌려도 CPU를 다 쓰지 않게). 이미 정해 두었으면 그 값을 쓴다.
"""
from __future__ import annotations

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "2")

import argparse  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

from . import bonus_tfidf, eval_sentiment  # noqa: E402
from .aspect import evaluate as evaluate_aspects  # noqa: E402
from .data import load_knu, load_splits  # noqa: E402
from .eval_extraction import evaluate_extraction, evaluate_masking  # noqa: E402
from .lexicon import knu_entries, load_modifiers, load_sentiment_tsv  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
HANDMADE = ROOT / "data" / "handmade"


def save(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def ablation_figure(sent: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    for name in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"):
        if any(name in f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    labels = [r["step"].split(" ", 1)[0] for r in sent["test"]["ablation"]]
    for split, color in (("dev", "#2a78d6"), ("test", "#eb6834")):
        ys = [r["accuracy"] for r in sent[split]["ablation"]]
        ax.plot(range(len(ys)), ys, color=color, linewidth=2, marker="o", markersize=5,
                label=f"{split} 1,000건" + (" (사전·규칙을 만든 집합)" if split == "dev" else " (규칙 고정 후 1회 평가)"))
        ax.annotate(f"{ys[-1]:.3f}", (len(ys) - 1, ys[-1]), textcoords="offset points", xytext=(8, 0), va="center",
                    fontsize=8, color="#52514e")
        ax.annotate(f"{ys[0]:.3f}", (0, ys[0]), textcoords="offset points", xytext=(-8, 0), va="center", ha="right",
                    fontsize=8, color="#52514e")
    ax.axvspan(-0.4, 4.4, color="#e6e5e0", alpha=0.35, linewidth=0)
    ax.text(2, 0.695, "필수 범위", ha="center", fontsize=8, color="#52514e")
    ax.text(6.5, 0.695, "확장 규칙", ha="center", fontsize=8, color="#52514e")
    ax.set_xticks(range(len(labels)))
    short = ["사전", "+강조", "+부정", "+부정\n+강조", "+이중부정", "+이모티콘", "+대조", "+고립\n부정어", "+평점"]
    ax.set_xticklabels([f"{lab}\n{s}" for lab, s in zip(labels, short)], fontsize=7)
    ax.set_xlim(-0.6, len(labels) - 0.2)
    ax.set_ylim(0.69, 0.83)
    ax.set_ylabel("정확도", color="#52514e")
    ax.set_title("규칙을 하나씩 더할 때 감성 분류 정확도 (NSMC)", fontsize=11, color="#0b0b0b", loc="left")
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors="#52514e", labelsize=7)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def errors_markdown(sent: dict, annotations: list[dict]) -> str:
    by_id = {e["id"]: e for e in sent["test_errors"]}
    lines = ["# test 오분류 사례 (최종 규칙)", "",
             f"전체 오분류 {len(sent['test_errors'])}건 중 단서 없음(점수 0 → 기본값 부정) "
             f"{sum(e['tie'] for e in sent['test_errors'])}건. 아래는 원인을 직접 분류한 {len(annotations)}건이다.", ""]
    for a in annotations:
        e = by_id.get(a["id"])
        if not e:
            continue
        lines += [f"## [{a['category']}] {e['text']}", "",
                  f"- 정답 {'긍정' if e['label'] else '부정'}, 예측 {'긍정' if e['pred'] else '부정'}, 점수 {e['score']:+g}",
                  f"- 근거: {', '.join(f'{s}({v:+g})' for s, v in e['evidence']) or '없음'}",
                  f"- 원인: {a['cause']}", ""]
    return "\n".join(lines)


def main(argv=None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="보너스 2를 n ≤ 1000까지만 실행")
    args = ap.parse_args(argv)
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    splits = load_splits()
    knu = load_knu()
    print(f"데이터: dev {len(splits['dev'])}, test {len(splits['test'])}, pool {len(splits['pool'])}")

    lex = load_sentiment_tsv()
    lexicon_stats = {
        "custom_entries": len(lex),
        "custom_by_domain": {d: sum(e.domain == d for e in lex) for d in ("general", "movie", "service")},
        "custom_by_pos": {p: sum(e.pos == p for e in lex) for p in ("P", "N", "E")},
        "modifiers": len(load_modifiers()),
        "knu": knu_entries(knu)[1],
    }
    save("lexicon_stats.json", lexicon_stats)
    print("사전:", lexicon_stats["custom_entries"], lexicon_stats["custom_by_domain"])

    print("[1/5] 감성 분석 평가")
    sent = eval_sentiment.run(splits, knu)
    save("sentiment_eval.json", sent)
    ablation_figure(sent, OUT / "sentiment_ablation.png")
    annotations = json.loads((HANDMADE / "test_error_annotations.json").read_text(encoding="utf-8"))
    (OUT / "sentiment_errors.md").write_text(errors_markdown(sent, annotations), encoding="utf-8")
    for row in sent["test"]["ablation"]:
        print(f"  {row['step']:28s} test acc={row['accuracy']:.3f} macroF1={row['macro_f1']:.3f}")

    print("[2/5] 정보 추출 평가")
    ext = evaluate_extraction()
    save("extraction_eval.json", ext)
    for t, v in ext["per_type"].items():
        print(f"  {t:6s} P={v['precision']:.3f} R={v['recall']:.3f} F1={v['f1']:.3f} 정규화={v['normalization_accuracy']:.3f}")

    print("[3/5] 마스킹 평가 (보너스 1)")
    msk = evaluate_masking()
    save("masking_eval.json", msk)
    print(f"  유출 {len(msk['leaks'])}/{msk['n_gold']}")

    print("[4/5] 속성 기반 감성 (보너스 3)")
    asp = {link: evaluate_aspects(link=link) for link in ("preceding", "nearest")}
    save("aspect_eval.json", asp)
    for link, r in asp.items():
        print(f"  {link:9s} 쌍 F1={r['pair']['f1']:.3f}  문장 단위 기준선 F1={r['sentence_baseline']['f1']:.3f}")

    print("[5/5] 규칙 vs TF-IDF (보너스 2)")
    sizes = [s for s in bonus_tfidf.SIZES if s <= 1000] if args.quick else bonus_tfidf.SIZES
    tf = bonus_tfidf.run(splits, sizes, log=print)
    save("rule_vs_tfidf.json", tf)
    bonus_tfidf.plot(tf, OUT / "rule_vs_tfidf.png")

    summary = {
        "sentiment_test": {r["step"]: round(r["accuracy"], 4) for r in sent["test"]["ablation"]},
        "sentiment_dev": {r["step"]: round(r["accuracy"], 4) for r in sent["dev"]["ablation"]},
        "extraction_micro_f1": round(ext["micro"]["f1"], 4),
        "masking_leaks": len(msk["leaks"]),
        "aspect_pair_f1": round(asp["preceding"]["pair"]["f1"], 4),
        "tfidf_crossover_n": tf["crossover_n"],
        "seconds": round(time.time() - t0, 1),
    }
    save("summary.json", summary)
    print(f"완료 {summary['seconds']}초 → {OUT}")


if __name__ == "__main__":
    main()
