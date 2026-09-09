import streamlit as st
import pandas as pd
import plotly.express as px
from utils.helpers import init_state, inject_css, require_analysis, find_column, fmt_money

st.set_page_config(page_title="FounderOS — Inventory", page_icon="📦", layout="wide")
inject_css(); init_state(); require_analysis()

st.title("📦 Inventory")
st.caption("Where is my money stuck in inventory?")
df = st.session_state.datasets.get("inventory")
facts = st.session_state.analysis["operations"]["facts"]["inventory"]

if df is None:
    st.info("No inventory file was provided. Inventory-specific analysis isn't available, but your other business analysis is still working.")
else:
    c1,c2,c3 = st.columns(3)
    c1.metric("Total units", f"{facts.get('total_units', 0):,.0f}")
    c2.metric("Low-stock items", f"{facts.get('low_stock_items', 0):,}")
    if facts.get("inventory_cost_value") is None:
        c3.metric("Inventory cost value", "Unavailable")
    else:
        c3.metric("Inventory cost value", fmt_money(facts["inventory_cost_value"]))

    if facts.get("inventory_cost_value") is None:
        st.info("Inventory value could not be calculated because purchase cost information wasn't found.")

    product = find_column(df, "product")
    qty = find_column(df, "quantity")
    if product and qty:
        x = df.copy()
        x[qty] = pd.to_numeric(x[qty], errors="coerce").fillna(0)
        grouped = x.groupby(product)[qty].sum().sort_values().head(15).reset_index()
        fig = px.bar(grouped, x=qty, y=product, orientation="h", title="Products with the lowest stock")
        fig.update_layout(margin=dict(l=10,r=10,t=50,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Operational intelligence")
ai = st.session_state.analysis["operations"]["ai"]
st.markdown(f'<div class="insight-card"><b>{ai.get("summary","")}</b></div>', unsafe_allow_html=True)
for item in ai.get("problems", []):
    st.warning(f"**{item.get('title')}** — {item.get('evidence')} Recommended: {item.get('action')}")
