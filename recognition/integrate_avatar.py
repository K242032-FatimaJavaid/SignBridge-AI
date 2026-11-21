
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
ZIP = ROOT / "avatar-engine.zip"
ENGINE = ROOT / "avatar-engine"

if not APP.is_file():
    raise SystemExit("Missing main app.py in this folder.")
if not ZIP.is_file():
    raise SystemExit("Place avatar-engine.zip beside this script.")

# Extract only the actual avatar engine.
with zipfile.ZipFile(ZIP) as archive:
    names = archive.namelist()
    prefixes = [
        name[:-len("package.json")]
        for name in names
        if name.endswith("package.json")
        and "node_modules/" not in name
    ]
    prefix = next(
        (p for p in prefixes if p + "src/main.js" in names),
        None
    )
    if prefix is None:
        raise SystemExit("Cannot locate avatar-engine/src/main.js.")

    for name in names:
        if not name.startswith(prefix) or name.endswith("/"):
            continue
        relative = name[len(prefix):]
        parts = Path(relative).parts
        if not parts or ".." in parts:
            continue
        if any(p in {"node_modules", ".git", "__pycache__"} for p in parts):
            continue
        if relative.endswith(".zip"):
            continue

        destination = ENGINE / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(name) as source, destination.open("wb") as out:
            shutil.copyfileobj(source, out)

MAIN_JS = ENGINE / "src" / "main.js"
MODEL = ENGINE / "public" / "models" / "avatar.glb"
if not MAIN_JS.is_file() or not MODEL.is_file():
    raise SystemExit("Avatar engine source or 3D model is missing.")

# Ensure Streamlit messages reach the avatar, including during loading.
js = MAIN_JS.read_text(encoding="utf-8")
handler = '''
window.addEventListener("message", (event) => {
  const data = event.data;
  if (!data || data.type !== "SIGNBRIDGE_TEXT"
      || typeof data.text !== "string") return;
  const input = document.querySelector("#words");
  if (!input) return;
  input.value = data.text;
  if (!avatar || !mixer) {
    window.__signbridgePendingText = data.text;
    return;
  }
  document.querySelector("#compile")?.click();
});
'''
marker = 'window.addEventListener("message", (event) => {'
start = js.find(marker)
if start >= 0:
    end = js.find("\n});", start)
    if end < 0:
        raise SystemExit("Unexpected message handler in main.js.")
    js = js[:start] + handler + js[end + 4:]
else:
    js += "\n" + handler

ready = 'status.textContent = `Avatar ready. ${bones.length} bones found.`;'
pending = '''
if (window.__signbridgePendingText) {
  const input = document.querySelector("#words");
  if (input) input.value = window.__signbridgePendingText;
  window.__signbridgePendingText = null;
  document.querySelector("#compile")?.click();
}
'''
if ready in js:
    js = js.replace(ready, ready + "\n" + pending, 1)
else:
    raise SystemExit("Could not locate the avatar-ready handler.")

MAIN_JS.write_text(js, encoding="utf-8")

