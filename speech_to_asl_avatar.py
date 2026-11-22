

from pathlib import Path
import os
import shutil
import socket
import subprocess
import time

import streamlit as st
import streamlit.components.v1 as components

# Set the paths for the project and avatar engine
ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "avatar-engine"

AVATAR_HOST = "127.0.0.1"
AVATAR_PORT = 5173


def avatar_server_running():
    """Check whether the local avatar server is running."""

    try:
        with socket.create_connection(
            (AVATAR_HOST, AVATAR_PORT),
            timeout=0.5
        ):
            return True

    except OSError:
        return False


def start_avatar_server():
    """Launch the existing Vite avatar engine."""

    if avatar_server_running():
        return True

    npm = shutil.which("npm.cmd") or shutil.which("npm")

    if not npm:
        raise RuntimeError(
            "Node.js/npm is not installed or is not on PATH."
        )

    if not (ENGINE / "node_modules").is_dir():
        raise RuntimeError(
            "Avatar dependencies are missing. "
            "Run run_signbridge.bat first."
        )

    command = [
        npm,
        "run",
        "dev",
        "--",
        "--host",
        AVATAR_HOST,
        "--port",
        str(AVATAR_PORT),
        "--strictPort",
    ]

    options = {
        "cwd": str(ENGINE),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW

    subprocess.Popen(command, **options)

    for _ in range(40):
        if avatar_server_running():
            return True
        time.sleep(0.25)

    raise RuntimeError(
        "3D avatar server did not start on port 5173."
    )


def show_avatar_studio():
    """Display speech input and the 3D ASL avatar."""

    if not (ENGINE / "src" / "main.js").is_file():
        st.error("The avatar-engine folder is missing.")
        return

    try:
        start_avatar_server()
    except Exception as error:
        st.error(f"Avatar startup error: {error}")
        return

    components.html(
        r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Inter, Arial, sans-serif;
    background: transparent;
    color: #eaf4ff;
}

.panel {
    background: rgba(13, 27, 46, 0.8);
    border: 1px solid rgba(173, 214, 250, 0.2);
    border-radius: 18px;
    padding: 20px;
}

.heading {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 8px;
}

.description {
    color: #a5b9d0;
    font-size: 14px;
    margin-bottom: 18px;
}

.controls {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}

input {
    flex: 1;
    min-width: 230px;
    padding: 13px;
    font-size: 15px;
    color: #ffffff;
    background: #101d31;
    border: 1px solid #456078;
    border-radius: 11px;
}

button {
    padding: 12px 17px;
    border: 0;
    border-radius: 11px;
    color: #071525;
    font-weight: 700;
    cursor: pointer;
    background: linear-gradient(
        105deg,
        #31c5bb,
        #388dc5
    );
}

button:hover {
    filter: brightness(1.12);
}

#status {
    color: #b8cadd;
    font-size: 14px;
    margin: 15px 0;
    min-height: 20px;
}

iframe {
    display: block;
    width: 100%;
    height: 820px;
    border: 1px solid rgba(173, 214, 250, 0.2);
    border-radius: 15px;
    background: #0b1220;
}

.note {
    font-size: 12px;
    color: #a5b9d0;
    margin-top: 14px;
    line-height: 1.7;
}
</style>
</head>

<body>

<div class="panel">

    <div class="heading">
        3D Sign Language Studio
    </div>

    <div class="description">
        Enter English text or speak into your microphone.
        The 3D avatar will animate supported signs.
    </div>

    <div class="controls">

        <input
            id="phrase"
            type="text"
            placeholder="Example: Hello, I need help"
        >

        <button id="send" type="button">
            Show ASL
        </button>

        <button id="mic" type="button">
            🎙 Speak
        </button>

    </div>

    <div id="status" role="status">
        Loading avatar...
    </div>

    <iframe
        id="avatar"
        src="http://127.0.0.1:5173/"
        title="SignBridge 3D ASL Avatar"
    ></iframe>

    <div class="note">
        The avatar displays the signs and fingerspelling
        supported by the current prototype.
        It is not a complete fluent ASL translator.
    </div>

</div>


<script>

const phrase = document.getElementById("phrase");
const status = document.getElementById("status");
const frame = document.getElementById("avatar");

let frameLoaded = false;
let pendingPhrase = "";


function sendPhrase(value) {

    const text = String(
        value || phrase.value || ""
    ).trim();

    if (!text) {
        status.textContent =
            "Please enter or speak a phrase first.";
        return;
    }

    phrase.value = text;

    if (!frameLoaded) {
        pendingPhrase = text;
        status.textContent =
            "Avatar is loading. Phrase queued.";
        return;
    }

    frame.contentWindow.postMessage(
        {
            type: "SIGNBRIDGE_TEXT",
            text: text
        },
        "http://127.0.0.1:5173"
    );

    status.textContent =
        "Phrase sent to avatar: " + text;
}


document.getElementById("send")
    .addEventListener("click", function () {
        sendPhrase(phrase.value);
    });


phrase.addEventListener("keydown", function (event) {

    if (event.key === "Enter") {
        sendPhrase(phrase.value);
    }

});


frame.addEventListener("load", function () {

    frameLoaded = true;

    status.textContent =
        "Avatar page loaded. Enter a phrase.";

    if (pendingPhrase) {

        const value = pendingPhrase;
        pendingPhrase = "";

        sendPhrase(value);
    }

});


document.getElementById("mic")
    .addEventListener("click", function () {

        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        if (!SpeechRecognition) {

            status.textContent =
                "Browser speech recognition is unavailable. "
                + "Try Google Chrome or type your phrase.";

            return;
        }

        const recognition = new SpeechRecognition();

        recognition.lang = "en-US";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = function () {
            status.textContent =
                "Listening... Speak now.";
        };

        recognition.onresult = function (event) {

            const text =
                event.results[0][0].transcript;

            phrase.value = text;

            status.textContent =
                "Recognized speech: " + text;

            sendPhrase(text);
        };

        recognition.onerror = function (event) {

            status.textContent =
                "Speech recognition error: "
                + event.error;
        };

        try {
            recognition.start();
        } catch (error) {

            status.textContent =
                "Microphone error: " + error.message;
        }

    });

</script>

</body>
</html>
""",
        height=1060,
        scrolling=True
    )

    st.caption(
        "Speech input uses the browser microphone. "
        "Depending on your browser, transcription may "
        "use an external speech recognition service."
    )
