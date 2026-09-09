import json
import streamlit as st
from sources import call_gemini
from utils.helpers import init_state, inject_css, require_analysis

st.set_page_config(page_title="FounderOS — AI Advisor", page_icon="🤖", layout="wide")
inject_css(); init_state(); require_analysis()

st.title("🤖 AI Business Advisor")
st.caption("Ask questions about your actual business records and FounderOS analysis.")

suggestions = [
    "Why did my profit decrease?",
    "What is my biggest problem?",
    "Where should I focus this month?",
    "What can I do to improve my business?",
]

for q in suggestions:
    if st.button(q):
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
            k: {
                "rows": len(v),
                "columns": list(v.columns),
                "sample": v.head(5).to_dict("records"),
            }
            for k,v in st.session_state.datasets.items()
        },
    }
    prompt = f"""
You are FounderOS AI Business Advisor.
Answer the user's question using ONLY the business context below.
Calculated facts are more authoritative than AI-generated interpretations.
Never invent figures, customers, products, trends, or causes.
If the records do not support an answer, say so clearly.
Separate factual observations from recommendations.
Keep the answer concise and useful for an inexperienced business owner.

Question:
{question}

Business context:
{json.dumps(context, default=str)}
"""
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                answer = call_gemini(prompt)
            except Exception:
                answer = (
                    "I couldn't reach the AI Advisor right now. "
                    "Your saved business analysis is still available on the other pages."
                )
        st.markdown(answer)
    st.session_state.advisor_messages.append({"role": "assistant", "content": answer})
