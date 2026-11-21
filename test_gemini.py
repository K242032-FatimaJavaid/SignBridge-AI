
import streamlit as st
from assistant.gemini_chat import ask_gemini

print("Connecting to Gemini...")

try:
    answer = ask_gemini(
        "What is American Sign Language? Explain in two sentences."
    )
    print("\nGemini response:")
    print(answer)

except Exception as exc:
    print(f"\nError: {exc}")
