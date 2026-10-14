"""Explicit, inspectable preprocessing and RFM analysis using NumPy/Pandas."""
from pathlib import Path

import numpy as np
import pandas as pd


def iqr_bounds(values, threshold=1.5):
    """Return Tukey fences. Flagging is not a decision to delete a record."""
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be finite and positive")
    values = pd.to_numeric(values, errors="raise")
    if not np.isfinite(values.dropna()).all() or values.dropna().empty:
        raise ValueError("IQR requires at least one finite observation")
    q1, q3 = values.quantile([0.25, 0.75])
    spread = q3 - q1
    return float(q1 - threshold * spread), float(q3 + threshold * spread)


class DataAnalyzer:
    """Load linked tables, engineer features and segment valid purchases.

    Transactions use one row per order line; images use one array per product.
    Monetary values always come from recorded transactions, never catalog-price
    imputation or the visualization-only outlier treatment.
    """

    def __init__(self, data_path, products_path=None, images_path=None):
        self.data_path = Path(data_path)
        base = self.data_path.parent
        self.products_path = Path(products_path) if products_path else base / "products.csv"
        self.images_path = Path(images_path) if images_path else base / "images.npy"
        self.df = None
        self.raw_df = None
        self.products = None
        self.images = None
        self.rfm = None
        self.audit = {}

    @staticmethod
    def _require_columns(frame, columns, label):
        missing = sorted(set(columns) - set(frame.columns))
        if missing:
            raise ValueError(f"{label} missing columns: {missing}")

    def _require_loaded(self):
        if self.df is None:
            raise RuntimeError("Call load_data() first")

    def load_data(self):
        """Validate table relationships before joining; reject ambiguous orders."""
        transactions = pd.read_csv(self.data_path, dtype={
            "line_id": "string", "order_id": "string", "customer_id": "string", "product_id": "string"})
        products = pd.read_csv(self.products_path, dtype={"product_id": "string"})
        self._require_columns(transactions, ["line_id", "order_id", "customer_id", "order_date",
                                            "product_id", "unit_price", "quantity", "amount"], "transactions")
        self._require_columns(products, ["product_id", "product_name", "category", "catalog_price",
                                        "rating", "image_index"], "products")
        if transactions.empty or products.empty:
            raise ValueError("Input tables must not be empty")
        for frame, key in [(transactions, "line_id"), (products, "product_id")]:
            if frame[key].isna().any() or frame[key].duplicated().any():
                raise ValueError(f"{key} must be unique and nonmissing")
        transactions["order_date"] = pd.to_datetime(transactions["order_date"], errors="coerce").dt.normalize()
        for col in ["unit_price", "quantity", "amount"]:
            transactions[col] = pd.to_numeric(transactions[col], errors="raise")
            if not np.isfinite(transactions[col].dropna()).all():
                raise ValueError(f"{col} contains infinite values")
        comparable = transactions[["unit_price", "quantity", "amount"]].notna().all(axis=1)
        if not np.isclose(transactions.loc[comparable, "amount"],
                          transactions.loc[comparable, "unit_price"] * transactions.loc[comparable, "quantity"],
                          rtol=1e-6, atol=0.01).all():
            raise ValueError("amount must be the line total unit_price * quantity")
        order_groups = transactions.groupby("order_id")
        for key in ["customer_id", "order_date"]:
            if (order_groups[key].nunique(dropna=False) > 1).any():
                raise ValueError(f"One order_id must have one {key}")
        overlap = (set(transactions.columns) & set(products.columns)) - {"product_id"}
        if overlap:
            raise ValueError(f"Overlapping table columns: {sorted(overlap)}")
        joined = transactions.merge(products, on="product_id", how="left", validate="many_to_one", indicator=True)
        if (joined["_merge"] != "both").any():
            raise ValueError("Every transaction must reference a known product_id")
        self.images = np.load(self.images_path, allow_pickle=False)
        if self.images.ndim not in (3, 4) or any(n == 0 for n in self.images.shape):
            raise ValueError("images must have shape (N,H,W) or (N,H,W,C), with nonempty axes")
        if not np.issubdtype(self.images.dtype, np.number) or not np.isfinite(self.images).all():
            raise ValueError("images must contain finite numeric pixels")
        indices = pd.to_numeric(products.image_index, errors="raise")
        if indices.isna().any() or ((indices % 1) != 0).any() or ((indices < 0) | (indices >= len(self.images))).any():
            raise ValueError("image_index must refer to an existing image")
        for col in ["catalog_price", "rating"]:
            products[col] = pd.to_numeric(products[col], errors="raise")
            if not np.isfinite(products[col].dropna()).all():
                raise ValueError(f"{col} contains infinite values")
        if products.category.isna().any():
            raise ValueError("Product category must be supplied for grouped imputation")
        self.products = products
        # Merge again after numeric normalization of the product table.
        self.df = transactions.merge(products, on="product_id", how="left", validate="many_to_one")
        if "shipping_days" in self.df:
            self.df["shipping_days"] = pd.to_numeric(self.df.shipping_days, errors="raise")
            if not np.isfinite(self.df.shipping_days.dropna()).all():
                raise ValueError("shipping_days contains infinite values")
        self.raw_df = self.df.copy(deep=True)
        self.rfm = None
        self.audit = {"input_rows": len(self.df), "products": len(products),
                      "missing_before": self.df.isna().sum().to_dict()}
        return self.df

    @staticmethod
    def _fill_by_group(frame, columns, group_col, strategy):
        """Group statistic with global fallback; all-missing variables fail explicitly."""
        changes = {}
        for column in columns:
            numeric = pd.to_numeric(frame[column], errors="raise")
            if not np.isfinite(numeric.dropna()).all():
                raise ValueError(f"{column} contains infinite values")
            global_value = getattr(numeric, strategy)()
            if pd.isna(global_value):
                raise ValueError(f"Cannot impute all-missing column {column}")
            group_values = frame.groupby(group_col, dropna=False)[column].transform(strategy)
            frame[column] = numeric.fillna(group_values).fillna(global_value)
            changes[column] = int(numeric.isna().sum())
        return changes

    def handle_missing_values(self, strategy="median", group_col="category",
                              product_columns=("catalog_price", "rating"),
                              transaction_columns=("shipping_days",)):
        """Impute catalog at product grain, shipping at line grain; keep purchase facts."""
        self._require_loaded()
        if strategy not in ("median", "mean"):
            raise ValueError("strategy must be median or mean")
        protected = {"amount", "quantity", "unit_price", "customer_id", "order_id", "order_date"}
        if protected.intersection(transaction_columns):
            raise ValueError("Do not impute purchase facts used for RFM")
        self._require_columns(self.df, [group_col, *transaction_columns], "transactions")
        self._require_columns(self.products, [group_col, *product_columns], "products")
        product_counts = self._fill_by_group(self.products, product_columns, group_col, strategy)
        self.products["product_name"] = self.products.product_name.fillna("Unknown product")
        # A catalog statistic must not be weighted by how often each product sold.
        for column in [*product_columns, "product_name"]:
            self.df[column] = self.df.product_id.map(self.products.set_index("product_id")[column])
        line_counts = self._fill_by_group(self.df, transaction_columns, group_col, strategy)
        self.audit["imputation"] = {"strategy": strategy, "group": group_col,
                                    "product_values": product_counts, "line_values": line_counts}
        self.audit["missing_after"] = self.df.isna().sum().to_dict()
        return self.df

    def handle_missing(self, strategy="median", group_col="category",
                       product_columns=("catalog_price", "rating"),
                       transaction_columns=("shipping_days",)):
        """Compatibility name for handle_missing_values(), with identical behavior."""
        return self.handle_missing_values(
            strategy=strategy, group_col=group_col,
            product_columns=product_columns, transaction_columns=transaction_columns)

    def engineer_features(self):
        """Reduce all image axes except the product axis, without a pixel/image loop."""
        self._require_loaded()
        axes = tuple(range(1, self.images.ndim))
        image_mean = self.images.mean(axis=axes, dtype=np.float64)
        image_std = self.images.std(axis=axes, dtype=np.float64)
        indices = self.df.image_index.to_numpy(dtype=int)
        self.df["image_mean"] = image_mean[indices]
        self.df["image_std"] = image_std[indices]
        self.df["name_length"] = self.df.product_name.astype("string").str.len()
        self.df["name_word_count"] = self.df.product_name.astype("string").str.split().str.len()
        return self.df

    def detect_outliers(self, column, threshold=1.5):
        """Add a flag and return outlier rows; retain the unaltered measurements."""
        self._require_loaded()
        lower, upper = iqr_bounds(self.df[column], threshold)
        values = self.df[column]
        flag = values.lt(lower) | values.gt(upper)
        self.df[f"{column}_is_outlier"] = flag
        self.audit.setdefault("outliers", {})[column] = {
            "threshold": threshold, "lower": lower, "upper": upper, "count": int(flag.sum())}
        return self.df.loc[flag].copy()

    def treat_outliers(self, column, threshold=1.5, method="clip"):
        """Return a comparison series; do not mutate source columns or RFM inputs."""
        self._require_loaded()
        if method not in ("clip", "remove"):
            raise ValueError("method must be clip or remove")
        lower, upper = iqr_bounds(self.df[column], threshold)
        values = self.df[column]
        if method == "clip":
            return values.clip(lower, upper).rename(f"{column}_treated")
        return values.loc[values.between(lower, upper)].rename(f"{column}_treated")

    def calculate_rfm(self, customer_col="customer_id", date_col="order_date",
                      amount_col="amount", order_col="order_id", reference_date=None,
                      recent_days=30, inactive_days=90, loyal_orders=4):
        """Compute purchases only, stable tied scores and mutually exclusive segments.

        Default reference is the latest purchase date plus one day. Rank(method=
        'average') gives equal values equal scores, including constant columns.
        Fixed behavioural rules, not scores, define actionable segments.
        """
        self._require_loaded()
        if recent_days < 0 or inactive_days <= recent_days or loyal_orders < 2:
            raise ValueError("Require 0 <= recent_days < inactive_days and loyal_orders >= 2")
        self._require_columns(self.df, [customer_col, date_col, amount_col, order_col, "quantity"], "RFM")
        if self.df[amount_col].isna().any() and amount_col != "amount":
            raise ValueError("Custom amount column has missing values")
        valid = (self.df[customer_col].notna() & self.df[order_col].notna() & self.df[date_col].notna()
                 & self.df[amount_col].gt(0) & self.df.quantity.gt(0) & self.df.unit_price.gt(0))
        purchases = self.df.loc[valid].copy()
        if purchases.empty:
            raise ValueError("No valid positive purchases available for RFM")
        dates = pd.to_datetime(purchases[date_col], errors="raise").dt.normalize()
        reference = pd.Timestamp(reference_date).normalize() if reference_date is not None else dates.max() + pd.Timedelta(days=1)
        if pd.isna(reference) or reference < dates.max():
            raise ValueError("reference_date must not precede the latest purchase")
        purchases[date_col] = dates
        for key in [customer_col, date_col]:
            if (purchases.groupby(order_col)[key].nunique() > 1).any():
                raise ValueError(f"One order must have one {key}")
        grouped = purchases.groupby(customer_col)
        result = grouped.agg(last_purchase=(date_col, "max"), frequency=(order_col, "nunique"),
                             monetary=(amount_col, "sum"))
        result["recency"] = (reference - result.last_purchase).dt.days
        for variable, ascending, score in [("recency", False, "r_score"),
                                            ("frequency", True, "f_score"),
                                            ("monetary", True, "m_score")]:
            percentile = result[variable].rank(method="average", pct=True, ascending=ascending)
            result[score] = np.ceil(percentile * 5).clip(1, 5).astype(int)
        result["rfm_score"] = result[["r_score", "f_score", "m_score"]].sum(axis=1)
        vip_cutoff = float(result.monetary.quantile(0.75))
        inactive = result.recency > inactive_days
        new = (result.recency <= recent_days) & result.frequency.eq(1)
        vip = (result.recency <= recent_days) & (result.frequency >= loyal_orders) & (result.monetary >= vip_cutoff)
        loyal = result.frequency >= loyal_orders
        result["segment"] = np.select([inactive, new, vip, loyal],
                                       ["Inactive", "New", "VIP", "Loyal"], default="Regular")
        self.audit["rfm"] = {"reference_date": reference.strftime("%Y-%m-%d"),
                             "eligible_rows": len(purchases), "excluded_rows": int((~valid).sum()),
                             "customers": len(result), "orders": purchases[order_col].nunique(),
                             "recent_days": recent_days, "inactive_days": inactive_days,
                             "loyal_orders": loyal_orders, "vip_monetary_cutoff": vip_cutoff,
                             "excluded_reason_counts_overlapping": {
                                 "missing_customer": int(self.df[customer_col].isna().sum()),
                                 "missing_order": int(self.df[order_col].isna().sum()),
                                 "invalid_date": int(self.df[date_col].isna().sum()),
                                 "nonpositive_or_missing_amount": int((~self.df[amount_col].gt(0)).sum()),
                                 "nonpositive_or_missing_quantity": int((~self.df.quantity.gt(0)).sum()),
                                 "nonpositive_or_missing_price": int((~self.df.unit_price.gt(0)).sum())}}
        self.rfm = result[["recency", "frequency", "monetary", "r_score", "f_score", "m_score", "rfm_score", "segment"]]
        return self.rfm

    def summarize(self, columns=("unit_price", "amount", "shipping_days", "image_mean", "image_std")):
        self._require_loaded()
        return self.df[list(columns)].describe(percentiles=[0.25, 0.5, 0.75]).T

    def segment_summary(self):
        if self.rfm is None:
            raise RuntimeError("Call calculate_rfm() first")
        summary = self.rfm.groupby("segment").agg(
            customers=("monetary", "size"), mean_recency=("recency", "mean"),
            mean_frequency=("frequency", "mean"), mean_monetary=("monetary", "mean"),
            revenue=("monetary", "sum"))
        summary["customer_share_pct"] = summary.customers / summary.customers.sum() * 100
        summary["revenue_share_pct"] = summary.revenue / summary.revenue.sum() * 100
        return summary
