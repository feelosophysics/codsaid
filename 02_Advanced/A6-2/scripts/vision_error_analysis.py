"""오차 분석: 사람이 단 태그(annotations/error_tags.csv)로 통계와 태그별 오분류 갤러리를 만든다.

태그가 빠진 오분류가 있으면 멈춘다. 태그는 tools/build_tagging_page.py로 만든 HTML에서 달고 검수한다.
출력: results/vision_error_stats.json, figures/vision_error_gallery.png, figures/vision_error_tags.png

실행: uv run python scripts/vision_error_analysis.py
"""
import sys
from collections import Counter

import numpy as np
import pandas as pd
from PIL import Image

from perfdiag.common import RESULTS, ROOT, save_json, utf8_console
from perfdiag.plots import plt, save
from perfdiag.vision.data import CLASS_KO, FLOWERS

TAGS_CSV = ROOT / "annotations" / "error_tags.csv"
CATEGORIES = ["데이터 품질", "배경/잡음", "클래스 유사성", "라벨 오류", "모델 한계"]
COLORS = dict(zip(CATEGORIES, ["#d69e2e", "#805ad5", "#3182ce", "#e53e3e", "#4a5568"]))
REMEDY = {"데이터 품질": "밝기·대비·색 증강(ColorJitter), 저화질 사진 보강",
          "배경/잡음": "RandomResizedCrop으로 크기·위치 다양화, 가림 증강(RandomErasing)",
          "클래스 유사성": "더 깊은 층까지 미세 조정, 고해상도 입력, 헷갈리는 쌍의 사진 보강",
          "라벨 오류": "원본 데이터 정제(라벨 재확인)",
          "모델 한계": "모델 구조 변경·앙상블, 신뢰도 보정(temperature scaling)"}


def load():
    errors = pd.read_csv(RESULTS / "vision_errors.csv")
    if not TAGS_CSV.exists():
        sys.exit(f"{TAGS_CSV}가 없다. tools/build_tagging_page.py로 태깅 도구를 만들어 태그를 단다")
    tags = pd.read_csv(TAGS_CSV, dtype=str, encoding="utf-8-sig").fillna("")
    df = errors.merge(tags[["file", "primary_tag", "secondary_tags", "detail", "note", "tagged_by", "reviewed_by"]],
                      on="file", how="left").fillna("")
    missing = df[~df["primary_tag"].isin(CATEGORIES)]
    if len(missing):
        sys.exit(f"주 원인 태그가 없거나 잘못된 오분류 {len(missing)}건: {missing['file'].tolist()[:5]} …")
    df.insert(0, "no", range(1, len(df) + 1))
    return df


def statistics(df):
    n = len(df)
    primary = Counter(df["primary_tag"])
    detail = Counter(d for row in df["detail"] for d in row.split(";") if d)
    pairs = Counter(f"{t} → {p}" for t, p in zip(df["true"], df["pred"]))
    by_tag = {c: {"count": primary.get(c, 0), "share": primary.get(c, 0) / n,
                  "mean_confidence": float(df.loc[df["primary_tag"] == c, "confidence"].mean())
                  if primary.get(c) else None, "remedy": REMEDY[c]} for c in CATEGORIES}
    return {
        "n_errors": n, "reviewed": int((df["reviewed_by"] != "").sum()),
        "tagged_by": dict(Counter(df["tagged_by"])), "reviewed_by": dict(Counter(df["reviewed_by"].replace("", "(미검수)"))),
        "primary": by_tag, "detail": dict(detail.most_common()), "pairs": dict(pairs.most_common()),
        "high_confidence_errors": int((df["confidence"] >= 0.8).sum()),
        "dominant": max(CATEGORIES, key=lambda c: primary.get(c, 0)),
        "table": df[["no", "file", "true", "pred", "confidence", "primary_tag", "detail", "note", "tagged_by",
                     "reviewed_by"]].to_dict("records"),
    }


def thumb(path, size=200):
    image = Image.open(FLOWERS / path).convert("RGB")
    w, h = image.size
    s = min(w, h)
    return image.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((size, size))


def gallery(df, per_tag=6):
    groups = [(c, df[df["primary_tag"] == c].sort_values("confidence", ascending=False)) for c in CATEGORIES]
    groups = [(c, g) for c, g in groups if len(g)]
    fig, axes = plt.subplots(len(groups), per_tag, figsize=(per_tag * 2.3, len(groups) * 2.75), squeeze=False)
    for row, (category, g) in enumerate(groups):
        for col in range(per_tag):
            ax = axes[row, col]
            ax.axis("off")
            if col >= len(g):
                continue
            r = g.iloc[col]
            ax.imshow(thumb(r["file"]))
            ax.set_title(f"#{r['no']} {CLASS_KO[r['true']]}→{CLASS_KO[r['pred']]}\n신뢰도 {r['confidence']:.2f}"
                         + (f" · {r['detail'].split(';')[0].split('(')[0]}" if r["detail"] else ""), fontsize=8)
        axes[row, 0].text(-0.08, 0.5, f"{category}\n({len(g)}건)", transform=axes[row, 0].transAxes, ha="right",
                          va="center", fontsize=11, color=COLORS[category], fontweight="bold")
    fig.suptitle("오분류 이미지 갤러리 — 주 원인 태그별 (태그마다 신뢰도 높은 순 최대 6장, 실제→예측)", fontsize=12)
    fig.tight_layout(rect=(0.08, 0, 1, 0.97))
    return save(fig, "vision_error_gallery.png")


def tag_chart(stats):
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8), gridspec_kw={"width_ratios": [1, 1.2, 1.2]})
    counts = [stats["primary"][c]["count"] for c in CATEGORIES]
    bars = axes[0].barh(CATEGORIES[::-1], counts[::-1], color=[COLORS[c] for c in CATEGORIES[::-1]])
    for bar, value in zip(bars, counts[::-1]):
        axes[0].text(value, bar.get_y() + bar.get_height() / 2, f" {value} ({value / stats['n_errors']:.0%})", va="center")
    axes[0].set_title(f"주 원인 태그 (오분류 {stats['n_errors']}건)")
    detail = list(stats["detail"].items())[:10]
    axes[1].barh([d for d, _ in detail][::-1], [v for _, v in detail][::-1], color="#718096")
    axes[1].set_title("세부 태그 (중복 가능, 상위 10)")
    pairs = list(stats["pairs"].items())[:10]
    axes[2].barh([p for p, _ in pairs][::-1], [v for _, v in pairs][::-1], color="#3182ce")
    axes[2].set_title("자주 틀린 (실제 → 예측) 쌍")
    fig.tight_layout()
    return save(fig, "vision_error_tags.png")


def main():
    utf8_console()
    df = load()
    stats = statistics(df)
    save_json(RESULTS / "vision_error_stats.json", stats)
    print(f"오분류 {stats['n_errors']}건, 검수 {stats['reviewed']}건, 작성자 {stats['tagged_by']}")
    for c in CATEGORIES:
        p = stats["primary"][c]
        conf = "-" if p["mean_confidence"] is None else f"{p['mean_confidence']:.2f}"
        print(f"  {c:<8} {p['count']:>3}건 {p['share']:>5.0%}  평균 신뢰도 {conf}")
    print(f"저장: {gallery(df).name}, {tag_chart(stats).name}")


if __name__ == "__main__":
    main()
