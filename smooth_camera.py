
from pathlib import Path
from datetime import datetime
import re
import shutil

FILE = Path("recognition/webcam_streamlit.py")

if not FILE.is_file():
    raise SystemExit(
        "ERROR: recognition/webcam_streamlit.py not found."
    )

code = FILE.read_text(encoding="utf-8")

if "SIGNBRIDGE_AI_BACKGROUND_V1" in code:
    raise SystemExit(
        "Background recognition is already installed."
    )

if "def _recognize_small_frame(self, frame):" not in code:
    raise SystemExit(
        "Your earlier optimized webcam code is missing. "
        "No changes were made."
    )

# -------------------------------------------------
# 1. Initialize the separate AI processing thread
# -------------------------------------------------

anchor = "        self.translator.start()"

if code.count(anchor) != 1:
    raise SystemExit(
        "Could not locate recognition worker initialization."
    )

initialization = """

        # Keep only the newest frame for AI processing.
        self._ai_frame_lock = threading.Lock()
        self._ai_frame_ready = threading.Event()
        self._latest_ai_frame = None
        self._last_ai_submit = 0.0

        self._ai_thread = threading.Thread(
            target=self._ai_background_loop,
            daemon=True,
        )
        self._ai_thread.start()
"""

code = code.replace(anchor, anchor + initialization, 1)

# -------------------------------------------------
# 2. Replace blocking recognition with background AI
# -------------------------------------------------

pattern = (
    r"(?ms)^    def recv\\(self, frame\\):\\n"
    r".*?(?=^    def "
    r"(?:_draw_sign_label|_recognize_small_frame)"
    r"\\(self, frame\\):)"
)

# Build the regex without double-escaped backslashes.
pattern = (
    r"(?ms)^    def recv\(self, frame\):\n"
    r".*?(?=^    def "
    r"(?:_draw_sign_label|_recognize_small_frame)"
    r"\(self, frame\):)"
)

match = re.search(pattern, code)

if not match:
    raise SystemExit(
        "Could not safely locate the existing webcam loop."
    )

has_label = (
    "def _draw_sign_label(self, frame):" in code
)

video_return = (
    "self._draw_sign_label(frame)"
    if has_label else "frame"
)

replacement = '''
    # SIGNBRIDGE_AI_BACKGROUND_V1

    def _ai_background_loop(self):
        """
        Process only the newest available video frame.

        The camera display never waits for inference.
        """

        while not self.stop_event.is_set():

            if not self._ai_frame_ready.wait(timeout=0.1):
                continue

            self._ai_frame_ready.clear()

            with self._ai_frame_lock:
                frame = self._latest_ai_frame
                self._latest_ai_frame = None

            if frame is None:
                continue

            if self.stop_event.is_set():
                break

            try:
                self._recognize_small_frame(frame)

            except Exception as exc:
                print("Background AI error:", exc)

    def recv(self, frame):
        """
        Return camera frames immediately.

        MediaPipe runs independently in another thread.
        """

        now = time.monotonic()

        # Cap AI analysis at 12 samples per second.
        # This does not cap the webcam preview FPS.
        if now - self._last_ai_submit >= 1.0 / 12.0:

            self._last_ai_submit = now

            with self._ai_frame_lock:
                # Replace any unprocessed older frame.
                self._latest_ai_frame = frame

            self._ai_frame_ready.set()

        return VIDEO_RETURN

'''.replace("VIDEO_RETURN", video_return)

code = (
    code[:match.start()]
    + replacement
    + code[match.end():]
)

# -------------------------------------------------
# 3. Shut down AI thread safely when camera stops
# -------------------------------------------------

close_anchor = (
    "    def close(self):\n"
    "        self.stop_event.set()"
)

if code.count(close_anchor) != 1:
    raise SystemExit(
        "Could not locate the camera shutdown method."
    )

code = code.replace(
    close_anchor,
    close_anchor + """

        self._ai_frame_ready.set()

        if self._ai_thread.is_alive():
            self._ai_thread.join(timeout=3)
""",
    1,
)

# -------------------------------------------------
# 4. Check syntax and save backup
# -------------------------------------------------

compile(code, str(FILE), "exec")

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

backup = FILE.with_name(
    f"webcam_before_background_ai_{timestamp}.py"
)

shutil.copy2(FILE, backup)
FILE.write_text(code, encoding="utf-8")

print()
print("======================================")
print("SMOOTH CAMERA UPGRADE INSTALLED")
print("======================================")
print("AI processing moved to background thread.")
print("Old AI frames automatically discarded.")
print("Camera preview is no longer held up by AI.")
print("Existing sign labels preserved.")
print("Existing sign recognition model preserved.")
print("Existing sentence and voice logic preserved.")
print()
print("Backup:", backup)
print()
print("Start with:")
print("python -m streamlit run app.py")