# Dedicated Streamlit component: no changes to recognition or Gemini.
helper = r'''
from pathlib import Path
import os
import shutil
import socket
import subprocess
import time

import streamlit as st
import streamlit.components.v1 as components

ENGINE = Path(__file__).resolve().parent / "avatar-engine"

def server_running():
    try:
        with socket.create_connection(("127.0.0.1", 5173), timeout=0.4):
            return True
    except OSError:
        return False

def show_avatar_studio():
    if not (ENGINE / "package.json").is_file():
        st.error("3D avatar engine files are missing.")
        return

    if not server_running():
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm:
            st.error("Install Node.js, then use run_signbridge.bat.")
            return
        if not (ENGINE / "node_modules").is_dir():
            st.error("Run run_signbridge.bat to install avatar dependencies.")
            return
        try:
            options = {
                "cwd": str(ENGINE),
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if os.name == "nt":
                options["creationflags"] = subprocess.CREATE_NO_WINDOW
            subprocess.Popen(
                [npm, "run", "dev", "--",
                 "--host", "127.0.0.1",
                 "--port", "5173", "--strictPort"],
                **options
            )
            for _ in range(40):
                if server_running():
                    break
                time.sleep(0.25)
        except OSError as error:
            st.error(f"Avatar server could not start: {error}")
            return

    if not server_running():
        st.error("Avatar server is unavailable on port 5173.")
        return

    components.html(r"""
    <style>
      * { box-sizing:border-box; }
      body { margin:0; color:#eaf4ff;
        font-family:Inter,Arial,sans-serif; background:transparent; }
      .panel { background:#101d31; border:1px solid #30485e;
        border-radius:17px; padding:18px; }
      .controls { display:flex; flex-wrap:wrap; gap:10px; }
      input { flex:1; min-width:230px; padding:13px;
        border-radius:10px; color:white; background:#0b1426;
        border:1px solid #465c75; font-size:15px; }
      button { padding:12px 17px; border:0; border-radius:10px;
        background:#42cfc0; color:#071525; font-weight:700;
        cursor:pointer; }
      #status { margin:13px 0; color:#bed0e4; font-size:14px; }
      iframe { width:100%; height:820px; border:1px solid #30485e;
        border-radius:13px; background:#0b1220; }
      small { display:block; margin-top:10px; color:#9fb3c8; }
    </style>

    <div class="panel">
      <div class="controls">
        <input id="phrase" placeholder="Hello, I need help">
        <button id="send">Show ASL</button>
        <button id="mic">🎙 Speak</button>
      </div>
      <div id="status" role="status">
        Enter a phrase or use your microphone.
      </div>
      <iframe id="avatar"
        title="SignBridge 3D ASL Avatar"
        src="http://127.0.0.1:5173/"
        allow="microphone"></iframe>
      <small>Supported words use avatar sign animations.
      Other words may be fingerspelled. This is a prototype,
      not a complete ASL translation system.</small>
    </div>

    <script>
      const phrase = document.getElementById("phrase");
      const status = document.getElementById("status");
      const frame = document.getElementById("avatar");

      function sendPhrase(value) {
        const text = String(value || phrase.value).trim();
        if (!text) {
          status.textContent = "Enter or speak a phrase first.";
          return;
        }
        phrase.value = text;
        frame.contentWindow.postMessage(
          {type:"SIGNBRIDGE_TEXT", text:text},
          "http://127.0.0.1:5173"
        );
        status.textContent = "Sent to the avatar: " + text;
      }

      document.getElementById("send").onclick =
        () => sendPhrase(phrase.value);

      phrase.addEventListener("keydown", event => {
        if (event.key === "Enter") sendPhrase(phrase.value);
      });

      document.getElementById("mic").onclick = () => {
        const Recognition =
          window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!Recognition) {
          status.textContent =
            "Browser speech recognition is unavailable. Type instead.";
          return;
        }
        try {
          const recognition = new Recognition();
          recognition.lang = "en-US";
          recognition.interimResults = false;
          recognition.onresult = event =>
            sendPhrase(event.results[0][0].transcript);
          recognition.onerror = event => {
            status.textContent = "Speech error: " + event.error;
          };
          recognition.start();
          status.textContent = "Listening...";
        } catch (error) {
          status.textContent = String(error);
        }
      };
      frame.addEventListener("load", () => {
        status.textContent = "Avatar page loaded. Enter a phrase.";
      });
    </script>
    """, height=1050, scrolling=True)

    st.caption(
        "Browser speech recognition may use an external service. "
        "The 3D avatar displays the prototype's available signs "
        "and fingerspelling."
    )
'''
compile(helper, "speech_to_asl_avatar.py", "exec")

# Replace only the Speech-to-ASL route.
original = APP.read_text(encoding="utf-8")
start = original.find("elif 'Speech → ASL' in page:")
if start < 0:
    raise SystemExit("Could not find the existing Speech → ASL page.")
end = original.find("\nelse:\n", start)
if end < 0:
    raise SystemExit("Could not locate the Gemini page boundary.")

replacement = """elif 'Speech → ASL' in page:
    st.markdown(
        '<div class="eyebrow">REVERSE TRANSLATION STUDIO</div>',
        unsafe_allow_html=True
    )
    st.title('Speech to ASL')
    st.caption('Speak or type English and watch the 3D signing avatar.')
    from speech_to_asl_avatar import show_avatar_studio
    show_avatar_studio()
"""
updated = original[:start] + replacement + original[end:]
updated = updated.replace(
    "Type or record English and view matching sign demonstration videos.",
    "Type or speak English and watch the 3D avatar sign."
)
compile(updated, str(APP), "exec")

shutil.copy2(APP, ROOT / "app_before_avatar_integration.py")
(ROOT / "speech_to_asl_avatar.py").write_text(
    helper, encoding="utf-8"
)
APP.write_text(updated, encoding="utf-8")

launcher = r"""@echo off
setlocal
cd /d "%~dp0"
where npm >nul 2>&1
if errorlevel 1 goto :node_error
pushd avatar-engine
if not exist node_modules call npm ci
if errorlevel 1 goto :failed
call npm run build
if errorlevel 1 goto :failed
popd
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run app.py
) else (
    python -m streamlit run app.py
)
exit /b
:node_error
echo Install Node.js and make sure npm is on PATH.
pause
exit /b 1
:failed
echo Avatar dependency installation or build failed.
pause
exit /b 1
"""
(ROOT / "run_signbridge.bat").write_text(
    launcher, encoding="utf-8"
)

print("Integration files created successfully.")
print("Existing recognition and Gemini code preserved.")
print("Next: double-click run_signbridge.bat")
