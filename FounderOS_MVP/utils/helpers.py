import io
import re
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

TYPE_KEYWORDS = {
    "sales": ["sale", "sales", "revenue", "invoice", "order", "transaction"],
    "expenses": ["expense", "expenses", "cost", "spending", "payment", "purchase"],
    "inventory": ["inventory", "stock", "sku", "reorder", "quantity", "warehouse"],
    "customers": ["customer", "client", "buyer", "phone", "email", "customer_id"],
}

ALIASES = {
    "amount": ["amount", "sale_amount", "revenue", "total", "price", "sales", "value"],
    "date": ["date", "sale_date", "transaction_date", "order_date", "invoice_date"],
    "product": ["product", "product_name", "item", "item_name", "sku", "product_id"],
    "quantity": ["quantity", "qty", "units", "stock", "units_sold"],
    "customer": ["customer", "customer_name", "client", "buyer", "customer_id"],
    "category": ["category", "expense_category", "type", "department"],
    "cost": ["cost", "purchase_cost", "unit_cost", "cost_price"],
}

def init_state():
    defaults = {
        "user": None,
        "session": None,
        "datasets": {},
        "analysis": None,
        "analysis_ready": False,
        "business_goal": None,
        "data_notices": [],
        "advisor_messages": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def inject_css():
    st.markdown("""
    <style>
    :root {
        --navy: #102a43;
        --blue: #1f4e79;
        --accent: #0ea5a8;
        --bg: #f8fafc;
        --muted: #64748b;
        --border: #e2e8f0;
    }
    .stApp { background: #f8fafc; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #102a43 0%, #173f5f 100%);
    }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    .block-container { max-width: 1400px; padding-top: 2.2rem; }
    h1, h2, h3 { color: #102a43; letter-spacing: -0.02em; }
    .feature-card, .metric-card, .insight-card, .priority-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 18px; margin-bottom: 12px; box-shadow: 0 4px 14px rgba(15,23,42,.05);
    }
    .feature-card { display:flex; gap:14px; align-items:flex-start; }
    .step-number { font-weight:800; color:#0ea5a8; font-size:18px; }
    .muted { color:#64748b; }
    .privacy-note { background:#eef6f7; border:1px solid #cde7e8; border-radius:12px; padding:16px; margin-top:20px; }
    .auth-shell { max-width:620px; margin: 8vh auto 25px; text-align:center; }
    .brand-mark { width:52px; height:52px; line-height:52px; margin:auto; border-radius:14px;
        background:#0ea5a8; color:white; font-weight:900; font-size:26px; }
    .kpi { font-size:30px; font-weight:800; color:#102a43; }
    .small-label { color:#64748b; font-size:13px; }
    div[data-testid="stFileUploader"] {
        background:white; border:1px dashed #94a3b8; border-radius:12px; padding:8px;
    }
    </style>
    """, unsafe_allow_html=True)

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [
        re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_")
        for c in out.columns
    ]
    return out

def find_column(df: pd.DataFrame, logical_name: str):
    cols = set(df.columns)
    for candidate in ALIASES.get(logical_name, []):
        normalized = re.sub(r"[^a-z0-9]+", "_", candidate.lower()).strip("_")
        if normalized in cols:
            return normalized
    return None

def detect_type(filename: str, df: pd.DataFrame):
    text = (filename + " " + " ".join(map(str, df.columns))).lower()
    scores = {kind: sum(1 for kw in kws if kw in text) for kind, kws in TYPE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    confidence = scores[best]
    return (best if confidence >= 1 else "unknown"), confidence

def read_file(uploaded_file) -> pd.DataFrame:
    data = uploaded_file.getvalue()
    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    return pd.read_excel(io.BytesIO(data))

def process_uploaded_files(uploaded_files) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
    datasets = {}
    notices = []
    for uploaded in uploaded_files:
        try:
            if uploaded.size == 0:
                notices.append(f"⚠️ {uploaded.name} is empty and was skipped.")
                continue
            df = clean_columns(read_file(uploaded))
            if df.empty:
                notices.append(f"⚠️ {uploaded.name} contains no data rows and was skipped.")
                continue

            df = df.drop_duplicates().copy()
            kind, confidence = detect_type(uploaded.name, df)

            if kind == "unknown":
                st.session_state["pending_classification"] = {
                    "filename": uploaded.name,
                    "dataframe": df,
                }
                # Use a neutral key so analysis can still proceed.
                kind = f"other_{len(datasets)+1}"
                notices.append(
                    f"ℹ️ {uploaded.name} could not be confidently identified. "
                    "It was kept as additional business data."
                )

            datasets[kind] = df
        except Exception:
            notices.append(
                f"⚠️ {uploaded.name} couldn't be read. Please make sure it is a valid CSV or Excel file."
            )
    return datasets, notices

def friendly_error(title, what, how, exc=None):
    st.error(f"⚠️ {title}")
    st.write(what)
    st.markdown(f"**How to fix it:** {how}")

def fmt_money(value):
    if value is None:
        return "—"
    return f"{value:,.0f}"

def fmt_pct(value):
    if value is None:
        return "—"
    return f"{value:.1f}%"

def require_analysis():
    if not st.session_state.get("analysis_ready"):
        st.info("Add your business records on the Home page first.")
        st.stop()
