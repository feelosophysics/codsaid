"""Six required charts, tabular evidence and synthetic-data interpretations."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

SEGMENT_COLORS = {"VIP": "#0072B2", "Loyal": "#E69F00", "New": "#009E73",
                  "Inactive": "#D55E00", "Regular": "#CC79A7"}


def create_charts(analyzer, output_dir):
    """Save charts and return paths. ASCII labels work without extra system fonts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", palette="colorblind")
    df, rfm = analyzer.df, analyzer.rfm
    paths = []

    def save(fig, filename):
        fig.tight_layout()
        path = output_dir / filename
        fig.savefig(path, dpi=140)
        plt.close(fig)
        paths.append(path)

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.histplot(data=df, x="unit_price", bins=35, ax=ax)
    ax.set(title="Distribution of recorded unit prices", xlabel="Unit price (KRW)", ylabel="Order lines")
    save(fig, "01_histogram.png")

    treated = analyzer.treat_outliers("shipping_days")
    comparison = pd.DataFrame({"Before": df.shipping_days, "After IQR clipping": treated})
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(data=comparison, ax=ax)
    ax.set(title="Shipping days: before / after illustrative treatment", xlabel="Treatment", ylabel="Shipping days")
    save(fig, "02_boxplot.png")

    counts = rfm.segment.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 4))
    positions = range(len(counts))
    ax.bar(positions, counts.values, color=[SEGMENT_COLORS[name] for name in counts.index])
    ax.set_xticks(list(positions), counts.index.to_list())
    ax.set(title="Customer counts by RFM segment", xlabel="Segment", ylabel="Customers")
    save(fig, "03_bar.png")

    numeric = df[["unit_price", "quantity", "amount", "shipping_days", "image_mean", "image_std"]]
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(numeric.corr(), annot=True, fmt=".2f", vmin=-1, vmax=1, center=0, cmap="vlag", ax=ax)
    ax.set(title="Pearson correlations at order-line grain", xlabel="Variable", ylabel="Variable")
    save(fig, "04_heatmap.png")

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.scatterplot(data=rfm.reset_index(), x="frequency", y="monetary", hue="segment",
                    palette=SEGMENT_COLORS, alpha=0.65, ax=ax)
    ax.set(title="Purchase frequency and total spend", xlabel="Distinct orders", ylabel="Total spend (KRW)")
    ax.legend(title="Segment", fontsize=8)
    save(fig, "05_scatter.png")

    # Match the purchase population used for RFM; refunds are not netted here.
    valid = df.customer_id.notna() & df.order_id.notna() & df.order_date.notna() & df.amount.gt(0) & df.quantity.gt(0) & df.unit_price.gt(0)
    monthly = df.loc[valid].groupby(df.loc[valid, "order_date"].dt.to_period("M"))["amount"].sum()
    periods = pd.period_range(monthly.index.min(), monthly.index.max(), freq="M")
    monthly = monthly.reindex(periods, fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(monthly.index.to_timestamp(), monthly.values, marker="o")
    ax.set(title="Monthly positive-purchase revenue (boundary months may be partial)", xlabel="Order month", ylabel="Revenue (KRW)")
    fig.autofmt_xdate()
    save(fig, "06_line.png")
    return paths


def business_insights(summary):
    """Return evidence/action/falsifiability triples; no measured campaign effects."""
    paragraphs = []
    strategies = {
        "VIP": ("멤버십 혜택을 소규모 대조군 실험으로 제공", "재구매 유지", "혜택 비용과 대조군의 재구매율이 필요하다. 비용 증가가 추가 이익보다 크면 제안을 기각한다."),
        "Inactive": ("최근 구매 간격을 확인하고 복귀 메시지를 대조군과 비교", "재구매 회복", "품목별 정상 구매 주기와 수신 동의 정보가 필요하다. 긴 구매 주기가 정상이라면 이탈 해석을 수정한다."),
        "New": ("첫 구매 후 사용 안내와 다음 구매 추천을 대조군과 비교", "두 번째 구매 전환", "첫 구매 후 동일한 추적 기간과 반품 정보가 필요하다. 전환율 차이가 없으면 추천 효과를 주장할 수 없다."),
        "Loyal": ("반복 구매 품목의 재입고 알림을 대조군과 비교", "구매 편의 개선", "재고와 알림 비용이 필요하다. 자연 재구매와 차이가 없으면 효과를 주장할 수 없다."),
        "Regular": ("구매 간격별 안내를 소규모 실험으로 비교", "추가 구매 전환", "품목별 구매 주기가 필요하다. 실험 차이가 없으면 효과를 주장할 수 없다."),
    }
    for segment in ["VIP", "Inactive", "New", "Loyal", "Regular"]:
        if segment not in summary.index:
            continue
        row = summary.loc[segment]
        action, effect, verification = strategies[segment]
        paragraphs.append(
            f"### {segment}\n\n"
            f"- 근거: 고객 {int(row.customers)}명({row.customer_share_pct:.1f}%), "
            f"매출 비중 {row.revenue_share_pct:.1f}%, 평균 구매 횟수 {row.mean_frequency:.2f}회, "
            f"평균 최근 구매 경과 {row.mean_recency:.1f}일. `segment_summary.csv`와 `03_bar.png`, `05_scatter.png` 참조.\n"
            f"- 실행: {segment} 대상 → {action} → 기대 효과: {effect}. 아직 검증하지 않은 가설이며 효과 크기를 측정하지 않았다.\n"
            f"- 검증: {verification}\n")
    return "\n".join(paragraphs)


def statistical_interpretation(analyzer):
    stats = analyzer.summarize()
    price = stats.loc["unit_price"]
    pairs = [("unit_price", "amount"), ("quantity", "amount")]
    lines = [
        f"거래 행 기준 단가 평균 {price['mean']:.0f}원, 중앙값 {price['50%']:.0f}원, "
        f"표준편차 {price['std']:.0f}원, Q1 {price['25%']:.0f}원, Q3 {price['75%']:.0f}원이다. "
        "평균·중앙값 차이와 히스토그램을 함께 봐야 고가 상품의 영향을 판단할 수 있다."]
    for left, right in pairs:
        coefficient = analyzer.df[left].corr(analyzer.df[right])
        lines.append(f"{left}–{right} Pearson r={coefficient:.3f}. "
                     "amount=unit_price×quantity라는 계산 관계가 있으므로 독립적인 원인이나 마케팅 효과의 증거로 해석하지 않는다.")
    return "\n\n".join(lines)


def write_report(analyzer, output_dir):
    """Export facts and explanations; notebook uses the same computed objects."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    analyzer.df.to_csv(output_dir / "processed_transactions.csv", index=False)
    analyzer.rfm.to_csv(output_dir / "rfm_customers.csv")
    summary = analyzer.segment_summary()
    summary.to_csv(output_dir / "segment_summary.csv")
    analyzer.summarize().to_csv(output_dir / "statistics.csv")
    analyzer.df[["unit_price", "quantity", "amount", "shipping_days", "image_mean", "image_std"]].corr().to_csv(output_dir / "correlations.csv")
    (output_dir / "audit.json").write_text(json.dumps(analyzer.audit, indent=2, ensure_ascii=False,
                                                     default=lambda value: value.item()), encoding="utf-8")
    chart_paths = create_charts(analyzer, output_dir / "figures")
    audit = analyzer.audit
    outlier = audit["outliers"]["shipping_days"]
    missing = audit["imputation"]
    body = (
        "# A1-1 분석 결과\n\n"
        "이 기본 실행은 고정 난수로 만든 합성 데이터다. 상품 이미지도 생성한 RGB 배열이며 실제 상품 사진이 아니다. "
        "고객 행동을 의도적으로 구성했으므로 아래 수치는 분석 구현을 설명하는 예시다. "
        "실제 시장 결론이나 세분화의 외부 타당성 검증으로 사용할 수 없다. 외부 데이터를 넣었다면 이 출처 설명을 별도로 갱신해야 한다.\n\n"
        f"입력 {audit['input_rows']:,}행, {len(analyzer.df.columns)}컬럼. 상품 {audit['products']}개. "
        f"유효 구매 {audit['rfm']['eligible_rows']:,}행, 제외 {audit['rfm']['excluded_rows']}행, "
        f"고객 {audit['rfm']['customers']}명, 주문 {audit['rfm']['orders']:,}건이다. "
        "한 주문의 여러 상품 행을 합쳐 고유 주문 수로 구매 횟수를 계산해야 한다.\n\n"
        f"상품 결측치 대치 수: {missing['product_values']}; 거래 행 대치 수: {missing['line_values']}. "
        f"카테고리별 {missing['strategy']}을 사용하고 그룹 전체가 비면 전체 통계로 보완했다. "
        "상품 통계와 판매 빈도를 구분하며 고객 ID·날짜·거래 금액은 추정하지 않는다.\n\n"
        f"배송 일수 IQR 경계는 [{outlier['lower']:.2f}, {outlier['upper']:.2f}]일이며 "
        f"{outlier['count']}행을 표시했다. 차트는 경계로 클리핑한 비교값을 보여준다. "
        "장기 배송이 오류인지는 별도 확인이 필요하며 원본과 RFM 거래 금액은 유지했다.\n\n"
        "## 통계 해석\n\n" + statistical_interpretation(analyzer) + "\n\n"
        "이미지 평균·표준편차는 밝기와 픽셀 변동의 요약값이다. 의미·품질·상품 종류를 판별한 값이 아니다.\n\n"
        "월별 매출은 관측 기간의 첫·마지막 달이 일부 날짜만 포함할 수 있다. "
        "특히 기본 데이터의 10월은 9일까지이므로 완전한 9월과 단순 비교해 매출 감소를 주장하지 않는다.\n\n"
        "## 고객 세분화\n\n"
        f"기준일 {audit['rfm']['reference_date']}. 기본값은 최종 유효 거래일 다음 날이다. "
        "관측 기간 전체의 고유 주문 수와 구매 금액을 사용한다. R은 작을수록, F·M은 클수록 높은 1–5 점수다. "
        "동점에는 같은 점수를 부여하므로 점수별 고객 수는 같지 않을 수 있다.\n\n"
        f"최근 기준 {audit['rfm']['recent_days']}일, 비활성 기준 {audit['rfm']['inactive_days']}일, "
        f"반복 구매 기준 {audit['rfm']['loyal_orders']}회, VIP 금액 경계 {audit['rfm']['vip_monetary_cutoff']:.0f}원. "
        "Inactive → New → VIP → Loyal → Regular 순서로 상호 배타적으로 분류한다. "
        "Inactive는 구매 공백을 나타내며 확정 이탈을 의미하지 않는다.\n\n"
        "## 비즈니스 가설\n\n" + business_insights(summary) + "\n"
        "## 차트\n\n" + "\n".join(f"![{path.stem}](figures/{path.name})\n" for path in chart_paths))
    (output_dir / "analysis_summary.md").write_text(body, encoding="utf-8")
    return chart_paths
