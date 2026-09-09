import hashlib
import io
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import plotly.express as px
import streamlit as st

from auth import get_supabase, login, logout, signup
from utils.helpers import find_column, process_uploaded_files, fmt_money, fmt_pct

# -----------------------------------------------------------------------------
# FounderOS — single-entry application
# This version keeps the workspace in session state and uses an in-process
# background worker for the AI analysis so changing the internal menu does not
# discard the uploaded data or analysis job.
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="FounderOS",
    page_icon="FOS",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Background jobs live at the server-process level, not inside a Streamlit
# rerun. The uploaded data itself remains in the user's session state.
# Process-global background worker + job registry. This lets an analysis
# continue while the user changes FounderOS sections or temporarily leaves
# the browser. Jobs are intentionally in memory; uploaded business files are
# not written to permanent storage by this app.
try:
    _JOB_LOCK
except NameError:
    _JOB_LOCK = threading.Lock()
    _ANALYSIS_JOBS = {}
    _ANALYSIS_EXECUTOR = ThreadPoolExecutor(max_workers=4)


# -----------------------------------------------------------------------------
# State
# -----------------------------------------------------------------------------
def init_app_state():
    defaults = {
        "user": None,
        "session": None,
        "datasets": {},
        "analysis": None,
        "analysis_ready": False,
        "analysis_status": "idle",  # idle | processing | ready | error
        "analysis_job_id": None,
        "analysis_error": None,
        "business_goal": None,
        "data_notices": [],
        "stored_files": {},
        "workspace_fingerprint": None,
        "advisor_messages": [],
        "theme": "Midnight Luxury",
        "menu_page": "Dashboard",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_app_state()


# -----------------------------------------------------------------------------
# Theme / visual system
# -----------------------------------------------------------------------------
def inject_fos_css():
    st.markdown(
        """
<style>
/* FounderOS theme-only CSS. Application logic, state, data processing and layout are untouched. */

/* Exact brand tokens for the two requested themes. */
[data-theme="dark"] {
  --background-color: #0A1128;
  --text-color: #F4F4F6;
  --secondary-background-color: #1C2541;
  --secondary-text-color: #F4F4F6;
  --primary-color: #D4AF37;
  --input-border-color: #1C2541;
  --input-focus-color: #D4AF37;
  --card-border-color: #1C2541;
}

[data-theme="light"] {
  --background-color: #F0F4F8;
  --text-color: #0F2537;
  --secondary-background-color: #F0F4F8;
  --secondary-text-color: #627D98;
  --primary-color: #185ADB;
  --input-border-color: #627D98;
  --input-focus-color: #185ADB;
  --card-border-color: #627D98;
}

/* Streamlit versions/themes that expose the variables on a higher ancestor. */
.stApp {
  background: var(--background-color, #0A1128) !important;
  color: var(--text-color, #F4F4F6) !important;
}

/* Top Streamlit header/chrome: unified with FounderOS instead of a white strip. */
[data-theme="dark"] header[data-testid="stHeader"],
[data-theme="light"] header[data-testid="stHeader"] {
  background: var(--background-color) !important;
  color: var(--text-color) !important;
}
[data-theme="dark"] header[data-testid="stHeader"] button,
[data-theme="light"] header[data-testid="stHeader"] button,
[data-theme="dark"] header[data-testid="stHeader"] svg,
[data-theme="light"] header[data-testid="stHeader"] svg {
  color: var(--text-color) !important;
  fill: currentColor !important;
  stroke: currentColor !important;
}
[data-theme="dark"] header[data-testid="stHeader"] button:hover,
[data-theme="light"] header[data-testid="stHeader"] button:hover {
  background: var(--secondary-background-color) !important;
}

/* Main page and sidebar */
.block-container {
  max-width: 1450px;
  padding-top: 2rem;
  padding-bottom: 4rem;
}
[data-testid="stSidebarNav"] { display: none !important; }
[data-theme="dark"] [data-testid="stSidebar"],
[data-theme="light"] [data-testid="stSidebar"] {
  background: var(--background-color) !important;
  border-right: 1px solid var(--primary-color) !important;
}
[data-theme="dark"] [data-testid="stSidebar"] *,
[data-theme="light"] [data-testid="stSidebar"] * {
  color: var(--text-color) !important;
}

/* Native Streamlit typography. */
[data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3,
[data-theme="dark"] h4, [data-theme="dark"] h5, [data-theme="dark"] h6,
[data-theme="light"] h1, [data-theme="light"] h2, [data-theme="light"] h3,
[data-theme="light"] h4, [data-theme="light"] h5, [data-theme="light"] h6,
[data-theme="dark"] [data-testid="stMarkdownContainer"] p,
[data-theme="light"] [data-testid="stMarkdownContainer"] p,
[data-theme="dark"] label, [data-theme="light"] label {
  color: var(--text-color) !important;
}
[data-theme="dark"] [data-testid="stCaptionContainer"],
[data-theme="light"] [data-testid="stCaptionContainer"],
[data-theme="dark"] .stCaption, [data-theme="light"] .stCaption {
  color: var(--secondary-text-color) !important;
}
[data-theme="dark"] a, [data-theme="dark"] a:visited,
[data-theme="light"] a, [data-theme="light"] a:visited {
  color: var(--primary-color) !important;
}

/* Buttons/CTAs: text uses the theme token, never a fixed black/white value. */
[data-theme="dark"] .stButton > button,
[data-theme="light"] .stButton > button,
[data-theme="dark"] .stDownloadButton > button,
[data-theme="light"] .stDownloadButton > button,
[data-theme="dark"] [data-testid="stFormSubmitButton"] button,
[data-theme="light"] [data-testid="stFormSubmitButton"] button,
[data-theme="dark"] button[kind="primary"],
[data-theme="light"] button[kind="primary"],
[data-theme="dark"] button[kind="secondary"],
[data-theme="light"] button[kind="secondary"] {
  color: var(--text-color) !important;
  background: var(--secondary-background-color) !important;
  border: 1px solid var(--primary-color) !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
}
[data-theme="dark"] .stButton > button:hover,
[data-theme="dark"] .stDownloadButton > button:hover,
[data-theme="dark"] [data-testid="stFormSubmitButton"] button:hover,
[data-theme="dark"] button[kind="primary"]:hover,
[data-theme="dark"] button[kind="secondary"]:hover,
[data-theme="light"] .stButton > button:hover,
[data-theme="light"] .stDownloadButton > button:hover,
[data-theme="light"] [data-testid="stFormSubmitButton"] button:hover,
[data-theme="light"] button[kind="primary"]:hover,
[data-theme="light"] button[kind="secondary"]:hover {
  color: var(--background-color) !important;
  background: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
}

/* Inputs: requested slate/gold borders in dark and slate/cobalt in light. */
[data-theme="dark"] .stTextInput input,
[data-theme="dark"] .stTextArea textarea,
[data-theme="dark"] [data-baseweb="input"] input,
[data-theme="dark"] [data-baseweb="textarea"] textarea,
[data-theme="dark"] .stSelectbox [data-baseweb="select"] > div,
[data-theme="dark"] .stMultiSelect [data-baseweb="select"] > div,
[data-theme="light"] .stTextInput input,
[data-theme="light"] .stTextArea textarea,
[data-theme="light"] [data-baseweb="input"] input,
[data-theme="light"] [data-baseweb="textarea"] textarea,
[data-theme="light"] .stSelectbox [data-baseweb="select"] > div,
[data-theme="light"] .stMultiSelect [data-baseweb="select"] > div {
  background: var(--secondary-background-color) !important;
  color: var(--text-color) !important;
  border: 1px solid var(--input-border-color) !important;
  box-shadow: none !important;
}
[data-theme="dark"] .stTextInput input:focus,
[data-theme="dark"] .stTextArea textarea:focus,
[data-theme="dark"] [data-baseweb="input"] input:focus,
[data-theme="dark"] [data-baseweb="textarea"] textarea:focus,
[data-theme="light"] .stTextInput input:focus,
[data-theme="light"] .stTextArea textarea:focus,
[data-theme="light"] [data-baseweb="input"] input:focus,
[data-theme="light"] [data-baseweb="textarea"] textarea:focus {
  border-color: var(--input-focus-color) !important;
  box-shadow: 0 0 0 1px var(--input-focus-color) !important;
  outline: none !important;
}
[data-theme="dark"] input::placeholder, [data-theme="dark"] textarea::placeholder,
[data-theme="light"] input::placeholder, [data-theme="light"] textarea::placeholder {
  color: var(--secondary-text-color) !important;
  opacity: 1 !important;
}

/* File uploader: readable in both modes, including uploaded-file chips. */
[data-theme="dark"] [data-testid="stFileUploader"],
[data-theme="light"] [data-testid="stFileUploader"] {
  background: var(--secondary-background-color) !important;
  border: 1px dashed var(--input-border-color) !important;
  border-radius: 14px !important;
}
[data-theme="dark"] [data-testid="stFileUploader"] *,
[data-theme="light"] [data-testid="stFileUploader"] * {
  color: var(--text-color) !important;
}
[data-theme="dark"] [data-testid="stFileUploader"] small,
[data-theme="light"] [data-testid="stFileUploader"] small {
  color: var(--secondary-text-color) !important;
}
[data-theme="dark"] [data-testid="stFileUploaderDropzone"],
[data-theme="light"] [data-testid="stFileUploaderDropzone"] {
  background: var(--secondary-background-color) !important;
  border-color: var(--input-border-color) !important;
}
[data-theme="dark"] [data-testid="stFileUploader"] [data-baseweb="tag"],
[data-theme="light"] [data-testid="stFileUploader"] [data-baseweb="tag"],
[data-theme="dark"] [data-testid="stFileUploader"] [role="listitem"],
[data-theme="light"] [data-testid="stFileUploader"] [role="listitem"] {
  background: var(--secondary-background-color) !important;
  border: 1px solid var(--input-border-color) !important;
}
[data-theme="dark"] [data-testid="stFileUploader"] [data-baseweb="tag"] *,
[data-theme="light"] [data-testid="stFileUploader"] [data-baseweb="tag"] *,
[data-theme="dark"] [data-testid="stFileUploader"] [role="listitem"] *,
[data-theme="light"] [data-testid="stFileUploader"] [role="listitem"] * {
  color: var(--text-color) !important;
}

/* BaseWeb select/dropdown menus. They may be rendered outside the selectbox. */
[data-theme="dark"] [data-baseweb="popover"],
[data-theme="dark"] [role="listbox"],
[data-theme="dark"] [role="option"],
[data-theme="dark"] [data-baseweb="menu"] {
  background: var(--secondary-background-color) !important;
  color: var(--text-color) !important;
}
[data-theme="light"] [data-baseweb="popover"],
[data-theme="light"] [role="listbox"],
[data-theme="light"] [role="option"],
[data-theme="light"] [data-baseweb="menu"] {
  background: var(--background-color) !important;
  color: var(--text-color) !important;
}
[data-theme="dark"] [role="option"]:hover,
[data-theme="dark"] [role="option"][aria-selected="true"],
[data-theme="light"] [role="option"]:hover,
[data-theme="light"] [role="option"][aria-selected="true"] {
  background: var(--primary-color) !important;
  color: var(--background-color) !important;
}
[data-baseweb="popover"] *, [role="listbox"] *, [role="option"] * {
  color: inherit !important;
}

/* Metrics, cards, expanders and other existing visual components. */
[data-theme="dark"] [data-testid="stMetric"],
[data-theme="light"] [data-testid="stMetric"] {
  background: var(--secondary-background-color) !important;
  border: 1px solid var(--card-border-color) !important;
  border-radius: 14px;
  padding: 16px;
}
[data-theme="dark"] [data-testid="stMetricLabel"], [data-theme="light"] [data-testid="stMetricLabel"] {
  color: var(--secondary-text-color) !important;
}
[data-theme="dark"] [data-testid="stMetricValue"], [data-theme="light"] [data-testid="stMetricValue"] {
  color: var(--text-color) !important;
}
[data-theme="dark"] .fos-card, [data-theme="light"] .fos-card,
[data-theme="dark"] .fos-feature, [data-theme="light"] .fos-feature,
[data-theme="dark"] .fos-status, [data-theme="light"] .fos-status,
[data-theme="dark"] .fos-purpose, [data-theme="light"] .fos-purpose {
  background: var(--secondary-background-color) !important;
  border-color: var(--card-border-color) !important;
}
[data-theme="dark"] .fos-card-gold, [data-theme="light"] .fos-card-gold {
  border-color: var(--primary-color) !important;
}
[data-theme="dark"] .fos-card *, [data-theme="light"] .fos-card *,
[data-theme="dark"] .fos-feature *, [data-theme="light"] .fos-feature *,
[data-theme="dark"] .fos-status *, [data-theme="light"] .fos-status *,
[data-theme="dark"] .fos-purpose *, [data-theme="light"] .fos-purpose * {
  color: var(--text-color);
}
[data-theme="dark"] .fos-muted, [data-theme="light"] .fos-muted,
[data-theme="dark"] .fos-feature-text, [data-theme="light"] .fos-feature-text,
[data-theme="dark"] .fos-purpose span, [data-theme="light"] .fos-purpose span,
[data-theme="dark"] .fos-nav-label, [data-theme="light"] .fos-nav-label {
  color: var(--secondary-text-color) !important;
}
[data-theme="dark"] .fos-gold, [data-theme="light"] .fos-gold,
[data-theme="dark"] .fos-nav-current, [data-theme="light"] .fos-nav-current,
[data-theme="dark"] .fos-feature-mark, [data-theme="light"] .fos-feature-mark {
  color: var(--primary-color) !important;
}
[data-theme="dark"] .fos-kpi, [data-theme="light"] .fos-kpi,
[data-theme="dark"] .fos-auth-title, [data-theme="light"] .fos-auth-title,
[data-theme="dark"] .fos-feature-title, [data-theme="light"] .fos-feature-title,
[data-theme="dark"] .fos-purpose strong, [data-theme="light"] .fos-purpose strong {
  color: var(--text-color) !important;
}
[data-theme="dark"] .fos-pill, [data-theme="light"] .fos-pill {
  color: var(--text-color) !important;
  border-color: var(--primary-color) !important;
}
[data-theme="dark"] .fos-section-note, [data-theme="light"] .fos-section-note {
  color: var(--secondary-text-color) !important;
  border-left-color: var(--primary-color) !important;
}
[data-theme="dark"] .fos-empty, [data-theme="light"] .fos-empty {
  background: var(--secondary-background-color) !important;
  border-color: var(--card-border-color) !important;
}
[data-theme="dark"] [data-testid="stExpander"],
[data-theme="light"] [data-testid="stExpander"] {
  background: var(--secondary-background-color) !important;
  border-color: var(--card-border-color) !important;
}
[data-theme="dark"] [data-testid="stExpander"] *,
[data-theme="light"] [data-testid="stExpander"] * {
  color: var(--text-color);
}
[data-theme="dark"] [data-baseweb="tab"], [data-theme="light"] [data-baseweb="tab"] {
  color: var(--secondary-text-color) !important;
}
[data-theme="dark"] [data-baseweb="tab"][aria-selected="true"],
[data-theme="light"] [data-baseweb="tab"][aria-selected="true"] {
  color: var(--primary-color) !important;
}
[data-theme="dark"] [data-testid="stDataFrame"],
[data-theme="light"] [data-testid="stDataFrame"] {
  border-color: var(--card-border-color) !important;
}

/* Native alerts inherit the active theme instead of Streamlit's default text. */
[data-theme="dark"] [data-testid="stAlert"],
[data-theme="light"] [data-testid="stAlert"] {
  color: var(--text-color) !important;
}
[data-theme="dark"] [data-testid="stAlert"] *,
[data-theme="light"] [data-testid="stAlert"] * {
  color: inherit !important;
}

/* FOS logos retain the exact midnight/navy brand mark while the surrounding text adapts. */
.fos-logo, .fos-auth-logo {
  background: #0A1128 !important;
  border-color: var(--primary-color) !important;
  color: var(--primary-color) !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


inject_fos_css()


# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------
def authenticated():
    return bool(st.session_state.get("user"))


def set_logged_in(result):
    if getattr(result, "user", None):
        st.session_state.user = result.user
    if getattr(result, "session", None):
        st.session_state.session = result.session


def render_auth_screen():
    left, right = st.columns([1.05, 1.0], gap="large")

    with left:
        st.markdown('<div class="fos-auth-wrap">', unsafe_allow_html=True)
        st.markdown('<div class="fos-auth-logo">FOS</div>', unsafe_allow_html=True)
        st.markdown('<div class="fos-auth-title">FounderOS</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="fos-auth-sub">Turn scattered business records into clear decisions, priorities, and actions.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Log in", "Create profile"])

        with tab_login:
            with st.form("fos_login"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in to FounderOS", use_container_width=True)
            if submitted:
                if not email.strip() or not password:
                    st.error("Enter your email and password.")
                else:
                    try:
                        result = login(email.strip(), password)
                        set_logged_in(result)
                        st.success("Welcome back.")
                        st.rerun()
                    except Exception:
                        st.error("We couldn't log you in. Check your email/password and Supabase Auth settings.")

        with tab_signup:
            with st.form("fos_signup"):
                email = st.text_input("Email", key="fos_signup_email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", key="fos_signup_password")
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create profile & continue", use_container_width=True)
            if submitted:
                if not email.strip() or not password:
                    st.error("Enter an email and password.")
                elif password != confirm:
                    st.error("Your passwords don't match.")
                elif len(password) < 6:
                    st.error("Use a password with at least 6 characters.")
                else:
                    try:
                        result = signup(email.strip(), password)
                        # If Supabase Email Confirmation is disabled, Supabase
                        # returns a session and the user enters immediately.
                        if getattr(result, "session", None):
                            set_logged_in(result)
                            st.success("Profile created. You're in.")
                            st.rerun()
                        else:
                            st.success(
                                "Profile created, but Supabase requires email confirmation before access. "
                                "Disable Confirm email in Supabase Auth if you want signup to enter the app immediately."
                            )
                    except Exception:
                        st.error("We couldn't create the profile. The email may already exist or Supabase needs configuration.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="fos-card fos-card-gold"><span class="fos-pill">THE FOUNDEROS CORE</span><h2>One workspace. Five decision views.</h2><p class="fos-muted">Your data stays at the center while FounderOS turns it into measurable business intelligence.</p></div>', unsafe_allow_html=True)
        features = [
            ("01", "Business Overview", "See business health, revenue, profit, warnings, opportunities, and the highest-priority actions in one place."),
            ("02", "Financial Intelligence", "Understand revenue, expenses, profit, margins, trends, and unusual financial patterns."),
            ("03", "Inventory Intelligence", "Spot low stock, slow-moving products, inventory risk, and money tied up when the data supports it."),
            ("04", "Customers & Sales", "Find high-value and repeat customers, purchasing patterns, and sales opportunities when customer data exists."),
            ("05", "AI Business Advisor", "Ask questions about your uploaded records and get evidence-based answers instead of generic business advice."),
        ]
        for num, title, text in features:
            st.markdown(
                f'<div class="fos-feature"><div class="fos-feature-mark">{num}</div><div class="fos-feature-title">{title}</div><div class="fos-feature-text">{text}</div></div>',
                unsafe_allow_html=True,
            )


if not authenticated():
    render_auth_screen()
    st.stop()


# -----------------------------------------------------------------------------
# Analysis jobs
# -----------------------------------------------------------------------------
def _job_key():
    user = st.session_state.get("user")
    uid = getattr(user, "id", None) or getattr(user, "email", None) or "anonymous"
    return str(uid)


def _run_analysis_job(job_id, datasets, goal):
    try:
        from agents.orchestrator import run_full_analysis
        result = run_full_analysis(datasets, goal)
        with _JOB_LOCK:
            _ANALYSIS_JOBS[job_id] = {"status": "ready", "analysis": result, "error": None}
    except Exception as exc:
        with _JOB_LOCK:
            _ANALYSIS_JOBS[job_id] = {
                "status": "error",
                "analysis": None,
                "error": str(exc),
            }


def start_analysis(datasets, goal):
    raw = goal or ""
    fingerprint_source = raw + "|" + "|".join(
        f"{k}:{len(v)}:{','.join(v.columns)}" for k, v in sorted(datasets.items())
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()

    # Avoid starting the exact same analysis twice.
    if st.session_state.get("workspace_fingerprint") == fingerprint and st.session_state.get("analysis_ready"):
        return

    job_id = f"{_job_key()}::{fingerprint}"
    with _JOB_LOCK:
        existing = _ANALYSIS_JOBS.get(job_id)
        if existing and existing.get("status") in {"processing", "ready"}:
            st.session_state.analysis_job_id = job_id
            st.session_state.analysis_status = existing["status"]
            return
        _ANALYSIS_JOBS[job_id] = {"status": "processing", "analysis": None, "error": None}

    st.session_state.analysis_job_id = job_id
    st.session_state.analysis_status = "processing"
    st.session_state.analysis_ready = False
    st.session_state.analysis_error = None
    st.session_state.workspace_fingerprint = fingerprint

    _ANALYSIS_EXECUTOR.submit(_run_analysis_job, job_id, datasets, goal)


def sync_analysis_job():
    job_id = st.session_state.get("analysis_job_id")
    if not job_id:
        return
    with _JOB_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
    if not job:
        return
    st.session_state.analysis_status = job["status"]
    if job["status"] == "ready":
        st.session_state.analysis = job["analysis"]
        st.session_state.analysis_ready = True
        st.session_state.analysis_error = None
    elif job["status"] == "error":
        st.session_state.analysis_ready = False
        st.session_state.analysis_error = job.get("error")


sync_analysis_job()


# -----------------------------------------------------------------------------
# Navigation / sidebar
# -----------------------------------------------------------------------------
PAGES = ["Dashboard", "Finance", "Inventory", "Customers & Sales", "AI Advisor"]

with st.sidebar:
    st.markdown(
        '<div class="fos-brand"><div class="fos-logo">FOS</div><div><b style="font-size:1.15rem">FounderOS</b><br><span class="fos-muted fos-small">Decision intelligence</span></div></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown('<div class="fos-nav-label">Workspace</div>', unsafe_allow_html=True)
    selected = st.selectbox(
        "Go to",
        PAGES,
        index=PAGES.index(st.session_state.get("menu_page", "Dashboard")),
        label_visibility="collapsed",
    )
    st.session_state.menu_page = selected

    st.markdown('<div class="fos-status"><span class="fos-muted fos-small">Data workspace</span><br><b>{}</b><br><span class="fos-muted fos-small">{} file(s) loaded</span></div>'.format(
        "Analysis ready" if st.session_state.analysis_ready else (
            "Analysis in progress" if st.session_state.analysis_status == "processing" else "Waiting for records"
        ),
        len(st.session_state.stored_files),
    ), unsafe_allow_html=True)

    if st.session_state.get("business_goal"):
        st.markdown('<div class="fos-status"><span class="fos-muted fos-small">Current goal</span><br><b>{}</b></div>'.format(st.session_state.business_goal), unsafe_allow_html=True)

    if st.button("Log out", use_container_width=True):
        logout()
        # logout() already clears the original auth state. Clear our new state too.
        for key in [
            "datasets", "analysis", "analysis_ready", "analysis_status", "analysis_job_id",
            "analysis_error", "business_goal", "data_notices", "stored_files", "workspace_fingerprint",
            "advisor_messages", "user", "session",
        ]:
            st.session_state.pop(key, None)
        st.rerun()


# -----------------------------------------------------------------------------
# Shared helpers
# -----------------------------------------------------------------------------
def money_or_dash(v):
    return fmt_money(v) if v is not None else "—"


def purpose_panel(items):
    for title, text in items:
        st.markdown(
            f'<div class="fos-purpose"><strong>{title}</strong><br><span>{text}</span></div>',
            unsafe_allow_html=True,
        )


def no_data_page(title, subtitle, purpose_items):
    st.title(title)
    st.caption(subtitle)
    st.markdown('<div class="fos-empty"><h3>No analysis loaded yet</h3><p class="fos-muted">Upload your business records from Dashboard. This page will remain available and will populate automatically once analysis is ready.</p></div>', unsafe_allow_html=True)
    st.subheader("What you will get here")
    purpose_panel(purpose_items)


def health_score():
    if not st.session_state.analysis_ready:
        return None
    try:
        from utils.calculations import calculate_health
        f = st.session_state.analysis["financial"]["facts"]
        inv = st.session_state.analysis["operations"]["facts"].get("inventory", {})
        return calculate_health({
            "revenue_trend": f.get("revenue_trend_pct"),
            "profit_margin": f.get("profit_margin"),
            "inventory_low_stock": inv.get("low_stock_items"),
        })
    except Exception:
        return None


def show_job_status():
    if st.session_state.analysis_status == "processing":
        st.info("FounderOS is analyzing your records in the background. You can move between sections while this continues. Return to Dashboard or refresh to see the completed analysis.")
    elif st.session_state.analysis_status == "error":
        st.error("The analysis could not be completed. Your uploaded records are still loaded. Check your Gemini configuration and try Analyze again.")


# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
def render_dashboard():
    st.title("Dashboard")
    st.caption("Your FounderOS command center — upload once, then explore without losing your workspace.")

    # Always-visible purpose / workflow column on the right.
    left, right = st.columns([1.55, 0.85], gap="large")

    with left:
        st.subheader("Business data")
        st.markdown('<div class="fos-section-note">Upload one or more CSV/XLSX files. FounderOS keeps the processed workspace in your session while you move through the menu.</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Business records",
            type=["csv", "xlsx"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="dashboard_uploader",
        )

        if uploaded:
            # Capture every selected file as bytes. On later reruns the
            # browser uploader can be empty, but the workspace remains alive
            # from these stored bytes.
            try:
                for f in uploaded:
                    st.session_state.stored_files[f.name] = {
                        "bytes": f.getvalue(),
                        "size": f.size,
                    }

                class _StoredUpload:
                    def __init__(self, name, payload):
                        self.name = name
                        self._payload = payload
                        self.size = len(payload)
                    def getvalue(self):
                        return self._payload

                all_stored = [
                    _StoredUpload(name, meta["bytes"])
                    for name, meta in st.session_state.stored_files.items()
                ]
                datasets, notices = process_uploaded_files(all_stored)
                if datasets:
                    st.session_state.datasets = datasets
                    st.session_state.data_notices = notices
                    st.session_state.analysis_ready = False
                    st.session_state.analysis = None
                    st.session_state.analysis_status = "idle"
                    st.session_state.analysis_error = None
                    st.session_state.analysis_job_id = None
                    st.session_state.workspace_fingerprint = None
            except Exception:
                st.error("FounderOS couldn't read one or more files. Please use valid CSV or XLSX business records.")

        # Persisted workspace indicator. This remains visible even after the
        # file uploader itself has no new browser value on another rerun.
        if st.session_state.stored_files:
            st.markdown("#### Loaded records")
            for name, meta in st.session_state.stored_files.items():
                st.markdown(f'<div class="fos-card"><b>{name}</b><br><span class="fos-muted">{meta["size"] / 1024:.1f} KB</span></div>', unsafe_allow_html=True)

        goal = st.text_input(
            "Business goal (optional)",
            value=st.session_state.get("business_goal") or "",
            placeholder="e.g. Increase profit, reduce unnecessary expenses, improve repeat sales",
            key="dashboard_goal",
        )
        st.session_state.business_goal = (goal or "").strip() or None

        if st.session_state.datasets:
            st.markdown("#### Data detected")
            cols = st.columns(min(4, max(1, len(st.session_state.datasets))))
            for i, (kind, df) in enumerate(st.session_state.datasets.items()):
                cols[i % len(cols)].metric(kind.replace("_", " ").title(), f"{len(df):,} rows")

            if st.button("Analyze Business", type="primary", use_container_width=True):
                try:
                    start_analysis(st.session_state.datasets, st.session_state.business_goal)
                    st.rerun()
                except Exception:
                    st.error("FounderOS couldn't start the analysis. Your records are still loaded; try again.")

        show_job_status()

        # Actual analysis on the left when available.
        if st.session_state.analysis_ready:
            a = st.session_state.analysis
            f = a["financial"]["facts"]
            st.subheader("Live business analysis")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Business health", f"{health_score()}/100" if health_score() is not None else "—")
            k2.metric("Revenue", money_or_dash(f.get("revenue")))
            k3.metric("Profit", money_or_dash(f.get("profit")))
            k4.metric("Profit margin", fmt_pct(f.get("profit_margin")))

            sales = st.session_state.datasets.get("sales")
            if sales is not None:
                dc, ac = find_column(sales, "date"), find_column(sales, "amount")
                if dc and ac:
                    d = sales.copy()
                    d[dc] = pd.to_datetime(d[dc], errors="coerce")
                    d[ac] = pd.to_numeric(d[ac], errors="coerce")
                    d = d.dropna(subset=[dc, ac])
                    if not d.empty:
                        monthly = d.assign(period=d[dc].dt.to_period("M").astype(str)).groupby("period")[ac].sum().reset_index()
                        fig = px.line(monthly, x="period", y=ac, markers=True, title="Revenue trend")
                        fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#F4F4F6"))
                        st.plotly_chart(fig, use_container_width=True)

            strategy = a.get("strategy", {})
            st.markdown("### What matters most")
            st.markdown(f'<div class="fos-card fos-card-gold"><b>{strategy.get("health_summary", "Analysis summary unavailable.")}</b></div>', unsafe_allow_html=True)

            priorities = strategy.get("priorities", [])
            if priorities:
                st.markdown("### Priority actions")
                for p in priorities[:5]:
                    st.markdown(
                        f'<div class="fos-card"><span class="fos-pill">{p.get("priority", "PRIORITY")}</span><h4>{p.get("rank", "")} · {p.get("title", "Priority")}</h4><p class="fos-muted">{p.get("why", "")}</p><b>Recommended action:</b> {p.get("recommended_action", "")}</div>',
                        unsafe_allow_html=True,
                    )
        elif st.session_state.datasets:
            st.markdown('<div class="fos-empty"><h3>Your records are loaded.</h3><p class="fos-muted">Click Analyze Business. Once started, the AI analysis runs as a background job so switching FounderOS sections does not discard your workspace.</p></div>', unsafe_allow_html=True)

    with right:
        st.subheader("What this workspace does")
        purpose_panel([
            ("Understand", "Recognizes sales, expenses, inventory, and customer records from the files you provide."),
            ("Calculate", "Uses Pandas-based calculations for revenue, expenses, profit, margins, trends, stock, and customer metrics when available."),
            ("Analyze", "Runs Financial Intelligence and Operations Intelligence against the actual uploaded data."),
            ("Prioritize", "The Strategy layer converts evidence into a short list of actions instead of overwhelming you with generic advice."),
            ("Ask", "AI Advisor lets you ask follow-up questions using the saved business context."),
        ])
        st.markdown('<div class="fos-card fos-card-gold"><b>Navigation promise</b><p class="fos-muted">Changing sections does not clear your uploaded records. Your current session keeps the workspace until you log out or the Streamlit session ends.</p></div>', unsafe_allow_html=True)
        if st.session_state.data_notices:
            st.markdown("### File notes")
            for note in st.session_state.data_notices:
                st.info(note)

        if st.button("Clear workspace", use_container_width=True):
            for key, value in {
                "datasets": {}, "analysis": None, "analysis_ready": False,
                "analysis_status": "idle", "analysis_job_id": None,
                "analysis_error": None, "business_goal": None,
                "data_notices": [], "stored_files": {},
                "workspace_fingerprint": None,
            }.items():
                st.session_state[key] = value
            st.rerun()


# -----------------------------------------------------------------------------
# Finance
# -----------------------------------------------------------------------------
def render_finance():
    if not st.session_state.analysis_ready:
        no_data_page("Finance", "Understand whether the business is making money and what is affecting it.", [
            ("Revenue", "Total revenue and the direction of revenue over the available periods."),
            ("Expenses", "Total expenses and category-level spending when expense data exists."),
            ("Profit & margin", "Calculated profit and profit margin when the necessary figures are available."),
            ("Trends", "Visual revenue and expense movement when dated amounts exist."),
        ])
        return
    a = st.session_state.analysis
    f = a["financial"]["facts"]
    st.title("Finance")
    st.caption("Understand the financial engine behind your business.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", money_or_dash(f.get("revenue")))
    c2.metric("Expenses", money_or_dash(f.get("expenses")))
    c3.metric("Profit", money_or_dash(f.get("profit")))
    c4.metric("Profit margin", fmt_pct(f.get("profit_margin")))

    sales = st.session_state.datasets.get("sales")
    expenses = st.session_state.datasets.get("expenses")
    left, right = st.columns([1.45, .85])
    with left:
        if sales is not None:
            dc, ac = find_column(sales, "date"), find_column(sales, "amount")
            if dc and ac:
                d = sales.copy()
                d[dc] = pd.to_datetime(d[dc], errors="coerce")
                d[ac] = pd.to_numeric(d[ac], errors="coerce")
                d = d.dropna(subset=[dc, ac])
                if not d.empty:
                    monthly = d.assign(period=d[dc].dt.to_period("M").astype(str)).groupby("period")[ac].sum().reset_index()
                    fig = px.line(monthly, x="period", y=ac, markers=True, title="Revenue trend")
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#F4F4F6"))
                    st.plotly_chart(fig, use_container_width=True)
        if expenses is not None:
            ec, ac = find_column(expenses, "category"), find_column(expenses, "amount")
            if ec and ac:
                x = expenses.copy(); x[ac] = pd.to_numeric(x[ac], errors="coerce").fillna(0)
                cat = x.groupby(ec)[ac].sum().sort_values(ascending=False).reset_index()
                fig = px.bar(cat, x=ec, y=ac, title="Expenses by category")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#F4F4F6"))
                st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("What you get here")
        purpose_panel([
            ("Financial snapshot", "Revenue, expenses, profit, and margin at a glance."),
            ("Trend visibility", "Spot whether revenue or expenses are moving up or down."),
            ("Category insight", "See which expense categories consume the most money when categories are available."),
            ("AI interpretation", "Financial Intelligence highlights evidence-backed problems, warnings, and opportunities."),
        ])
    ai = a["financial"].get("ai", {})
    st.subheader("Financial Intelligence")
    st.markdown(f'<div class="fos-card fos-card-gold"><b>{ai.get("summary", "")}</b></div>', unsafe_allow_html=True)
    for item in ai.get("problems", []):
        st.markdown(f'<div class="fos-card"><span class="fos-pill">{item.get("severity", "ISSUE")}</span><h4>{item.get("title", "Problem")}</h4><p>{item.get("evidence", "")}</p><b>Recommended:</b> {item.get("action", "")}</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Inventory
# -----------------------------------------------------------------------------
def render_inventory():
    if not st.session_state.analysis_ready:
        no_data_page("Inventory", "See where stock risk and working capital may be hiding.", [
            ("Stock levels", "Total units and low-stock items when inventory quantities are available."),
            ("Fast / slow stock", "Products with stronger or weaker unit movement based on the available inventory data."),
            ("Inventory value", "Money tied up in stock only when a defensible cost field exists."),
            ("Operational risk", "Warnings and actions based on the actual inventory records."),
        ])
        return
    a = st.session_state.analysis
    facts = a["operations"]["facts"].get("inventory", {})
    df = st.session_state.datasets.get("inventory")
    st.title("Inventory")
    st.caption("See where stock risk and working capital may be hiding.")
    left, right = st.columns([1.45, .85])
    with left:
        if df is None:
            st.markdown('<div class="fos-empty"><h3>No inventory file was uploaded</h3><p class="fos-muted">Inventory-specific metrics are unavailable, but the rest of FounderOS continues to work.</p></div>', unsafe_allow_html=True)
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total units", f"{facts.get('total_units', 0):,.0f}")
            c2.metric("Low-stock items", f"{facts.get('low_stock_items', 0):,}")
            c3.metric("Inventory cost value", money_or_dash(facts.get("inventory_cost_value")))
            product, qty = find_column(df, "product"), find_column(df, "quantity")
            if product and qty:
                x = df.copy(); x[qty] = pd.to_numeric(x[qty], errors="coerce").fillna(0)
                grouped = x.groupby(product)[qty].sum().sort_values().head(15).reset_index()
                fig = px.bar(grouped, x=qty, y=product, orientation="h", title="Products with the lowest stock")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#F4F4F6"))
                st.plotly_chart(fig, use_container_width=True)
            if facts.get("inventory_cost_value") is None:
                st.info("Inventory value is not calculated because a reliable purchase/unit-cost field was not found.")
    with right:
        st.subheader("What you get here")
        purpose_panel([
            ("Stock visibility", "Understand total units and low-stock exposure."),
            ("Product movement", "See fast/slow patterns when product and quantity fields support them."),
            ("Capital at risk", "Estimate stock value only when cost data is actually present."),
            ("Actionable warnings", "Operations Intelligence turns supported signals into operational recommendations."),
        ])
    ai = a["operations"].get("ai", {})
    st.subheader("Operational Intelligence")
    st.markdown(f'<div class="fos-card fos-card-gold"><b>{ai.get("summary", "")}</b></div>', unsafe_allow_html=True)
    for item in ai.get("problems", []):
        st.markdown(f'<div class="fos-card"><span class="fos-pill">{item.get("severity", "ISSUE")}</span><h4>{item.get("title", "Problem")}</h4><p>{item.get("evidence", "")}</p><b>Recommended:</b> {item.get("action", "")}</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Customers & Sales
# -----------------------------------------------------------------------------
def render_customers():
    if not st.session_state.analysis_ready:
        no_data_page("Customers & Sales", "Find customer and sales opportunities from the records you actually provide.", [
            ("Customer profile", "Count customers and identify high-value customers when customer identifiers and amounts exist."),
            ("Repeat behavior", "Measure repeat customers when transaction-level customer records are available."),
            ("Sales opportunities", "Surface supported patterns rather than inventing customer behavior."),
            ("Graceful fallback", "If customer information is absent, the page stays useful and explains what is missing."),
        ])
        return
    a = st.session_state.analysis
    facts = a["operations"]["facts"].get("customers", {})
    sales = st.session_state.datasets.get("sales")
    customers = st.session_state.datasets.get("customers")
    df = customers if customers is not None else sales
    st.title("Customers & Sales")
    st.caption("Find customer behavior and sales opportunities supported by your records.")
    left, right = st.columns([1.45, .85])
    with left:
        if df is None:
            st.markdown('<div class="fos-empty"><h3>No customer or sales records were uploaded</h3><p class="fos-muted">Upload sales/customer records on Dashboard to unlock this view.</p></div>', unsafe_allow_html=True)
        else:
            c1, c2 = st.columns(2)
            c1.metric("Customers identified", facts.get("customer_count", "—"))
            c2.metric("Repeat customers", facts.get("repeat_customers", "—"))
            if facts:
                top = facts.get("top_customers", {})
                if top:
                    table = pd.DataFrame.from_dict(top, orient="index")
                    table.index.name = "Customer"
                    st.subheader("Highest-value customers")
                    st.dataframe(table.reset_index(), use_container_width=True, hide_index=True)
            else:
                st.info("Customer-level analysis isn't available because a customer identifier and purchase amount were not found.")
    with right:
        st.subheader("What you get here")
        purpose_panel([
            ("Customer value", "See which customers contribute the most revenue when the data supports it."),
            ("Repeat behavior", "Identify repeat buyers from transaction counts."),
            ("Sales context", "Use actual sales records to understand purchasing patterns."),
            ("Data-aware limits", "FounderOS never invents customers or behavior that isn't present in the records."),
        ])
    ai = a["operations"].get("ai", {})
    st.subheader("Sales Intelligence")
    st.markdown(f'<div class="fos-card fos-card-gold"><b>{ai.get("summary", "")}</b></div>', unsafe_allow_html=True)
    for item in ai.get("opportunities", []):
        st.markdown(f'<div class="fos-card"><span class="fos-pill">OPPORTUNITY</span><h4>{item.get("title", "Opportunity")}</h4><p>{item.get("evidence", "")}</p><b>Recommended:</b> {item.get("action", "")}</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# AI Advisor
# -----------------------------------------------------------------------------
def render_advisor():
    if not st.session_state.analysis_ready:
        no_data_page("AI Advisor", "Ask questions about your actual business records and FounderOS analysis.", [
            ("Ask about performance", "Examples: Why did profit change? What is the biggest issue?"),
            ("Ask about priorities", "Ask where to focus next based on the evidence in your uploaded data."),
            ("Ask for actions", "Get practical next steps grounded in the calculated business context."),
            ("No generic guessing", "The advisor is instructed to say when the uploaded records do not support an answer."),
        ])
        return
    from sources import call_gemini
    st.title("AI Advisor")
    st.caption("Ask questions about your actual FounderOS workspace.")
    left, right = st.columns([1.45, .85])
    with left:
        suggestions = [
            "What is my biggest business problem right now?",
            "Where should I focus this month?",
            "What could improve my profit based on the data?",
            "What should I investigate first?",
        ]
        for q in suggestions:
            if st.button(q, key=f"advisor_{q}", use_container_width=True):
                st.session_state.pending_question = q
        for msg in st.session_state.advisor_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        question = st.chat_input("Ask FounderOS about your business…")
        question = question or st.session_state.pop("pending_question", None)
        if question:
            st.session_state.advisor_messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            context = {
                "business_goal": st.session_state.business_goal,
                "analysis": st.session_state.analysis,
                "datasets": {
                    k: {"rows": len(v), "columns": list(v.columns), "sample": v.head(5).to_dict("records")}
                    for k, v in st.session_state.datasets.items()
                },
            }
            import json
            prompt = f"""
You are FounderOS AI Business Advisor.
Answer using ONLY the business context below. Calculated facts are authoritative.
Never invent figures, customers, products, trends, causes, or events.
If the records do not support an answer, say so.
Separate observations from recommendations and keep the answer practical.

Question:
{question}

Business context:
{json.dumps(context, default=str)}
"""
            with st.chat_message("assistant"):
                with st.spinner("FounderOS is thinking…"):
                    try:
                        answer = call_gemini(prompt)
                    except Exception:
                        answer = "I couldn't reach the AI Advisor right now. Your saved analysis is still available in the other sections."
                st.markdown(answer)
            st.session_state.advisor_messages.append({"role": "assistant", "content": answer})
    with right:
        st.subheader("What you get here")
        purpose_panel([
            ("Evidence first", "Questions are answered from your uploaded data and calculated FounderOS facts."),
            ("Business context", "The advisor sees the goal, analysis, dataset structure, and small data samples."),
            ("Actionable answers", "Recommendations are written for a business owner, not as generic AI filler."),
            ("Clear uncertainty", "When the records cannot answer something, the advisor says so."),
        ])


# -----------------------------------------------------------------------------
# Render selected section
# -----------------------------------------------------------------------------
if st.session_state.menu_page == "Dashboard":
    render_dashboard()
elif st.session_state.menu_page == "Finance":
    render_finance()
elif st.session_state.menu_page == "Inventory":
    render_inventory()
elif st.session_state.menu_page == "Customers & Sales":
    render_customers()
elif st.session_state.menu_page == "AI Advisor":
    render_advisor()
