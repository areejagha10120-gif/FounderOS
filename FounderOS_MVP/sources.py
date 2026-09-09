import json
import os
from typing import Any

from google import genai

def _secret(name: str):
    try:
        import streamlit as st
        return st.secrets.get(name, os.getenv(name))
    except Exception:
        return os.getenv(name)

def get_gemini_client():
    key = _secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Gemini configuration is missing.")
    return genai.Client(api_key=key)

def call_gemini(prompt: str, *, temperature: float = 0.2) -> str:
    client = get_gemini_client()
    model = _secret("GEMINI_MODEL") or "gemini-3.6-flash"
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": temperature},
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response.")
    return text

def call_gemini_json(prompt: str) -> Any:
    client = get_gemini_client()
    model = _secret("GEMINI_MODEL") or "gemini-3.6-flash"
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response.")
    return json.loads(text)
