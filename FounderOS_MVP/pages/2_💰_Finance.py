import streamlit as st
import pandas as pd
import plotly.express as px
from utils.helpers import init_state, inject_css, require_analysis, find_column, fmt_money, fmt_pct

st.set_page_config(page_title="FounderOS — Finance", page_icon="💰", layout="wide")
inject_css(); init_state(); require_analysis()

a = st.session_state.analysis
f = a["financial"]["facts"]
st.title("💰 Finance")
st.caption("Am I actually making money, and what's affecting it?")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Revenue", fmt_money(f.get("revenue")))
c2.metric("Expenses", fmt_money(f.get("expenses")))
c3.metric("Profit", fmt_money(f.get("profit")))
c4.metric("Profit margin", fmt_pct(f.get("profit_margin")))

st.divider()
sales = st.session_state.datasets.get("sales")
expenses = st.session_state.datasets.get("expenses")

if sales is not None and find_column(sales, "date") and find_column(sales, "amount"):
    d = sales.copy()
    dc, ac = find_column(d,"date"), find_column(d,"amount")
    d[dc] = pd.to_datetime(d[dc], errors="coerce")
    d[ac] = pd.to_numeric(d[ac], errors="coerce")
    d = d.dropna(subset=[dc,ac])
    if not d.empty:
        monthly = d.assign(period=d[dc].dt.to_period("M").astype(str)).groupby("period")[ac].sum().reset_index()
        fig = px.line(monthly, x="period", y=ac, markers=True, title="Revenue trend")
        fig.update_layout(margin=dict(l=10,r=10,t=50,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("A revenue trend chart isn't available because dated sales amounts were not found.")

if expenses is not None and find_column(expenses, "category") and find_column(expenses, "amount"):
    ec, ac = find_column(expenses,"category"), find_column(expenses,"amount")
    x = expenses.copy()
    x[ac] = pd.to_numeric(x[ac], errors="coerce").fillna(0)
    cat = x.groupby(ec)[ac].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(cat, x=ec, y=ac, title="Expenses by category")
    fig.update_layout(margin=dict(l=10,r=10,t=50,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Financial intelligence")
ai = a["financial"]["ai"]
st.markdown(f'<div class="insight-card"><b>{ai.get("summary","")}</b></div>', unsafe_allow_html=True)
for item in ai.get("problems", []):
    st.warning(f"**{item.get('title')}** — {item.get('evidence')} Recommended: {item.get('action')}")
for item in ai.get("opportunities", []):
    st.success(f"**{item.get('title')}** — {item.get('evidence')} Recommended: {item.get('action')}")
