
"""Gemini-powered chatbot for SignBridge AI."""

import streamlit as st
from google import genai

MODEL_NAME = "gemini-3.5-flash-lite"


def ask_gemini(question):
    """Send a question to Gemini and return its response."""

    api_key = st.secrets["GEMINI_API_KEY"]

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=question,
        config={
            "system_instruction": (
                "You are SignBridge AI, a friendly and helpful "
                "communication assistant for a university project. "
                "Explain concepts clearly and concisely. "
                "You support demonstrations of five ASL signs: "
                "HELLO, YES, NO, HELP, and THANK YOU. "
                "Do not claim to translate complete sentences "
                "into American Sign Language."
            ),
            "max_output_tokens": 300,
        },
    )

    return response.text or "No response was generated."
