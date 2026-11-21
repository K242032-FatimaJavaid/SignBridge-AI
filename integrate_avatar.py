
from pathlib import Path
import os
import re
import shutil
import socket
import subprocess
import time

# =====================================================
# SIGNBRIDGE AI - 3D AVATAR INTEGRATION
# Uses the existing avatar-engine folder, NOT a ZIP.
# =====================================================

ROOT = Path(__file__).resolve().parent

APP = ROOT / "app.py"
ENGINE = ROOT / "avatar-engine"
MAIN_JS = ENGINE / "src" / "main.js"
AVATAR_MODEL = ENGINE / "public" / "models" / "avatar.glb"

COMPONENT_FILE = ROOT / "speech_to_asl_avatar.py"
LAUNCHER = ROOT / "run_signbridge.bat"

APP_BACKUP = ROOT / "app_before_avatar_integration.py"
JS_BACKUP = ENGINE / "src" / "main_before_integration.js"


# =====================================================
# STEP 1 - CHECK REQUIRED FILES
# =====================================================

print("\nChecking SignBridge AI project...")

required = {
    "Main Streamlit application": APP,
    "Avatar JavaScript engine": MAIN_JS,
    "3D avatar model": AVATAR_MODEL,
    "Avatar package.json": ENGINE / "package.json",
}

missing = []

for description, path in required.items():
    if path.is_file():
        print(f"[OK] {description}")
    else:
        print(f"[MISSING] {description}: {path}")
        missing.append(description)

if missing:
    raise SystemExit(
        "\nIntegration stopped. Copy the extracted "
        "'avatar-engine' folder into your main "
        "SignBridge-AI project first.\n"
        "Do not rename or extract avatar-engine.zip."
    )


# =====================================================
# STEP 2 - PREPARE AVATAR MESSAGE HANDLER
# =====================================================

print("\nPreparing avatar communication...")

js_original = MAIN_JS.read_text(encoding="utf-8")
js_updated = js_original

# This event receives text from the Streamlit iframe.
# The avatar may still be loading when text arrives.
# In that case, queue the text until the avatar is ready.

if "__signbridgePendingText" not in js_updated:

    handler_position = js_updated.find(
        'window.addEventListener("message"'
    )

    old_compile = (
        'document.querySelector("#compile")?.click();'
    )

    new_compile = """if (avatar && mixer) {
    document.querySelector("#compile")?.click();
  } else {
    window.__signbridgePendingText = data.text;
  }"""

    if (
        handler_position >= 0
        and "SIGNBRIDGE_TEXT"
        in js_updated[handler_position:]
    ):
        before = js_updated[:handler_position]
        handler = js_updated[handler_position:]

        if old_compile not in handler:
            raise SystemExit(
                "Cannot update the existing avatar "
                "message handler safely."
            )

        handler = handler.replace(
            old_compile, new_compile, 1
        )

        js_updated = before + handler

    else:
        # Add the message listener if it is missing.
        js_updated += """

// SignBridge AI - Streamlit message integration
window.addEventListener("message", (event) => {
  const data = event.data;

  if (
    !data ||
    data.type !== "SIGNBRIDGE_TEXT" ||
    typeof data.text !== "string"
  ) {
    return;
  }

  const input = document.querySelector("#words");
  if (!input) return;

  input.value = data.text;

  if (avatar && mixer) {
    document.querySelector("#compile")?.click();
  } else {
    window.__signbridgePendingText = data.text;
  }
});
"""

    # Play any phrase received while the avatar loaded.
    ready_marker = (
        'status.textContent = '
        '`Avatar ready. ${bones.length} bones found.`;'
    )

    pending_handler = """
    if (window.__signbridgePendingText) {
      const pending = window.__signbridgePendingText;
      window.__signbridgePendingText = null;

      const input = document.querySelector("#words");

      if (input) {
        input.value = pending;
        document.querySelector("#compile")?.click();
      }
    }
"""

    if ready_marker not in js_updated:
        raise SystemExit(
            "Avatar-ready code was not found in main.js. "
            "No files were changed."
        )

    js_updated = js_updated.replace(
        ready_marker,
        ready_marker + "\n" + pending_handler,
        1
    )

print("[OK] Avatar message handler prepared.")


# =====================================================
# STEP 3 - CREATE STREAMLIT AVATAR COMPONENT
# =====================================================

print("\nPreparing Speech-to-ASL interface...")

avatar_component = r'''
from pathlib import Path
import os
import shutil
import socket
import subprocess
import time

import streamlit as st
import streamlit.components.v1 as components


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
'''

# Check generated Python before writing anything.
compile(
    avatar_component,
    str(COMPONENT_FILE),
    "exec"
)

