"""Generate teaching data, not observations of real customers or products."""
import json
from pathlib import Path

import numpy as np
import pandas as pd


def generate_sample_data(output_dir, seed=42):
    """Write linked transactions, products and RGB arrays using a fixed seed."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    n_products, n_customers = 80, 240
    category = np.repeat(["Home", "Fashion", "Beauty", "Electronics"], 20)
    prices = np.round(rng.lognormal(9.7, 0.6, n_products) / 100) * 100
    prices[60:] *= 3
    products = pd.DataFrame({
        "product_id": [f"P{i:03d}" for i in range(n_products)],
        "product_name": [f"{cat} sample item {i:03d}" for i, cat in enumerate(category)],
        "category": category, "catalog_price": prices,
        "rating": np.round(rng.uniform(2.5, 5, n_products), 1),
        "image_index": np.arange(n_products),
    })
    # Broadcasting constructs the whole (product, height, width, channel) batch.
    levels = rng.uniform(35, 200, (n_products, 1, 1, 3))
    texture = rng.normal(0, 25, (n_products, 16, 16, 3))
    gradient = np.linspace(-20, 20, 16)[None, None, :, None]
    images = np.clip(levels + texture + gradient, 0, 255).astype(np.uint8)

    # Four behaviour patterns make segmentation inspectable; they are not labels
    # supplied to the analyzer and do not validate a real marketing hypothesis.
    profiles = np.repeat(np.arange(4), n_customers // 4)
    order_counts = np.choose(profiles, [rng.integers(10, 17, n_customers),
                                       rng.integers(4, 9, n_customers),
                                       np.ones(n_customers, dtype=int),
                                       rng.integers(2, 6, n_customers)])
    last_age = np.choose(profiles, [rng.integers(0, 15, n_customers),
                                   rng.integers(10, 45, n_customers),
                                   rng.integers(0, 8, n_customers),
                                   rng.integers(100, 250, n_customers)])
    owners = np.repeat(np.arange(n_customers), order_counts)
    starts = np.repeat(np.cumsum(order_counts) - order_counts, order_counts)
    positions = np.arange(len(owners)) - starts
    age = last_age[owners] + (order_counts[owners] - 1 - positions) * rng.integers(3, 15, len(owners))
    order_dates = pd.Timestamp("2026-10-09") - pd.to_timedelta(age, unit="D")
    line_counts = rng.integers(1, 4, len(owners))
    order_index = np.repeat(np.arange(len(owners)), line_counts)
    customer_index = owners[order_index]
    product_index = rng.integers(0, n_products, len(order_index))
    vip = profiles[customer_index] == 0
    product_index[vip] = rng.integers(60, 80, vip.sum())
    quantity = rng.integers(1, 5, len(order_index))
    unit_price = prices[product_index]
    shipping = rng.integers(1, 9, len(order_index)).astype(float)
    shipping[rng.choice(len(shipping), 15, replace=False)] = 60
    shipping[rng.random(len(shipping)) < 0.1] = np.nan
    transactions = pd.DataFrame({
        "line_id": [f"L{i:05d}" for i in range(len(order_index))],
        "order_id": [f"O{i:05d}" for i in order_index],
        "customer_id": [f"C{i:03d}" for i in customer_index],
        "order_date": order_dates[order_index].strftime("%Y-%m-%d"),
        "product_id": products.product_id.to_numpy()[product_index],
        "unit_price": unit_price, "quantity": quantity,
        "amount": unit_price * quantity,
        "country": rng.choice(["KR", "JP", "US"], len(order_index)),
        "payment_method": rng.choice(["Card", "Transfer", "Wallet"], len(order_index)),
        "shipping_days": shipping,
    })
    for column, fraction in [("catalog_price", 0.1), ("rating", 0.1), ("product_name", 0.05)]:
        products.loc[rng.random(n_products) < fraction, column] = np.nan
    transactions.to_csv(output_dir / "transactions.csv", index=False)
    products.to_csv(output_dir / "products.csv", index=False)
    np.save(output_dir / "images.npy", images, allow_pickle=False)
    # A separate RNG preserves the original transaction/product/image samples.
    # These are explicit synthetic signup dates, not dates inferred as signups
    # from the first purchase by the cohort analyzer.
    first = transactions.groupby('customer_id').order_date.min()
    signup_rng = np.random.default_rng(seed + 101)
    customers = pd.DataFrame({'customer_id': first.index,
                              'signup_date': (pd.to_datetime(first.to_numpy())
                                              - pd.to_timedelta(signup_rng.integers(0, 91, len(first)), unit='D'))})
    customers.to_csv(output_dir / 'customers.csv', index=False, date_format='%Y-%m-%d')
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
