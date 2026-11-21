
from pathlib import Path
from datetime import datetime
import re
import shutil

# SignBridge AI - Smooth 4K Webcam Upgrade
# Updates ONLY recognition/webcam_streamlit.py

ROOT = Path(__file__).resolve().parent
FILE = ROOT / "recognition" / "webcam_streamlit.py"

if not FILE.is_file():
    raise SystemExit(
        "ERROR: recognition/webcam_streamlit.py was not found."
    )

code = FILE.read_text(encoding="utf-8")

if "SIGNBRIDGE_SMOOTH_4K_V1" in code:
    raise SystemExit("Smooth 4K upgrade is already installed.")

# --------------------------------------------------
# 1. Add recognition performance controls
# --------------------------------------------------

old = "        self.lock = threading.Lock()\n"

new = """        self.lock = threading.Lock()

        self._inference_gate = threading.Lock()
        self._last_inference_time = 0.0
        self.current_label = "SHOW A SIGN"
        self.source_resolution = (0, 0)
"""

if code.count(old) != 1:
    raise SystemExit("Could not locate the processor lock.")

code = code.replace(old, new, 1)

# --------------------------------------------------
# 2. Replace the expensive video processing loop
# --------------------------------------------------

pattern = (
    r"(?ms)^    def recv\(self, frame\):\n"
    r".*?(?=^    def close\(self\):)"
)

match = re.search(pattern, code)

if not match:
    raise SystemExit("Could not locate the webcam recv method.")

replacement = '''    # SIGNBRIDGE_SMOOTH_4K_V1

    def recv(self, frame):
        """
        Return video frames immediately.

        Only run AI inference periodically, so MediaPipe
        does not hold up every webcam frame.
        """
        now = time.monotonic()
        interval = 1.0 / 12.0

        if now - self._last_inference_time >= interval:
            if self._inference_gate.acquire(blocking=False):
                try:
                    self._last_inference_time = now
                    self._recognize_small_frame(frame)
                except Exception as exc:
                    print("Recognition frame error:", exc)
                finally:
                    self._inference_gate.release()

        # Return original full-resolution frame directly.
        # No 4K NumPy copying, flipping, text drawing,
        # or recreation of the output video frame.
        return frame

    def _recognize_small_frame(self, frame):
        """
        Downscale only the frame used by MediaPipe.
        Keep the existing trained model and sign logic.
        """

        # Resize using FFmpeg/PyAV before converting to NumPy.
        small_frame = frame.reformat(
            width=640,
            height=360,
            format="bgr24"
        )

        image = small_frame.to_ndarray()

        # Preserve the mirrored input used during recognition.
        image = cv2.flip(image, 1)

        rgb = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )
        rgb.flags.writeable = False

        result = self.hands.process(rgb)

        hand_detected = hands_present(result)
        predicted_sign = None
        label = "NO HAND"
        now = time.monotonic()

        if hand_detected:
            self.last_hand_time = now

            probabilities = self.model.predict_proba(
                [vectorize_hands(result)]
            )[0]

            ranked = probabilities.argsort()[::-1]
            best_idx = int(ranked[0])
            best_confidence = float(probabilities[best_idx])

            second_confidence = (
                float(probabilities[ranked[1]])
                if len(ranked) > 1
                else 0.0
            )

            margin = best_confidence - second_confidence

            if (
                best_confidence >= CONFIDENCE_THRESHOLD
                and margin >= MIN_CONFIDENCE_MARGIN
            ):
                predicted_sign = str(
                    self.model.classes_[best_idx]
                )
                label = (
                    f"{predicted_sign} "
                    f"({best_confidence:.2f})"
                )
            else:
                label = "UNCERTAIN"

        if not hand_detected:
            self.no_hand_frames += 1
            self.recent_predictions.clear()

            if self.no_hand_frames >= NO_HAND_RESET_FRAMES:
                self.active_sign = None
                self.ready_for_next_sign = True

            if self.no_hand_frames == NO_HAND_RESET_FRAMES:
                self.finish_sentence()
        else:
            self.no_hand_frames = 0
            self.recent_predictions.append(predicted_sign)

        stable = (
            len(self.recent_predictions) == STABLE_FRAMES
            and predicted_sign is not None
            and all(
                sign == predicted_sign
                for sign in self.recent_predictions
            )
        )

        if (
            stable
            and now - self.last_sign_time >= SIGN_COOLDOWN
        ):
            with self.lock:
                busy = self.sentence_pending

            if not busy and predicted_sign != self.active_sign:
                word = predicted_sign.replace("_", " ")

                with self.lock:
                    self.detected_signs.append(predicted_sign)
                    self.detected_signs = (
                        self.detected_signs[-100:]
                    )

                    self.sentence_words.append(word)
                    self.sentence_words = (
                        self.sentence_words[-100:]
                    )

                self.active_sign = predicted_sign
                self.last_spoken = predicted_sign
                self.last_sign_time = now
                self.ready_for_next_sign = False

                print("Recognized:", predicted_sign)

        with self.lock:
            self.current_label = label
            self.source_resolution = (
                frame.width,
                frame.height
            )

'''

code = code[:match.start()] + replacement + code[match.end():]

print("[OK] Nonblocking recognition loop prepared.")

