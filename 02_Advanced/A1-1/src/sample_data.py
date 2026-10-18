"""실제 고객 자료 대신 구조를 점검하기 위한 합성 학습 데이터를 만든다.

특정 고객 행동을 의도적으로 구성한다. 생성 패턴을 발견했다고 해서
실제 시장에 같은 패턴이나 마케팅 효과가 있다는 증거가 되지는 않는다.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd


def generate_sample_data(output_dir, seed=42):
    """고정 난수로 거래·상품·이미지·가입일 파일을 생성해 저장한다.

    Args:
        output_dir (str | pathlib.Path): 파일을 저장할 폴더.
            같은 이름의 기존 파일은 교체된다.
        seed (int): 난수 생성의 출발값. 같은 환경과 seed에서 같은 표본을 재현한다.

    Returns:
        dict: 생성 규모·seed·이미지 모양·출처를 담은 메타데이터.

    Raises:
        OSError: 출력 폴더나 파일을 만들 수 없는 경우.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # 난수는 무작위처럼 보이는 수열이다. 고정 seed로 설명·검증의 입력을 맞춘다.
    rng = np.random.default_rng(seed)
    n_products, n_customers = 80, 240
    # repeat는 각 값을 반복한다. 카테고리 4종 × 20상품 = 80상품.
    category = np.repeat(["Home", "Fashion", "Beauty", "Electronics"], 20)
    # lognormal은 양수이고 큰 값 쪽 꼬리가 긴 분포를 만든다. 실제 가격 추정은 아니다.
    # 100으로 나눈 뒤 반올림하고 다시 곱해 100원 단위로 맞춘다.
    prices = np.round(rng.lognormal(9.7, 0.6, n_products) / 100) * 100
    # [60:]는 위치 60부터 끝까지, *=3은 선택한 값에 3을 곱해 다시 저장한다.
    prices[60:] *= 3
    products = pd.DataFrame({
        # 리스트 내포: 반복 결과를 목록으로 모은다. :03d는 0을 채운 세 자리 정수.
        "product_id": [f"P{i:03d}" for i in range(n_products)],
        "product_name": [f"{cat} sample item {i:03d}" for i, cat in enumerate(category)],
        "category": category, "catalog_price": prices,
        "rating": np.round(rng.uniform(2.5, 5, n_products), 1),
        "image_index": np.arange(n_products),
    })
    # [이미지 생성] 브로드캐스팅은 크기 1인 축 등을 맞춰 배열을 함께 계산한다.
    # levels (80,1,1,3) + texture (80,16,16,3) + gradient (1,1,16,1)
    # → (80,16,16,3). 작은 이미지를 상품마다 숫자로 생성하며 실제 사진은 아니다.
    levels = rng.uniform(35, 200, (n_products, 1, 1, 3))
    texture = rng.normal(0, 25, (n_products, 16, 16, 3))
    # linspace는 일정 간격의 16개 값, None은 축 추가, :는 그 축 전체 선택이다.
    gradient = np.linspace(-20, 20, 16)[None, None, :, None]
    # clip으로 0~255를 보장한 다음 uint8(0~255 정수)로 바꿔 저장한다.
    images = np.clip(levels + texture + gradient, 0, 255).astype(np.uint8)

    # 고객 240명을 네 행동 패턴으로 구성한다. 이 profiles는 정답 라벨로
    # 분석기에 전달되지 않는다. RFM은 거래를 읽고 고정 규칙으로 그룹을 만든다.
    profiles = np.repeat(np.arange(4), n_customers // 4)
    # choose는 각 고객의 패턴 번호(0~3)에 해당하는 후보 값을 선택한다.
    # integers(10,17)은 10 이상 17 미만이다. 패턴마다 구매 횟수·최근성을 다르게 한다.
    order_counts = np.choose(profiles, [rng.integers(10, 17, n_customers),
                                       rng.integers(4, 9, n_customers),
                                       np.ones(n_customers, dtype=int),
                                       rng.integers(2, 6, n_customers)])
    last_age = np.choose(profiles, [rng.integers(0, 15, n_customers),
                                   rng.integers(10, 45, n_customers),
                                   rng.integers(0, 8, n_customers),
                                   rng.integers(100, 250, n_customers)])
    # [변화] 고객별 주문 수 → 주문별 소유 고객 번호.
    # 예: 고객 [0,1], 주문 수 [2,1] → owners [0,0,1].
    owners = np.repeat(np.arange(n_customers), order_counts)
    # cumsum은 누적합이다. 각 고객 주문의 시작 위치를 전체 주문에 펼친다.
    starts = np.repeat(np.cumsum(order_counts) - order_counts, order_counts)
    # 전체 위치에서 고객별 시작 위치를 빼면 고객 안에서의 주문 순번이 된다.
    positions = np.arange(len(owners)) - starts
    age = last_age[owners] + (order_counts[owners] - 1 - positions) * rng.integers(3, 15, len(owners))
    order_dates = pd.Timestamp("2026-10-09") - pd.to_timedelta(age, unit="D")
    # [변화] 주문 → 주문 안의 상품 행. 주문마다 1~3행을 만든다.
    # order_index가 반복되므로 같은 order_id가 여러 줄에 나타나는 것이 정상이다.
    line_counts = rng.integers(1, 4, len(owners))
    order_index = np.repeat(np.arange(len(owners)), line_counts)
    customer_index = owners[order_index]
    product_index = rng.integers(0, n_products, len(order_index))
    # 생성용 vip 마스크다. 분석 결과의 VIP 판정 자체가 아니다.
    vip = profiles[customer_index] == 0
    product_index[vip] = rng.integers(60, 80, vip.sum())
    quantity = rng.integers(1, 5, len(order_index))
    unit_price = prices[product_index]
    shipping = rng.integers(1, 9, len(order_index)).astype(float)
    # replace=False는 같은 위치를 중복 추출하지 않는다는 뜻이다.
    # 긴 배송을 넣은 뒤 결측을 넣으므로 일부 조건은 같은 행에 겹칠 수 있다.
    shipping[rng.choice(len(shipping), 15, replace=False)] = 60
    shipping[rng.random(len(shipping)) < 0.1] = np.nan
    transactions = pd.DataFrame({
        "line_id": [f"L{i:05d}" for i in range(len(order_index))],
        "order_id": [f"O{i:05d}" for i in order_index],
        "customer_id": [f"C{i:03d}" for i in customer_index],
        "order_date": order_dates[order_index].strftime("%Y-%m-%d"),
        "product_id": products.product_id.to_numpy()[product_index],
        "unit_price": unit_price, "quantity": quantity,
        # 각 상품 행의 금액이다. 주문 합계를 모든 상품 행에 반복하지 않는다.
        "amount": unit_price * quantity,
        "country": rng.choice(["KR", "JP", "US"], len(order_index)),
        "payment_method": rng.choice(["Card", "Transfer", "Wallet"], len(order_index)),
        "shipping_days": shipping,
    })
    # 각 상품에 독립적으로 결측을 주입한다. 0.1은 확률이라 정확히 10%는 아닐 수 있다.
    # np.nan은 숫자 데이터에서 결측을 나타낼 때 쓰는 값이다.
    for column, fraction in [("catalog_price", 0.1), ("rating", 0.1), ("product_name", 0.05)]:
        products.loc[rng.random(n_products) < fraction, column] = np.nan
    # index=False는 Pandas의 행 번호를 별도 CSV 컬럼으로 저장하지 않는 옵션이다.
    transactions.to_csv(output_dir / "transactions.csv", index=False)
    products.to_csv(output_dir / "products.csv", index=False)
    np.save(output_dir / "images.npy", images, allow_pickle=False)
    # 가입일은 별도 난수 생성기로 만들어 위의 거래·상품·이미지 난수 수열을 유지한다.
    # 여기서 첫 구매 이전 0~90일로 합성한 가입일을 명시적으로 저장한다.
    # 실제 분석기에서 '첫 구매일=가입일'로 추정하는 정책과는 구분해야 한다.
    first = transactions.groupby('customer_id').order_date.min()
    signup_rng = np.random.default_rng(seed + 101)
    customers = pd.DataFrame({'customer_id': first.index,
                              'signup_date': (pd.to_datetime(first.to_numpy())
                                              - pd.to_timedelta(signup_rng.integers(0, 91, len(first)), unit='D'))})
    customers.to_csv(output_dir / 'customers.csv', index=False, date_format='%Y-%m-%d')
    # 메타데이터는 데이터에 대한 설명이다. 출처·단위·생성 조건을 함께 남긴다.
    metadata = {
        "source": "Locally generated synthetic teaching data; not real commerce records",
        "seed": seed, "transactions": len(transactions), "orders": len(owners),
        "customers": n_customers, "products": n_products,
        "image_shape": list(images.shape), "currency": "KRW (synthetic)",
        "signup_source": "Synthetic first purchase minus 0..90 days, independent RNG seed+101",
        "injected_conditions": ["missing catalog price, rating, name and shipping days",
                                "long shipping times", "legitimate high-price products"],
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata
