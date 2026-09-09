import streamlit as st
from auth import login_view, logout, is_authenticated
from utils.helpers import init_state, inject_css, friendly_error

st.set_page_config(
    page_title="FounderOS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
init_state()

if not is_authenticated():
    login_view()
    st.stop()

with st.sidebar:
    st.markdown("## FounderOS")
    st.caption("AI Operating System for Smarter Business Decisions")
    st.divider()
    st.markdown("### Your workspace")
    if st.session_state.get("business_goal"):
        st.info(f"Goal: {st.session_state.business_goal}")
    else:
        st.caption("No business goal provided — that's okay.")
    st.divider()
    if st.button("🚪 Log Out", use_container_width=True):
        logout()
        st.rerun()

st.title("Welcome to FounderOS")
st.markdown("### Turn your business records into clear decisions.")
st.write(
    "Start by adding your sales, expenses, inventory, or customer records. "
    "FounderOS will organize the information, calculate business metrics, and "
    "use three specialized AI agents to identify priorities and actions."
)

st.divider()

left, right = st.columns([1.35, 1])

with left:
    st.subheader("📁 Add your business records")
    st.caption(
        "Upload CSV or Excel files containing sales, expenses, inventory, "
        "or customer information. FounderOS will organize and analyze them for you."
    )
    uploaded = st.file_uploader(
        "Choose your business records",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    goal = st.text_input(
        "Business Goal (Optional)",
        value=st.session_state.get("business_goal", ""),
        placeholder="e.g. Increase profit, reduce expenses, improve sales",
    )
    st.session_state.business_goal = goal.strip() or None

    if uploaded:
        st.markdown("#### Files ready for analysis")
        for f in uploaded:
            st.write(f"• **{f.name}** — {f.size / 1024:.1f} KB")

        if st.button("✨ Analyze Business", type="primary", use_container_width=True):
            try:
                from utils.helpers import process_uploaded_files
                from agents.orchestrator import run_full_analysis

                with st.spinner("FounderOS is organizing your records…"):
                    datasets, notices = process_uploaded_files(uploaded)
                    st.session_state.datasets = datasets
                    st.session_state.data_notices = notices

                    if not datasets:
                        st.error(
                            "⚠️ We couldn't find usable business records. "
                            "Please check that your CSV or Excel files contain a header row and data."
                        )
                        st.stop()

                    analysis = run_full_analysis(
                        datasets,
                        st.session_state.business_goal,
                    )
                    st.session_state.analysis = analysis
                    st.session_state.analysis_ready = True

                st.success("Your business analysis is ready.")
                st.switch_page("pages/1_🏠_Overview.py")
            except Exception as exc:
                friendly_error(
                    "We couldn't complete the analysis",
                    "Something prevented FounderOS from finishing the analysis.",
                    "Check your files and API settings, then try again.",
                    exc,
                )

with right:
    st.subheader("How FounderOS works")
    steps = [
        ("01", "Understand", "Identify what each business file contains."),
        ("02", "Calculate", "Compute reliable metrics with Python and Pandas."),
        ("03", "Analyze", "Three specialized AI agents interpret the evidence."),
        ("04", "Prioritize", "The Strategy Agent turns findings into actions."),
    ]
    for n, title, desc in steps:
        st.markdown(
            f'<div class="feature-card"><span class="step-number">{n}</span>'
            f'<div><b>{title}</b><br><span class="muted">{desc}</span></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="privacy-note"><b>Privacy note</b><br>'
        "Only upload business information you are authorized to share. "
        "Keep your API keys and secrets out of your files.</div>",
        unsafe_allow_html=True,
    )

if st.session_state.get("data_notices"):
    st.divider()
    st.subheader("File notes")
    for note in st.session_state.data_notices:
        st.info(note)