# --------------------------------------------------
# 3. Report current recognition status in dashboard
# --------------------------------------------------

if '"current_label": self.current_label' not in code:
    marker = '"history": self.detected_signs.copy(),'

    if marker not in code:
        raise SystemExit("Could not locate recognition snapshot.")

    code = code.replace(
        marker,
        '"current_label": self.current_label,\n'
        '                "source_resolution": '
        'self.source_resolution,\n'
        '                ' + marker,
        1
    )

# Remove duplicate resolution entry if an older
# 4K patch already added that key.
snapshot_start = code.index("    def get_snapshot(self):")
snapshot_end = code.index(
    "    def undo_last(self):",
    snapshot_start
)

snapshot_block = code[snapshot_start:snapshot_end]

resolution_line = (
    '"source_resolution": self.source_resolution,'
)

if snapshot_block.count(resolution_line) > 1:
    snapshot_block = snapshot_block.replace(
        resolution_line, "", 1
    )
    code = (
        code[:snapshot_start]
        + snapshot_block
        + code[snapshot_end:]
    )

# --------------------------------------------------
# 4. Add 4K and high-FPS quality modes
# --------------------------------------------------

quality_code = '''
    quality = st.selectbox(
        "Camera quality and smoothness",
        [
            "4K UHD - 30 FPS",
            "Full HD - 60 FPS",
            "Full HD - 30 FPS",
            "HD - 60 FPS",
        ],
        index=0,
        help=(
            "4K provides maximum detail. "
            "Full HD at 60 FPS may look smoother "
            "if the browser or GPU cannot handle "
            "the 4K WebRTC stream."
        ),
    )

    target_width, target_height, target_fps = {
        "4K UHD - 30 FPS": (3840, 2160, 30),
        "Full HD - 60 FPS": (1920, 1080, 60),
        "Full HD - 30 FPS": (1920, 1080, 30),
        "HD - 60 FPS": (1280, 720, 60),
    }[quality]

    st.caption(
        "Requested: "
        f"{target_width} x {target_height} "
        f"at {target_fps} FPS. "
        "Actual camera settings may vary. "
        "Stop and restart the webcam "
        "after changing this option."
    )

'''

webcam_start = code.find("def show_webcam():")

if webcam_start < 0:
    raise SystemExit("Could not find show_webcam().")

# Remove an older quality selector if present.
old_quality = code.find(
    "    quality = st.selectbox(",
    webcam_start
)

streamer_start = code.find(
    "    ctx = webrtc_streamer(",
    webcam_start
)

if streamer_start < 0:
    raise SystemExit("Could not find webrtc_streamer().")

if 0 <= old_quality < streamer_start:
    code = (
        code[:old_quality]
        + quality_code
        + code[streamer_start:]
    )
else:
    code = (
        code[:streamer_start]
        + quality_code
        + code[streamer_start:]
    )

# --------------------------------------------------
# 5. Set browser camera resolution and FPS
# --------------------------------------------------

constraints_pattern = (
    r"(?ms)^        media_stream_constraints=\{\n"
    r".*?^        \},\n"
)

constraints = re.search(constraints_pattern, code)

if not constraints:
    raise SystemExit(
        "Could not find browser camera constraints."
    )

new_constraints = '''        media_stream_constraints={
            "video": {
                "width": {"ideal": target_width},
                "height": {"ideal": target_height},
                "frameRate": {
                    "ideal": target_fps,
                    "max": target_fps,
                },
                "facingMode": "user",
            },
            "audio": False,
        },
'''

code = (
    code[:constraints.start()]
    + new_constraints
    + code[constraints.end():]
)

# Keep async processing enabled for frame dropping.
if "async_processing=True" not in code:
    raise SystemExit(
        "Expected async_processing=True was not found."
    )

# --------------------------------------------------
# 6. Show status and actual video resolution
# --------------------------------------------------

status_code = '''    label = snapshot.get(
        "current_label", "Waiting for a sign"
    )

    actual_width, actual_height = snapshot.get(
        "source_resolution", (0, 0)
    )

    st.markdown(f"**Current detection:** {label}")

    if actual_width and actual_height:
        st.caption(
            "Actual webcam stream: "
            f"{actual_width} x {actual_height}"
        )

'''

snapshot_marker = (
    '    snapshot = processor.get_snapshot()\n'
)

if code.count(snapshot_marker) != 1:
    raise SystemExit(
        "Could not find the live-results snapshot."
    )

code = code.replace(
    snapshot_marker,
    snapshot_marker + "\n" + status_code,
    1
)

# --------------------------------------------------
# 7. Validate, back up, save
# --------------------------------------------------

compile(code, str(FILE), "exec")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = FILE.with_name(
    f"webcam_before_smooth_4k_{timestamp}.py"
)

shutil.copy2(FILE, backup)
FILE.write_text(code, encoding="utf-8")

print()
print("=====================================")
print("SIGNBRIDGE AI SMOOTH 4K UPDATE SAVED")
print("=====================================")
print("4K capture mode available.")
print("High-FPS alternatives available.")
print("AI processes small frames at 12 FPS.")
print("Video frames pass through immediately.")
print("Existing trained model preserved.")
print("Sentence recognition logic preserved.")
print("Backup:", backup)
print()
print("Run: python -m streamlit run app.py")
