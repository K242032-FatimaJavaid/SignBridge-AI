
"""Rule-based assistant for SignBridge AI."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize(text):
    """Normalize text for simple intent matching."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def reply(message):
    """Generate a response using supported conversational intents."""
    text = normalize(message)
    words = set(text.split())

    if not text:
        return "Please enter a question."

    if "name" in words and (
        "your" in words or "you" in words
    ):
        return "My name is SignBridge AI."

    if "how are you" in text:
        return "I am doing well and ready to help!"

    if "thank" in words or "thanks" in words:
        return "You are welcome!"

    if "help" in words or "assist" in words:
        return (
            "I can recognize five supported hand signs, "
            "speak them aloud, and show ASL demonstration "
            "videos for supported English words."
        )

    if "hello" in words or "hi" in words or "hey" in words:
        return "Hello! How can I help you?"

    if "what can you do" in text or "features" in words:
        return (
            "I support hand sign recognition, speech output, "
            "speech recognition, and a small ASL video library."
        )

    if "asl" in words or "sign" in words:
        return (
            "ASL means American Sign Language. "
            "This prototype supports five signs: "
            "hello, yes, no, help, and thank you."
        )

    return (
        "I am a limited rule-based assistant. "
        "You can ask about my name, supported signs, "
        "features, or how I can help."
    )


def sign_video_for(text):
    """Find an exact matching ASL demonstration video."""
    slug = normalize(text).replace(" ", "_").upper()
    path = ROOT / "assets" / "asl_videos" / f"{slug}.mp4"
    return path if path.is_file() else None