print("[OK] Avatar Streamlit component prepared.")


# =====================================================
# STEP 4 - UPDATE ONLY SPEECH -> ASL PAGE
# =====================================================

print("\nPreparing main application changes...")

app_original = APP.read_text(encoding="utf-8")

speech_page = re.search(
    r"(?m)^elif ['\"]Speech → ASL['\"] in page:[ \t]*$",
    app_original
)

if speech_page is None:
    raise SystemExit(
        "Could not locate the Speech -> ASL page in app.py. "
        "The main application was not changed."
    )

# Find the next top-level else, which is the Gemini page.
remaining = app_original[speech_page.end():]

gemini_page = re.search(
    r"(?m)^else:[ \t]*$",
    remaining
)

if gemini_page is None:
    raise SystemExit(
        "Could not locate the Gemini Assistant section. "
        "The main application was not changed."
    )

gemini_position = (
    speech_page.end() + gemini_page.start()
)

new_speech_page = """elif 'Speech → ASL' in page:

    st.markdown(
        '<div class="eyebrow">REVERSE TRANSLATION STUDIO</div>',
        unsafe_allow_html=True
    )

    st.title('Speech to ASL')

    st.caption(
        'Convert typed or spoken English into '
        '3D sign language animations.'
    )

    from speech_to_asl_avatar import show_avatar_studio

    show_avatar_studio()

"""

app_updated = (
    app_original[:speech_page.start()]
    + new_speech_page
    + app_original[gemini_position:]
)

# Check final main Python syntax before modifying it.
compile(
    app_updated,
    str(APP),
    "exec"
)

print("[OK] Main application prepared.")
print("[OK] Existing ASL recognition section retained.")
print("[OK] Gemini Assistant section retained.")


# =====================================================
# STEP 5 - CREATE WINDOWS LAUNCHER
# =====================================================

launcher_code = r"""@echo off
setlocal

title SignBridge AI

cd /d "%~dp0"

echo ==========================================
echo          SIGNBRIDGE AI
echo ==========================================
echo.

where npm >nul 2>&1

if errorlevel 1 (
    echo ERROR: Node.js/npm is not installed.
    echo Install Node.js and reopen PowerShell.
    pause
    exit /b 1
)

if not exist "avatar-engine\package.json" (
    echo ERROR: avatar-engine folder is missing.
    pause
    exit /b 1
)

echo Checking avatar dependencies...

pushd avatar-engine

if not exist "node_modules" (
    echo Installing avatar dependencies...
    call npm ci

    if errorlevel 1 (
        echo ERROR: npm installation failed.
        popd
        pause
        exit /b 1
    )
)

echo Building avatar signing engine...

call npm run build

if errorlevel 1 (
    echo ERROR: avatar build failed.
    popd
    pause
    exit /b 1
)

popd

echo.
echo Starting SignBridge AI dashboard...
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run app.py
) else (
    python -m streamlit run app.py
)

pause
"""

print("[OK] Windows launcher prepared.")


# =====================================================
# STEP 6 - BACK UP AND SAVE CHANGES
# =====================================================

print("\nSaving integration files...")

if not APP_BACKUP.exists():
    shutil.copy2(APP, APP_BACKUP)
    print("[OK] Main app backup created.")
else:
    print("[OK] Existing main app backup preserved.")

if not JS_BACKUP.exists():
    shutil.copy2(MAIN_JS, JS_BACKUP)
    print("[OK] Avatar JavaScript backup created.")
else:
    print("[OK] Existing JavaScript backup preserved.")

MAIN_JS.write_text(
    js_updated,
    encoding="utf-8"
)

COMPONENT_FILE.write_text(
    avatar_component,
    encoding="utf-8"
)

APP.write_text(
    app_updated,
    encoding="utf-8"
)

LAUNCHER.write_text(
    launcher_code,
    encoding="utf-8"
)


# =====================================================
# STEP 7 - FINISH
# =====================================================

print("\n==========================================")
print("SIGNBRIDGE AI INTEGRATION FILES CREATED")
print("==========================================")

print("\nCreated / updated:")
print("  app.py")
print("  speech_to_asl_avatar.py")
print("  avatar-engine/src/main.js")
print("  run_signbridge.bat")

print("\nPreserved:")
print("  recognition/")
print("  assistant/")
print("  models/")
print("  Existing webcam recognition code")
print("  Existing Gemini Assistant code")

print("\nBackups:")
print("  app_before_avatar_integration.py")
print("  avatar-engine/src/main_before_integration.js")

print("\nNext command:")
print("  .\\run_signbridge.bat")
print("\n")
