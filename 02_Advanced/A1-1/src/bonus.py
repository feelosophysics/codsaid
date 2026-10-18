"""이미지 피처·가입 코호트·대화형 RFM으로 분석을 확장한다.

이미지 계산은 NumPy 배열 연산을 사용한다. Plotly는 보너스 시각화에만 쓴다.
필수 분석을 먼저 이해한 뒤 image_features → signup_cohorts 순으로 읽는다.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd


def image_features(images, bins=8):
    """이미지별 밝기 분포·이웃 차이·엔트로피를 숫자로 요약한다.

    Args:
        images (numpy.ndarray): (N,H,W) 흑백 또는 (N,H,W,3) RGB 배열.
            N은 이미지 수, H·W는 높이·너비. 픽셀은 유한한 0~255 숫자다.
        bins (int): 밝기를 나눌 구간 수. 2~256, 기본값은 8.

    Returns:
        pandas.DataFrame: 이미지당 한 행인 (N, bins+2) 표.
            image_hist_*는 픽셀 비율(행 합=1), image_edge_mean은 이웃 차이,
            image_entropy는 밝기 구간 분포의 엔트로피(bit)다.

    Raises:
        ValueError: 빈 축·지원하지 않는 배열 모양·픽셀 범위·구간 수인 경우.
    """
    # asarray는 입력을 배열로 다룬다. float64로 바꿔 음수 차이와 소수 계산을 한다.
    # uint8 상태에서 작은 값-큰 값을 계산하면 음수가 올바르게 표현되지 않을 수 있다.
    images = np.asarray(images, dtype=np.float64)
    if images.ndim not in (3, 4) or any(n == 0 for n in images.shape):
        raise ValueError('Expected nonempty (N,H,W) or (N,H,W,3) images')
    if not np.isfinite(images).all() or images.min() < 0 or images.max() > 255:
        raise ValueError('Image pixels must be finite and in [0,255]')
    if not isinstance(bins, int) or not 2 <= bins <= 256:
        raise ValueError('bins must be an integer in [2,256]')
    if images.ndim == 4:
        # shape[-1]은 마지막 축의 크기다. 여기서는 RGB 세 채널만 허용한다.
        if images.shape[-1] != 3:
            raise ValueError('Colour images require exactly three RGB channels')
        # @는 마지막 RGB 축과 가중치의 곱을 합한다. (N,H,W,3) → (N,H,W).
        # 녹색에 큰 가중치를 주는 간단한 밝기 요약이며 정밀한 색공간 변환은 아니다.
        gray = images @ np.array([0.2126, 0.7152, 0.0722])
    else:
        gray = images
    # shape의 세 값을 각각 변수에 담는다. 밝기 구간은 기본적으로 32 간격이다.
    n, h, w = gray.shape
    # 예: bins=8일 때 0→0번, 32→1번, 255→7번 구간.
    # minimum은 최댓값도 마지막 구간 안에 들어가도록 제한한다.
    labels = np.minimum((gray / 256 * bins).astype(int), bins - 1)
    # [이유] 전체 이미지를 한꺼번에 세면서 이미지끼리 구간 번호가 섞이지 않게 한다.
    # bins=2, 이미지 두 장이면 첫 장 구간은 0·1, 둘째는 2·3으로 분리한다.
    # [:,None,None]은 (N,)을 (N,1,1)로 바꿔 각 이미지의 모든 픽셀에 더하게 한다.
    offsets = np.arange(n)[:, None, None] * bins
    # ravel은 1차원으로 펼침, bincount는 번호별 개수 세기, reshape는 모양 복원이다.
    # [변화] 픽셀별 구간 번호 (N,H,W) → 이미지별 구간별 개수 (N,bins).
    counts = np.bincount((labels + offsets).ravel(), minlength=n * bins).reshape(n, bins)
    # 픽셀 개수로 나눠 크기와 상관없이 비교할 비율로 만든다. 행마다 합이 1이다.
    hist = counts / (h * w)
    # 가로 이웃쌍 H×(W-1), 세로 이웃쌍 (H-1)×W를 더한다.
    # 2×2는 총 4쌍이다. 이미지가 1×1이면 비교할 이웃쌍이 없어 0을 반환한다.
    edge_count = h * (w - 1) + (h - 1) * w
    # diff는 이웃의 값 차이, abs는 절댓값이다. 이미지 축을 남기고 차이를 합한다.
    edge_sum = (np.abs(np.diff(gray, axis=2)).sum(axis=(1, 2))
                + np.abs(np.diff(gray, axis=1)).sum(axis=(1, 2)))
    edges = edge_sum / edge_count if edge_count else np.zeros(n)
    # 엔트로피 H=-Σp log2(p): 한 구간에만 있으면 0, 여러 구간에 고르면 커진다.
    # maximum(..., tiny)은 log2(0)을 피한다. p=0인 항의 기여는 0으로 유지된다.
    # 밝기 분포의 흩어짐이지 사진 품질·상품 의미·모델 예측 불확실성이 아니다.
    entropy = -(hist * np.log2(np.maximum(hist, np.finfo(float).tiny))).sum(axis=1)
    frame = pd.DataFrame(hist, columns=[f'image_hist_{i}' for i in range(bins)])
    frame['image_edge_mean'] = edges
    frame['image_entropy'] = entropy
    return frame


def signup_cohorts(transactions, customers, observation_end=None):
    """가입 월별 고객의 경과 월 구매 활동률을 계산하고 미관측 월을 가린다.

    Args:
        transactions (pandas.DataFrame): customer_id, order_date, amount,
            quantity, unit_price 컬럼이 있는 거래 표.
        customers (pandas.DataFrame): 고유 customer_id와 signup_date 표.
            한 번도 구매하지 않은 가입 고객도 포함해야 한다.
        observation_end (str | None): 실제 수집 완료일. 생략하면 거래 날짜 최댓값.
            실제 자료의 마지막 구매일과 수집 완료일은 다를 수 있어 직접 지정한다.

    Returns:
        tuple: 가입 월별 인원 Series, 경과 월별 구매 고객 수 표,
            구매 활동률 표. 월말까지 관측하지 못한 칸은 NaN으로 남긴다.
            가입 월(0개월)도 완전 관측한 경우만 계산하며 반드시 100%는 아니다.

    Raises:
        ValueError: 가입 ID·날짜가 잘못되거나 구매와 가입·관측 시점이 모순인 경우.
    """
    # 코호트(cohort)는 같은 시기에 가입한 집단이다. 첫 구매 월로 나누지 않는다.
    required = {'customer_id', 'signup_date'}
    # 집합의 <=는 '필요한 이름들이 모두 포함되는가'다. set(표)는 컬럼명 집합이다.
    if not required <= set(customers):
        raise ValueError('customers requires customer_id and signup_date')
    if customers.empty or customers.customer_id.isna().any() or customers.customer_id.duplicated().any():
        raise ValueError('customers requires unique, nonmissing customer IDs')
    # 사본을 만들어 호출한 쪽의 가입 표에 날짜·코호트 컬럼을 덧쓰지 않는다.
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
    # RFM처럼 양수 구매만 센다. 취소·반품을 차감한 순매출 기준은 아니다.
    valid = (transactions.customer_id.notna() & dates.notna() & transactions.amount.gt(0)
             & transactions.quantity.gt(0) & transactions.unit_price.gt(0))
    purchases = transactions.loc[valid, ['customer_id']].copy()
    purchases['order_date'] = dates[valid]
    if (purchases.order_date > end).any():
        raise ValueError('observation_end must not precede observed purchases')
    # 구매 행 여러 개 → 고객의 가입일 하나. 가입일 없는 고객을 임의 추정하지 않는다.
    purchases = purchases.merge(customers, on='customer_id', how='left', validate='many_to_one')
    if purchases.signup_date.isna().any():
        raise ValueError('Every purchasing customer needs a signup date')
    if (purchases.order_date < purchases.signup_date).any():
        raise ValueError('Purchase date must not precede signup')
    # [변화] 2026-01-15 같은 날짜 → 2026-01이라는 달 단위 Period.
    # 월의 정수 번호 차이를 쓰면 12월→다음 해 1월도 1개월 차이로 계산된다.
    customers['cohort'] = customers.signup_date.dt.to_period('M')
    purchases['cohort'] = purchases.signup_date.dt.to_period('M')
    purchases['month'] = purchases.order_date.dt.to_period('M')
    purchases['age'] = purchases['month'].astype('int64') - purchases.cohort.astype('int64')
    # 분모는 구매자 표가 아니라 가입자 표에서 구한다. 미구매자도 분모에 남는다.
    sizes = customers.groupby('cohort').size().rename('signups')
    age_max = max(0, end.to_period('M').ordinal - sizes.index.min().ordinal)
    # 같은 고객이 같은 달에 10행을 구매해도 1명이다. 중복을 제거하고 인원을 센다.
    # unstack은 경과 월을 열로 펼친다. reindex는 없는 월·코호트 조합을 맞춘다.
    counts = (purchases.drop_duplicates(['customer_id', 'month']).groupby(['cohort', 'age'])
              .size().unstack(fill_value=0).reindex(index=sizes.index, columns=range(age_max + 1), fill_value=0))
    # 이중 리스트 내포로 각 칸의 달 말일 <= 수집 완료일인지 검사한다.
    # 10/9에 수집이 끝났다면 10월은 공백이다. 관측한 구매자가 있어도 완전 월이 아니다.
    complete = np.array([[(cohort + age).end_time.normalize() <= end for age in counts.columns]
                         for cohort in counts.index])
    # where는 조건이 참인 값만 유지하고 나머지는 NaN(미관측)으로 만든다.
    # 관측 완료한 달의 구매자 0명과 아직 끝나지 않은 달을 구분해야 한다.
    counts = counts.astype(float).where(complete)
    # axis=0으로 행의 가입 월에 맞춰 나눈다. 가입자 10명·구매자 3명 → 0.3(30%).
    # '한 번이라도 돌아왔는가' 누적 비율이 아니라 해당 월의 구매 활동률이다.
    rates = counts.div(sizes, axis=0)
    return sizes, counts, rates


def interactive_rfm(rfm):
    """고객별 RFM을 확대·그룹 선택이 가능한 산점도 객체로 만든다.

    Args:
        rfm (pandas.DataFrame): 고객 ID 인덱스와 RFM·점수·segment가 있는 표.

    Returns:
        plotly.graph_objects.Figure: x축은 주문 수, y축은 양수 구매 합계인 그림.
    """
    import plotly.graph_objects as go
    from .report import SEGMENT_COLORS

    fig = go.Figure()
    # 그룹마다 하나의 trace(그림 요소)를 만든다. 범례로 그룹을 켜고 끌 수 있다.
    for segment, group in rfm.groupby('segment', sort=True):
        # column_stack은 각 컬럼을 가로로 묶는다. 점을 가리킬 때 추가 정보를 보여준다.
        custom = np.column_stack([group.index.astype(str), group.recency,
                                  group.r_score, group.f_score, group.m_score])
        fig.add_trace(go.Scatter(x=group.frequency, y=group.monetary, mode='markers', name=segment,
                                marker={'color': SEGMENT_COLORS[segment], 'size': 9, 'opacity': 0.75},
                                customdata=custom,
                                # %{...}는 Plotly가 값을 채우는 문법이다. Python f문자열이 아니다.
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
    """보너스 피처·코호트 표·그림·오프라인 Plotly HTML을 저장한다.

    Args:
        analyzer (DataAnalyzer): 전처리와 필수 RFM 계산을 끝낸 객체.
        output_dir (str | pathlib.Path): 결과 상위 폴더. 그 안의 bonus에 저장한다.
        customers_path (str | pathlib.Path | None): 가입 고객 CSV.
            생략하면 거래 파일과 같은 폴더의 customers.csv를 사용한다.
        observation_end (str | None): 코호트 수집 완료일.

    Returns:
        dict: 피처 수·가입 인원·관측 칸 수·차트 고객 수 등 저장 결과의 요약.
            analyzer.df에는 기본 8구간 기준 피처 10개를 직접 추가한다.

    Raises:
        ValueError: 가입 자료가 없거나 이미지·코호트 입력이 유효하지 않은 경우.
        OSError: 파일을 읽거나 저장할 수 없는 경우.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    out = Path(output_dir) / 'bonus'
    out.mkdir(parents=True, exist_ok=True)
    features = image_features(analyzer.images)
    products = analyzer.products[['product_id', 'image_index']].copy()
    # 피처 표의 행 번호는 이미지 위치다. 상품 표의 image_index로 찾아 붙인다.
    products = products.join(features, on='image_index')
    products.to_csv(out / 'image_features.csv', index=False)
    # 이 반복문은 피처 컬럼을 순회한다. 이미지·픽셀별 계산은 NumPy가 한꺼번에 했다.
    # 배열 조회로 상품 단위 피처를 거래 단위에 펼쳐 기본 22→32컬럼이 된다.
    for column in features:
        analyzer.df[column] = features[column].to_numpy()[analyzer.df.image_index.to_numpy(dtype=int)]
    analyzer.df.to_csv(out / 'transactions_with_image_features.csv', index=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(np.arange(8), features.filter(like='image_hist_').mean())
    axes[0].set(title='Mean normalized luminance histogram', xlabel='Bin (0..255, width 32)', ylabel='Pixel fraction')
    axes[1].scatter(analyzer.images.std(axis=tuple(range(1, analyzer.images.ndim))), features.image_edge_mean)
    axes[1].set(title='Pixel variation versus local edges', xlabel='Pixel standard deviation', ylabel='Mean neighbour difference')
    # 세미콜론은 한 줄에 여러 문장을 쓰는 구분자다. 조정 → 저장 → 해제 순서다.
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
    # 첫 any는 열별로, 두 번째 any는 그 결과 전체에 대해 관측값 존재를 묻는다.
    if rates.notna().any().any():
        sns.heatmap(rates, mask=rates.isna(), vmin=0, vmax=1, cmap='YlGnBu', annot=True, fmt='.0%', ax=ax)
    else:
        ax.text(.5, .5, 'No complete calendar months observed', ha='center', transform=ax.transAxes)
    ax.set(title='Signup-cohort purchase activity (blank = not fully observed)',
           xlabel='Months since signup', ylabel='Signup month')
    fig.tight_layout(); fig.savefig(out / 'cohort_retention.png', dpi=140); plt.close(fig)

    rfm = analyzer.rfm
    chart = interactive_rfm(rfm)
    # full_html=False는 그림 조각만, include_plotlyjs=True는 실행 라이브러리도
    # 포함하라는 뜻이다. 파일은 커지지만 인터넷 없이 차트를 조작할 수 있다.
    fragment = chart.to_html(full_html=False, include_plotlyjs=True, div_id='rfm-plot',
                             config={'responsive': True, 'displaylogo': False})
    page = ('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>A1-1 RFM 탐색</title><body style="margin:0 auto;max-width:1100px;padding:20px;font-family:system-ui">'
            '<h1>고객 RFM 탐색</h1><p>고정 난수로 생성한 합성 고객 240명의 예시입니다. 실제 고객 정보가 아닙니다. '
            '점에 마우스를 올리면 고객별 R/F/M을 확인할 수 있습니다. 범례를 누르면 그룹을 숨기거나 표시하고, '
            '드래그하면 확대할 수 있습니다. 도구 모음에서 그림을 저장할 수 있습니다.</p>' + fragment + '</body></html>')
    (out / 'rfm_interactive.html').write_text(page, encoding='utf-8')
    # 수치 검증용 요약. 히스토그램의 행 합이 1에 얼마나 가까운지도 기록한다.
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
