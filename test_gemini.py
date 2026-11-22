import streamlit as st
from assistant.gemini_chat import ask_gemini

# Connecting to Gemini
print("Connecting to Gemini...")

try:
    # Ask Gemini a question
    answer = ask_gemini(
        "What is American Sign Language? Explain in two sentences."
    )

    # Print the response
    print("\nGemini response:")
    print(answer)

except Exception as exc:
    # Show the error if something goes wrong
    print(f"\nError: {exc}")
