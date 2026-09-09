import streamlit as st
from utils.helpers import init_state, inject_css, require_analysis, fmt_money, fmt_pct

st.set_page_config(page_title="FounderOS — Overview", page_icon="🏠", layout="wide")
inject_css(); init_state(); require_analysis()

a = st.session_state.analysis
f = a["financial"]["facts"]
s = a["strategy"]

st.title("🏠 Overview")
st.caption("A clear snapshot of what is happening in your business.")

health = None
try:
    from utils.calculations import calculate_health
    health = calculate_health({
        "revenue_trend": f.get("revenue_trend_pct"),
        "profit_margin": f.get("profit_margin"),
        "inventory_low_stock": a["operations"]["facts"]["inventory"].get("low_stock_items"),
    })
except Exception:
    pass

c1,c2,c3,c4 = st.columns(4)
c1.markdown(f'<div class="metric-card"><span class="small-label">Business Health</span><div class="kpi">{health if health is not None else "—"} / 100</div><span class="muted">Based on available data</span></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><span class="small-label">Revenue</span><div class="kpi">{fmt_money(f.get("revenue"))}</div><span class="muted">{fmt_pct(f.get("revenue_trend_pct"))} vs previous period</span></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><span class="small-label">Profit</span><div class="kpi">{fmt_money(f.get("profit"))}</div><span class="muted">{fmt_pct(f.get("profit_margin"))} margin</span></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><span class="small-label">Inventory Risk</span><div class="kpi">{"High" if a["operations"]["facts"]["inventory"].get("low_stock_items",0) > 10 else "Normal"}</div><span class="muted">Based on available stock data</span></div>', unsafe_allow_html=True)

st.divider()
st.subheader("What matters most")
st.markdown(f'<div class="insight-card"><b>{s.get("health_summary","Analysis summary unavailable.")}</b></div>', unsafe_allow_html=True)

st.subheader("🎯 Top priorities")
priorities = s.get("priorities", [])
if priorities:
    for p in priorities:
        st.markdown(
            f'<div class="priority-card"><b>{p.get("rank","")} · {p.get("title","Priority")}</b>'
            f'<br><span class="muted">{p.get("priority","")}</span>'
            f'<p>{p.get("why","")}</p><b>Recommended action:</b> {p.get("recommended_action","")}</div>',
            unsafe_allow_html=True,
        )
else:
    st.info("No AI priorities are available yet. Review the Finance, Inventory, and Customers pages for calculated insights.")

if not st.session_state.get("business_goal"):
    st.info("Some goal-based insights aren't available because you haven't provided a business goal. Your other business analysis is still available.")
