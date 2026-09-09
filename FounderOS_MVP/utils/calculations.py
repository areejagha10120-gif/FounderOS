from typing import Dict, Optional
import numpy as np
import pandas as pd
from .helpers import find_column

def revenue(df: Optional[pd.DataFrame]):
    if df is None: return None
    c = find_column(df, "amount")
    return float(pd.to_numeric(df[c], errors="coerce").sum()) if c else None

def expense_total(df: Optional[pd.DataFrame]):
    if df is None: return None
    c = find_column(df, "amount") or find_column(df, "cost")
    return float(pd.to_numeric(df[c], errors="coerce").sum()) if c else None

def profit(rev, exp):
    return rev - exp if rev is not None and exp is not None else None

def profit_margin(rev, prof):
    return (prof / rev * 100) if rev and prof is not None else None

def trend_pct(df: Optional[pd.DataFrame], amount_col="amount", date_col="date"):
    if df is None or amount_col not in df.columns or date_col not in df.columns:
        return None
    x = df.copy()
    x[date_col] = pd.to_datetime(x[date_col], errors="coerce")
    x[amount_col] = pd.to_numeric(x[amount_col], errors="coerce")
    x = x.dropna(subset=[date_col, amount_col])
    if x.empty: return None
    x["period"] = x[date_col].dt.to_period("M")
    s = x.groupby("period")[amount_col].sum().sort_index()
    if len(s) < 2 or s.iloc[-2] == 0: return None
    return float((s.iloc[-1] - s.iloc[-2]) / abs(s.iloc[-2]) * 100)

def inventory_metrics(df):
    if df is None:
        return {}
    q = find_column(df, "quantity")
    product = find_column(df, "product")
    cost = find_column(df, "cost")
    amount = find_column(df, "amount")
    result = {}
    if q:
        qty = pd.to_numeric(df[q], errors="coerce").fillna(0)
        result["total_units"] = float(qty.sum())
        result["low_stock_items"] = int((qty <= 5).sum())
        if product:
            grouped = df.assign(_q=qty).groupby(product)["_q"].sum().sort_values()
            result["slow_products"] = grouped.head(5).to_dict()
            result["fast_products"] = grouped.tail(5).sort_values(ascending=False).to_dict()
    if cost and q:
        result["inventory_cost_value"] = float(
            (pd.to_numeric(df[cost], errors="coerce").fillna(0) * qty).sum()
        )
    elif amount and q:
        result["inventory_cost_value"] = None
    return result

def customer_metrics(df):
    if df is None:
        return {}
    c = find_column(df, "customer")
    amount = find_column(df, "amount")
    if not c or not amount:
        return {}
    x = df.copy()
    x[amount] = pd.to_numeric(x[amount], errors="coerce").fillna(0)
    grouped = x.groupby(c)[amount].agg(["sum", "count"]).sort_values("sum", ascending=False)
    return {
        "customer_count": int(grouped.shape[0]),
        "top_customers": grouped.head(5).to_dict("index"),
        "repeat_customers": int((grouped["count"] > 1).sum()),
    }

def calculate_health(metrics: Dict) -> Optional[int]:
    components = []
    if metrics.get("revenue_trend") is not None:
        components.append(max(0, min(100, 50 + metrics["revenue_trend"])))
    if metrics.get("profit_margin") is not None:
        components.append(max(0, min(100, metrics["profit_margin"] * 5)))
    if metrics.get("inventory_low_stock") is not None:
        components.append(max(0, 100 - metrics["inventory_low_stock"] * 5))
    if not components:
        return None
    return int(round(sum(components) / len(components)))
