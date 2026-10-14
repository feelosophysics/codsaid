"""Optional mission extensions; image calculations use NumPy only.

Plotly is imported only by the interactive RFM chart, as allowed by bonus 3.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd


def image_features(images, bins=8):
    """Normalized intensity histograms and mean absolute neighbour differences.

    RGB is converted to luminance with weights (0.2126, 0.7152, 0.0722).
    The last bin includes 255. No loop traverses images or pixels; bincount
    accumulates all image/bin pairs together. Single-pixel axes add no edges.
    """
    images = np.asarray(images, dtype=np.float64)
    if images.ndim not in (3, 4) or any(n == 0 for n in images.shape):
        raise ValueError('Expected nonempty (N,H,W) or (N,H,W,3) images')
    if not np.isfinite(images).all() or images.min() < 0 or images.max() > 255:
        raise ValueError('Image pixels must be finite and in [0,255]')
    if not isinstance(bins, int) or not 2 <= bins <= 256:
        raise ValueError('bins must be an integer in [2,256]')
    if images.ndim == 4:
        if images.shape[-1] != 3:
            raise ValueError('Colour images require exactly three RGB channels')
        gray = images @ np.array([0.2126, 0.7152, 0.0722])
    else:
        gray = images
    n, h, w = gray.shape
    labels = np.minimum((gray / 256 * bins).astype(int), bins - 1)
    offsets = np.arange(n)[:, None, None] * bins
    counts = np.bincount((labels + offsets).ravel(), minlength=n * bins).reshape(n, bins)
    hist = counts / (h * w)
    edge_count = h * (w - 1) + (h - 1) * w
    edge_sum = (np.abs(np.diff(gray, axis=2)).sum(axis=(1, 2))
                + np.abs(np.diff(gray, axis=1)).sum(axis=(1, 2)))
    edges = edge_sum / edge_count if edge_count else np.zeros(n)
    entropy = -(hist * np.log2(np.maximum(hist, np.finfo(float).tiny))).sum(axis=1)
    frame = pd.DataFrame(hist, columns=[f'image_hist_{i}' for i in range(bins)])
    frame['image_edge_mean'] = edges
    frame['image_entropy'] = entropy
    return frame


def signup_cohorts(transactions, customers, observation_end=None):
    """Monthly purchase activity / all signups, with incomplete months masked.

    This is signup-cohort activity retention, not 'ever returned' cumulative
    retention or first-purchase cohorts. Each customer counts once per month;
    people with no purchase remain in the signup denominator. Only fully
    observed calendar months are reported, including month zero.
    """
    required = {'customer_id', 'signup_date'}
    if not required <= set(customers):
        raise ValueError('customers requires customer_id and signup_date')
    if customers.empty or customers.customer_id.isna().any() or customers.customer_id.duplicated().any():
        raise ValueError('customers requires unique, nonmissing customer IDs')
    customers = customers[list(required)].copy()
    customers['signup_date'] = pd.to_datetime(customers.signup_date, errors='raise').dt.normalize()
    if customers.signup_date.isna().any():
        raise ValueError('signup_date must not be missing')
    dates = pd.to_datetime(transactions.order_date, errors='coerce').dt.normalize()
    end = pd.Timestamp(observation_end).normalize() if observation_end is not None else dates.max()
    if pd.isna(end):
        raise ValueError('An observation_end date is required without dated purchases')
    if (customers.signup_date > end).any():
        raise ValueError('Signups must not follow observation_end')
    valid = (transactions.customer_id.notna() & dates.notna() & transactions.amount.gt(0)
             & transactions.quantity.gt(0) & transactions.unit_price.gt(0))
    purchases = transactions.loc[valid, ['customer_id']].copy()
    purchases['order_date'] = dates[valid]
    if (purchases.order_date > end).any():
        raise ValueError('observation_end must not precede observed purchases')
    purchases = purchases.merge(customers, on='customer_id', how='left', validate='many_to_one')
    if purchases.signup_date.isna().any():
        raise ValueError('Every purchasing customer needs a signup date')
    if (purchases.order_date < purchases.signup_date).any():
        raise ValueError('Purchase date must not precede signup')
    customers['cohort'] = customers.signup_date.dt.to_period('M')
    purchases['cohort'] = purchases.signup_date.dt.to_period('M')
    purchases['month'] = purchases.order_date.dt.to_period('M')
    purchases['age'] = purchases['month'].astype('int64') - purchases.cohort.astype('int64')
    sizes = customers.groupby('cohort').size().rename('signups')
    age_max = max(0, end.to_period('M').ordinal - sizes.index.min().ordinal)
    counts = (purchases.drop_duplicates(['customer_id', 'month']).groupby(['cohort', 'age'])
              .size().unstack(fill_value=0).reindex(index=sizes.index, columns=range(age_max + 1), fill_value=0))
    # NaN means not fully observed, rather than a measured zero retention rate.
    complete = np.array([[(cohort + age).end_time.normalize() <= end for age in counts.columns]
                         for cohort in counts.index])
    counts = counts.astype(float).where(complete)
    rates = counts.div(sizes, axis=0)
    return sizes, counts, rates


def interactive_rfm(rfm):
    """Return Plotly scatter traces with customer-level hover and segment toggles."""
    import plotly.graph_objects as go
    from .report import SEGMENT_COLORS

    fig = go.Figure()
    for segment, group in rfm.groupby('segment', sort=True):
        custom = np.column_stack([group.index.astype(str), group.recency,
                                  group.r_score, group.f_score, group.m_score])
        fig.add_trace(go.Scatter(x=group.frequency, y=group.monetary, mode='markers', name=segment,
                                marker={'color': SEGMENT_COLORS[segment], 'size': 9, 'opacity': 0.75},
                                customdata=custom,
                                hovertemplate=('%{customdata[0]}<br>Orders: %{x}<br>Spend: %{y:,.0f} KRW'
                                               '<br>Recency: %{customdata[1]} days'
                                               '<br>R/F/M scores: %{customdata[2]}/%{customdata[3]}/%{customdata[4]}'
                                               '<extra>%{fullData.name}</extra>')))
    fig.update_layout(title='Synthetic customers: purchase frequency and spend',
                      xaxis_title='Distinct orders', yaxis_title='Positive-purchase spend (KRW)',
                      template='plotly_white', height=550, legend_title_text='Click to show/hide a segment',
                      margin={'l': 60, 'r': 20, 't': 60, 'b': 60})
    return fig


def write_bonus(analyzer, output_dir, customers_path=None, observation_end=None):
    """Export bonus evidence separately so the six required figures stay stable."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    out = Path(output_dir) / 'bonus'
    out.mkdir(parents=True, exist_ok=True)
    features = image_features(analyzer.images)
    products = analyzer.products[['product_id', 'image_index']].copy()
    products = products.join(features, on='image_index')
    products.to_csv(out / 'image_features.csv', index=False)
    for column in features:
        analyzer.df[column] = features[column].to_numpy()[analyzer.df.image_index.to_numpy(dtype=int)]
    analyzer.df.to_csv(out / 'transactions_with_image_features.csv', index=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(np.arange(8), features.filter(like='image_hist_').mean())
    axes[0].set(title='Mean normalized luminance histogram', xlabel='Bin (0..255, width 32)', ylabel='Pixel fraction')
    axes[1].scatter(analyzer.images.std(axis=tuple(range(1, analyzer.images.ndim))), features.image_edge_mean)
    axes[1].set(title='Pixel variation versus local edges', xlabel='Pixel standard deviation', ylabel='Mean neighbour difference')
    fig.tight_layout(); fig.savefig(out / 'image_features.png', dpi=140); plt.close(fig)

    customer_file = Path(customers_path) if customers_path else analyzer.data_path.parent / 'customers.csv'
    if not customer_file.exists():
        raise ValueError('Bonus signup cohorts need customers.csv; provide --customers-path or use --skip-bonus')
    customers = pd.read_csv(customer_file, dtype={'customer_id': 'string'})
    sizes, counts, rates = signup_cohorts(analyzer.df, customers, observation_end)
    sizes.to_csv(out / 'cohort_sizes.csv')
    counts.to_csv(out / 'cohort_counts.csv')
    rates.to_csv(out / 'cohort_retention.csv')
    fig, ax = plt.subplots(figsize=(max(8, rates.shape[1] * .6), max(4, rates.shape[0] * .4)))
    if rates.notna().any().any():
        sns.heatmap(rates, mask=rates.isna(), vmin=0, vmax=1, cmap='YlGnBu', annot=True, fmt='.0%', ax=ax)
    else:
        ax.text(.5, .5, 'No complete calendar months observed', ha='center', transform=ax.transAxes)
    ax.set(title='Signup-cohort purchase activity (blank = not fully observed)',
           xlabel='Months since signup', ylabel='Signup month')
    fig.tight_layout(); fig.savefig(out / 'cohort_retention.png', dpi=140); plt.close(fig)

    rfm = analyzer.rfm
    chart = interactive_rfm(rfm)
    fragment = chart.to_html(full_html=False, include_plotlyjs=True, div_id='rfm-plot',
                             config={'responsive': True, 'displaylogo': False})
    page = ('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>A1-1 RFM 탐색</title><body style="margin:0 auto;max-width:1100px;padding:20px;font-family:system-ui">'
            '<h1>고객 RFM 탐색</h1><p>고정 난수로 생성한 합성 고객 240명의 예시입니다. 실제 고객 정보가 아닙니다. '
            '점에 마우스를 올리면 고객별 R/F/M을 확인할 수 있습니다. 범례를 누르면 그룹을 숨기거나 표시하고, '
            '드래그하면 확대할 수 있습니다. 도구 모음에서 그림을 저장할 수 있습니다.</p>' + fragment + '</body></html>')
    (out / 'rfm_interactive.html').write_text(page, encoding='utf-8')
    summary = {'products': len(products), 'histogram_bins': 8, 'feature_columns': list(features),
               'histogram_sum_max_error': float(np.abs(features.filter(like='image_hist_').sum(axis=1) - 1).max()),
               'signups': int(sizes.sum()), 'cohorts': len(sizes),
               'observation_end': str(pd.Timestamp(observation_end).date() if observation_end else analyzer.df.order_date.max().date()),
               'fully_observed_cells': int(rates.notna().sum().sum()), 'masked_cells': int(rates.isna().sum().sum()),
               'interactive_customers': len(rfm), 'interactive_segments': int(rfm.segment.nunique())}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'README.md').write_text(
        '# A1-1 보너스 결과\n\n'
        '이미지 피처는 NumPy로 직접 계산한 8구간 정규화 히스토그램·이웃 픽셀 차이·엔트로피다. '
        '상품별 결과는 image_features.csv, 거래에 연결한 결과는 transactions_with_image_features.csv에 있다. '
        '밝기와 질감의 요약이며 의미·품질을 판별한 값이 아니다.\n\n'
        '코호트는 customers.csv의 가입 월을 기준으로 한다. 가입 고객 전체를 분모로, '
        '해당 경과 월에 양수 구매한 고유 고객 수를 분자로 사용한다. 미구매자도 분모에 포함한다. '
        'month 0은 가입 월의 구매 활동률이며 반드시 100%가 아니다. '
        f"관측 종료일은 {summary['observation_end']}이다. 월말까지 관측하지 않은 칸은 NaN/공백으로 남긴다. "
        '공백을 재구매율 0%로 해석하면 안 된다. 합성 가입일이므로 실제 유지율의 근거가 아니다.\n\n'
        '![이미지 피처](image_features.png)\n\n![가입 코호트](cohort_retention.png)\n\n'
        '[오프라인 Plotly RFM 차트](rfm_interactive.html): 확대·hover·범례 그룹 선택·PNG 저장. '
        'Plotly는 이 보너스 시각화에서만 사용한다.\n', encoding='utf-8')
    return summary
