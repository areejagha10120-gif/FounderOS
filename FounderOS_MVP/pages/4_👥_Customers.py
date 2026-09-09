import streamlit as st
import pandas as pd
import plotly.express as px
from utils.helpers import init_state, inject_css, require_analysis, find_column, fmt_money

st.set_page_config(page_title="FounderOS — Customers & Sales", page_icon="👥", layout="wide")
inject_css(); init_state(); require_analysis()

st.title("👥 Customers & Sales")
st.caption("Where are my sales opportunities?")

sales = st.session_state.datasets.get("sales")
customers = st.session_state.datasets.get("customers")
df = customers if customers is not None else sales
facts = st.session_state.analysis["operations"]["facts"]["customers"]

if df is None:
    st.info("No sales or customer records were provided. Customer-specific analysis isn't available.")
else:
    c1,c2 = st.columns(2)
    c1.metric("Customers identified", facts.get("customer_count", "—"))
    c2.metric("Repeat customers", facts.get("repeat_customers", "—"))

    if not facts:
        st.info("Customer-level analysis isn't available because a customer identifier and purchase amount were not found. Your sales analysis can still continue.")
    else:
        top = facts.get("top_customers", {})
        if top:
            table = pd.DataFrame.from_dict(top, orient="index")
            table.index.name = "Customer"
            table = table.reset_index()
            st.subheader("Highest-value customers")
            st.dataframe(table, use_container_width=True, hide_index=True)

st.subheader("Sales intelligence")
ai = st.session_state.analysis["operations"]["ai"]
st.markdown(f'<div class="insight-card"><b>{ai.get("summary","")}</b></div>', unsafe_allow_html=True)
for item in ai.get("opportunities", []):
    st.success(f"**{item.get('title')}** — {item.get('evidence')} Recommended: {item.get('action')}")
