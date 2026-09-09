import os
import streamlit as st
from supabase import create_client, Client

def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
    if not url or not key:
        raise RuntimeError("Supabase configuration is missing.")
    return create_client(url, key)

def is_authenticated() -> bool:
    return bool(st.session_state.get("user"))

def signup(email: str, password: str):
    return get_supabase().auth.sign_up({"email": email, "password": password})

def login(email: str, password: str):
    return get_supabase().auth.sign_in_with_password({"email": email, "password": password})

def logout():
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    for key in ["user", "session", "analysis_ready", "analysis", "datasets", "business_goal"]:
        st.session_state.pop(key, None)

def login_view():
    st.markdown(
        '<div class="auth-shell"><div class="brand-mark">F</div>'
        "<h1>FounderOS</h1>"
        "<p>Turn your business records into clear decisions.</p></div>",
        unsafe_allow_html=True,
    )
    tab1, tab2 = st.tabs(["Log In", "Create Account"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
        if submitted:
            try:
                result = login(email.strip(), password)
                st.session_state.user = result.user
                st.session_state.session = result.session
                st.success("You're logged in.")
                st.rerun()
            except Exception:
                st.error(
                    "⚠️ We couldn't log you in. Please check your email and password, "
                    "or create an account first."
                )

    with tab2:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
        if submitted:
            if password != confirm:
                st.error("⚠️ Your passwords don't match. Please enter them again.")
            elif len(password) < 6:
                st.error("⚠️ Please use a password with at least 6 characters.")
            else:
                try:
                    result = signup(email.strip(), password)
                    if result.session:
                        st.session_state.user = result.user
                        st.session_state.session = result.session
                        st.success("Account created.")
                        st.rerun()
                    else:
                        st.success(
                            "Your account was created. Check your email if confirmation is required, "
                            "then log in."
                        )
                except Exception:
                    st.error(
                        "⚠️ We couldn't create the account. The email may already be registered "
                        "or the Supabase settings may need attention."
                    )
