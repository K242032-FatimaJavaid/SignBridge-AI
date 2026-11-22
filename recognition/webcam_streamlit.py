
"""SignBridge AI - Sentence interpretation and automatic speech."""

from pathlib import Path
from collections import deque
import base64
import queue
import subprocess
import threading
import time
import os
import av
import cv2
import numpy as np
import joblib
import mediapipe as mp
import streamlit as st
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer, WebRtcMode

from recognition.features import vectorize_hands, hands_present
from recognition.unified_realtime import UnifiedRecognizer


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "sequence_extended_v1.joblib"

CONFIDENCE_THRESHOLD = 0.70
STABLE_FRAMES = 5
MIN_STABLE_VOTES = 3
MIN_CONFIDENCE_MARGIN = 0.08

NO_HAND_RESET_SECONDS = 0.25
SENTENCE_PAUSE_SECONDS = 0.85
SIGN_COOLDOWN = 0.35

@st.cache_resource
def load_sign_model():
    return joblib.load(MODEL_PATH)


def windows_speak(text):
    """Speak through the Windows computer's speakers."""
    encoded = base64.b64encode(
        text.encode("utf-8")
    ).decode("ascii")

    script = f"""
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{
    $bytes = [Convert]::FromBase64String('{encoded}')
    $message = [System.Text.Encoding]::UTF8.GetString($bytes)
    $speaker.Speak($message)
}}
finally {{
    $speaker.Dispose()
}}
"""

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Windows speech failed."
        )


def interpret_sentence(words, api_key, model_name):
    """Convert recognized sign labels into conservative English."""
    raw = " ".join(words).strip()

    if not raw or not api_key:
        return raw

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are the sentence interpretation component of
SignBridge AI, an assistive sign recognition prototype.

The following words were recognized by a webcam classifier:

{raw}

Convert these words into one short, natural English
sentence when their meaning is reasonably clear.

Rules:
- Preserve the recognized meaning and word order.
- Do not add important information that was not signed.
- Do not invent names, objects, actions, or intentions.
- If the words are ambiguous, keep them close to the
  original sequence instead of guessing.
- Do not explain or mention these instructions.
- Return only the sentence, without quotation marks.
"""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        text = (response.text or "").strip()

        if not text:
            return raw

        # Reject unexpectedly long generated responses.
        if len(text) > 300:
            return raw

        return text

    except Exception as exc:
        print("Gemini interpretation error:", exc)
        return raw


class SignVideoProcessor(VideoProcessorBase):

    def __init__(self, api_key="", model_name="gemini-2.5-flash"):
        self.model = load_sign_model()
        self.sequence_recognizer = UnifiedRecognizer(self.model)

        self.api_key = api_key
        self.model_name = model_name

        self.hands = mp.solutions.hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )

        self.recent_predictions = deque(
            maxlen=STABLE_FRAMES
        )

        self.lock = threading.Lock()

        self._inference_gate = threading.Lock()
        self._last_inference_time = 0.0
        self.current_label = "SHOW A SIGN"
        self.source_resolution = (0, 0)
        self.source_resolution = (0, 0)

        self.detected_signs = []
        self.sentence_words = []
        self.completed_sentences = []

        self.last_spoken = None
        self.last_sign_time = 0.0
        self.last_hand_time = time.monotonic()

        self.ready_for_next_sign = True
        self.active_sign = None
        self.no_hand_frames = 0
        self.hand_absent_since = None
        self.absence_finalized = False
        self.sentence_pending = False

        self.speech_queue = queue.Queue(maxsize=10)
        self.sentence_queue = queue.Queue(maxsize=10)
        self.stop_event = threading.Event()

        self.speaker = threading.Thread(
            target=self.speech_worker,
            daemon=True,
        )
        self.speaker.start()

        self.translator = threading.Thread(
            target=self.sentence_worker,
            daemon=True,
        )
        self.translator.start()

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


    def speech_worker(self):

        # Reuse one Windows speech engine for faster startup.
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
        except Exception as exc:
            print("Fast speech unavailable:", exc)
            speaker = None

        while not self.stop_event.is_set():
            try:
                text = self.speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if text is None:
                    break

                if speaker is not None:
                    try:
                        speaker.Speak(text)
                    except Exception as exc:
                        print("Fast speech fallback:", exc)
                        speaker = None
                        windows_speak(text)
                else:
                    windows_speak(text)
                print("Spoken:", text)

            except Exception as exc:
                print("Speech error:", exc)

            finally:
                self.speech_queue.task_done()

    def sentence_worker(self):
        while not self.stop_event.is_set():
            try:
                words = self.sentence_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if words is None:
                    break

                raw = " ".join(words)

                translated = interpret_sentence(
                    words,
                    self.api_key,
                    self.model_name,
                )

                with self.lock:
                    self.completed_sentences.append(
                        {
                            "raw": raw,
                            "translation": translated,
                        }
                    )

                    self.completed_sentences = (
                        self.completed_sentences[-50:]
                    )

                print("Recognized sequence:", raw)
                print("Interpreted sentence:", translated)

                # The raw recognized words were already queued for immediate
                # speech in finish_sentence(). Do not speak a second time.

            except Exception as exc:
                print("Sentence worker error:", exc)

            finally:
                with self.lock:
                    self.sentence_pending = False

                self.sentence_queue.task_done()

    def speak_text(self, text):
        if not text.strip():
            return False

        try:
            self.speech_queue.put_nowait(text)
            return True
        except queue.Full:
            return False

    def get_snapshot(self):
        with self.lock:
            return {
                
                "current_label": self.current_label,
                "source_resolution": self.source_resolution,
                "history": self.detected_signs.copy(),
                "words": self.sentence_words.copy(),
                "sentences": [
                    item.copy()
                    for item in self.completed_sentences
                ],
                "pending": self.sentence_pending,
            }

    def undo_last(self):
        with self.lock:
            if self.sentence_words:
                self.sentence_words.pop()

    def clear_sentence(self):
        with self.lock:
            self.sentence_words.clear()

    def clear_history(self):
        with self.lock:
            self.detected_signs.clear()

    def clear_completed_sentences(self):
        with self.lock:
            self.completed_sentences.clear()

    def finish_sentence(self):
        """Finish immediately; Gemini runs separately."""

        with self.lock:
            if not self.sentence_words:
                print(
                    "[SENTENCE] No words to finish",
                    flush=True
                )
                return False

            words = self.sentence_words.copy()
            raw = " ".join(words)

            # Clear the current sentence immediately,
            # allowing recognition of the next sentence.
            self.sentence_words.clear()

            # Gemini interpretation must never prevent
            # sentence completion or speech.
            try:
                self.sentence_queue.put_nowait(words)
                self.sentence_pending = True

            except queue.Full:
                # Preserve the sentence even when the
                # Gemini processing queue is full.
                self.completed_sentences.append({
                    "raw": raw,
                    "translation": raw,
                })

                self.completed_sentences = (
                    self.completed_sentences[-50:]
                )

                print(
                    "[SENTENCE] Gemini queue full; "
                    "using original words",
                    flush=True
                )

        # Speak the raw sentence independently
        # of Gemini interpretation.
        queued = self.speak_text(raw)

        print(
            "[SENTENCE FINISHED]",
            raw,
            "speech_queued=" + str(queued),
            flush=True
        )

        if not queued:
            print(
                "[SENTENCE] Speech queue is full",
                flush=True
            )

        return True

    # SIGNBRIDGE_SMOOTH_4K_V1


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
        # SIGNBRIDGE_FAST_PREVIEW_LATEST_V1
        # Keep video processing as light as possible.

        now = time.monotonic()

        # AI processing remains in the background.
        # Only the newest pending frame is retained.
        if now - self._last_ai_submit >= 1.0 / 12.0:
            self._last_ai_submit = now

            with self._ai_frame_lock:
                self._latest_ai_frame = frame

            self._ai_frame_ready.set()

        # Return the original video immediately.
        # Recognition and sentence display still run.
        return frame


    async def recv_queued(self, frames):
        # Discard old video frames when the playback
        # pipeline falls behind the live webcam.
        if not frames:
            return []

        return [self.recv(frames[-1])]



    def _draw_sign_label(self, frame):
        import av

        with self.lock:
            label = str(self.current_label or "READY FOR SIGN")
            sentence_words = list(self.sentence_words[-12:])

        # Normalize labels for a cleaner UI
        upper_label = label.upper()

        if upper_label in ("NO HAND", "READY FOR SIGN"):
            display_label = "Ready for sign"
            accent = (255, 255, 255)
        elif "ANALYZING" in upper_label or "READING SIGN" in upper_label:
            display_label = "Reading sign..."
            accent = (255, 220, 140)
        elif "UNCERTAIN" in upper_label:
            display_label = "Uncertain"
            accent = (140, 210, 255)
        elif "OTHER - IGNORED" in upper_label:
            display_label = "Gesture ignored"
            accent = (180, 180, 180)
        else:
            # remove confidence from display if present
            if " (" in label:
                display_label = label.split(" (")[0].title()
            else:
                display_label = label.title()
            accent = (120, 255, 170)

        sentence_text = " ".join(sentence_words).strip()
        if not sentence_text:
            sentence_text = "Sentence will appear here"

        image = frame.to_ndarray(format="bgr24").copy()

        # Mirror camera preview horizontally
        image = cv2.flip(image, 1)

        h, w = image.shape[:2]

        ui_scale = max(0.75, min(1.35, w / 1600.0))
        title_scale = 0.70 * ui_scale
        body_scale = 0.60 * ui_scale
        thickness = max(1, int(round(2 * ui_scale)))

        def draw_glass_panel(img, x1, y1, x2, y2, alpha=0.30):
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(img.shape[1], x2)
            y2 = min(img.shape[0], y2)

            if x2 <= x1 or y2 <= y1:
                return

            roi = img[y1:y2, x1:x2].copy()
            overlay = roi.copy()

            # dark translucent fill
            cv2.rectangle(
                overlay,
                (0, 0),
                (overlay.shape[1] - 1, overlay.shape[0] - 1),
                (28, 34, 45),
                -1
            )

            roi = cv2.addWeighted(overlay, alpha, roi, 1.0 - alpha, 0)

            # subtle white border
            cv2.rectangle(
                roi,
                (0, 0),
                (roi.shape[1] - 1, roi.shape[0] - 1),
                (210, 220, 235),
                1
            )

            img[y1:y2, x1:x2] = roi

        def wrap_text(text, max_width, scale, thick):
            words = text.split()
            if not words:
                return [""]

            lines = []
            current = words[0]

            for word in words[1:]:
                trial = current + " " + word
                width = cv2.getTextSize(
                    trial,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    scale,
                    thick
                )[0][0]

                if width <= max_width:
                    current = trial
                else:
                    lines.append(current)
                    current = word

            lines.append(current)
            return lines

        # ---------- TOP LEFT STATUS CHIP ----------
        status_text = display_label
        text_size, base = cv2.getTextSize(
            status_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            title_scale,
            thickness
        )
        status_w = text_size[0] + int(80 * ui_scale)
        status_h = text_size[1] + base + int(30 * ui_scale)

        top_x = int(22 * ui_scale)
        top_y = int(18 * ui_scale)

        draw_glass_panel(
            image,
            top_x,
            top_y,
            top_x + status_w,
            top_y + status_h,
            alpha=0.36
        )

        # status dot
        dot_center = (
            top_x + int(20 * ui_scale),
            top_y + status_h // 2
        )
        cv2.circle(
            image,
            dot_center,
            max(5, int(7 * ui_scale)),
            accent,
            -1,
            cv2.LINE_AA
        )

        cv2.putText(
            image,
            status_text,
            (
                top_x + int(35 * ui_scale),
                top_y + status_h - int(12 * ui_scale)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            title_scale,
            (245, 248, 252),
            thickness,
            cv2.LINE_AA
        )

        # ---------- BOTTOM LEFT SENTENCE PANEL ----------
        sentence_title = "Sentence"
        sentence_max_width = int(w * 0.52)
        wrapped = wrap_text(
            sentence_text,
            sentence_max_width - int(34 * ui_scale),
            body_scale,
            thickness
        )

        if len(wrapped) > 3:
            wrapped = wrapped[:3]

        title_size = cv2.getTextSize(
            sentence_title,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48 * ui_scale,
            thickness
        )[0]

        line_height = int(30 * ui_scale)
        sentence_panel_h = int(28 * ui_scale) + title_size[1] + len(wrapped) * line_height + int(24 * ui_scale)

        widest = title_size[0]
        for line in wrapped:
            line_w = cv2.getTextSize(
                line,
                cv2.FONT_HERSHEY_SIMPLEX,
                body_scale,
                thickness
            )[0][0]
            widest = max(widest, line_w)

        sentence_panel_w = min(
            int(w * 0.60),
            widest + int(44 * ui_scale)
        )

        bottom_x = int(22 * ui_scale)
        bottom_y = h - sentence_panel_h - int(22 * ui_scale)

        draw_glass_panel(
            image,
            bottom_x,
            bottom_y,
            bottom_x + sentence_panel_w,
            bottom_y + sentence_panel_h,
            alpha=0.33
        )

        cv2.putText(
            image,
            sentence_title,
            (
                bottom_x + int(18 * ui_scale),
                bottom_y + int(24 * ui_scale)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48 * ui_scale,
            (185, 205, 225),
            thickness,
            cv2.LINE_AA
        )

        start_y = bottom_y + int(52 * ui_scale)
        for i, line in enumerate(wrapped):
            cv2.putText(
                image,
                line,
                (
                    bottom_x + int(18 * ui_scale),
                    start_y + i * line_height
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                body_scale,
                (245, 248, 252),
                thickness,
                cv2.LINE_AA
            )

        return av.VideoFrame.from_ndarray(image, format="bgr24")
    def _recognize_small_frame(self, frame):
        if self.stop_event.is_set():
            return

        small = frame.reformat(
            width=640,
            height=360,
            format="bgr24"
        )

        image = small.to_ndarray()
        image = cv2.flip(image, 1)

        rgb = cv2.cvtColor(
            image, cv2.COLOR_BGR2RGB
        )
        rgb.flags.writeable = False

        result = self.hands.process(rgb)

        label, sign, sentence_ended = (
            self.sequence_recognizer.update(result)
        )

        with self.lock:
            self.current_label = label
            self.source_resolution = (
                frame.width, frame.height
            )

        if sign:
            is_letter = sign.startswith("LETTER:")
            is_digit = sign.startswith("DIGIT:")

            if is_letter or is_digit:
                character = sign.split(":", 1)[1]

                kind = (
                    "letters" if is_letter else "digits"
                )

                with self.lock:
                    if (
                        self.sentence_words
                        and getattr(
                            self, "_last_token_kind", None
                        ) == kind
                    ):
                        self.sentence_words[-1] += character
                    else:
                        self.sentence_words.append(character)

                    self._last_token_kind = kind
                    self.detected_signs.append(character)
                    self.detected_signs = (
                        self.detected_signs[-100:]
                    )

            else:
                word = sign.replace("_", " ")

                with self.lock:
                    self.sentence_words.append(word)
                    self._last_token_kind = "word"

                    self.detected_signs.append(sign)
                    self.detected_signs = (
                        self.detected_signs[-100:]
                    )

            with self.lock:
                self.sentence_words = self.sentence_words[-100:]

            self.last_spoken = sign
            self.last_sign_time = time.monotonic()
            self.ready_for_next_sign = False

            print(
                "[UNIFIED SENTENCE TOKEN]",
                sign,
                flush=True
            )

        if sentence_ended:
            self.ready_for_next_sign = True
            self.finish_sentence()

    def close(self):
        self.stop_event.set()

        self._ai_frame_ready.set()

        if self._ai_thread.is_alive():
            self._ai_thread.join(timeout=3)


        for work_queue in (
            self.speech_queue,
            self.sentence_queue,
        ):
            try:
                work_queue.put_nowait(None)
            except queue.Full:
                pass

        self.hands.close()


@st.fragment(run_every=1)
def show_live_results(ctx):
    processor = ctx.video_processor

    if processor is None:
        st.info("Waiting for webcam initialization...")
        return

    snapshot = processor.get_snapshot()

    label = snapshot.get(
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


    camera_width, camera_height = snapshot.get(
        "source_resolution", (0, 0)
    )

    if camera_width and camera_height:
        st.caption(
            f"Actual camera stream: "
            f"{camera_width} x {camera_height}"
        )

    history = snapshot["history"]
    words = snapshot["words"]
    sentences = snapshot["sentences"]
    pending = snapshot["pending"]


    st.markdown("### Recognition Controls")

    capture_col, auto_col = st.columns(2)

    with capture_col:
        if st.button(
            "Record One Sign",
            key="precise_sign_capture",
            use_container_width=True
        ):
            processor.sequence_recognizer.arm()
            st.info(
                "Get ready, then perform one complete "
                "sign for approximately two seconds."
            )

    with auto_col:
        if st.button(
            "Automatic Mode",
            key="return_auto_recognition",
            use_container_width=True
        ):
            processor.sequence_recognizer.use_automatic()
            st.success("Automatic recognition restored.")

    st.caption(
        "Precise mode captures one complete sign "
        "per button press. Use Finish Sentence "
        "when your sentence is complete."
    )

    st.markdown("### Live Recognition History")

    if history:
        st.write(
            " → ".join(
                sign.replace("_", " ")
                for sign in history[-15:]
            )
        )
    else:
        st.info("No signs recognized yet.")

    st.markdown("### Current Sentence")

    current_sentence = " ".join(words)

    if current_sentence:
        st.info(current_sentence)
    else:
        st.caption("Waiting for signs...")

    if pending:
        st.warning(
            "Interpreting the recognized signs..."
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "Finish Sentence",
            use_container_width=True,
            disabled=not words,
        ):
            processor.finish_sentence()
            st.rerun(scope="fragment")

    with col2:
        if st.button(
            "Undo Last",
            use_container_width=True,
            disabled=not words,
        ):
            processor.undo_last()
            st.rerun(scope="fragment")

    with col3:
        if st.button(
            "Clear",
            use_container_width=True,
            disabled=not words,
        ):
            processor.clear_sentence()
            st.rerun(scope="fragment")

    st.markdown("### Interpreted Sentences")

    if sentences:
        latest = sentences[-1]

        st.success(latest["translation"])

        st.caption(
            "Recognized signs: " + latest["raw"]
        )

        if st.button(
            "Speak Last Sentence",
            use_container_width=True,
        ):
            processor.speak_text(
                latest["translation"]
            )

        with st.expander("Sentence History"):
            for index, item in enumerate(
                sentences,
                start=1,
            ):
                st.write(
                    f"{index}. {item['translation']}"
                )
                st.caption(
                    "Signs: " + item["raw"]
                )

            if st.button("Clear Sentence History"):
                processor.clear_completed_sentences()
                st.rerun(scope="fragment")

    else:
        st.info(
            "Complete a sequence of signs to "
            "generate your first sentence."
        )

    with st.expander("Full Sign Recognition History"):
        for index, sign in enumerate(history, start=1):
            st.write(
                f"{index}. {sign.replace('_', ' ')}"
            )

        if history and st.button(
            "Clear Sign History"
        ):
            processor.clear_history()
            st.rerun(scope="fragment")



# SIGNBRIDGE_SIDE_PANEL_V1
@st.fragment(run_every="1s")
def show_live_side_panel(ctx):
    from html import escape

    processor = ctx.video_processor

    if processor is None:
        st.info("Initializing recognition...")
        return

    data = processor.get_snapshot()

    current = str(
        data.get("current_label") or "READY"
    )

    words = data.get("words", [])
    sentence = " ".join(words).strip()

    history = data.get("history", [])
    latest = (
        str(history[-1]).replace("_", " ")
        if history else "None yet"
    )

    recent = " ? ".join(
        str(sign).replace("_", " ")
        for sign in history[-7:]
    )

    if not recent:
        recent = "Waiting for first sign..."

    st.markdown("""
    <style>
    .sb-side-card {
        background: rgba(23,43,68,.75);
        border: 1px solid rgba(176,218,248,.17);
        border-radius: 20px;
        padding: 21px;
        margin-bottom: 12px;
        box-shadow: 0 12px 35px rgba(0,0,0,.13);
    }
    .sb-side-label {
        font-size: .72rem;
        letter-spacing: .13em;
        font-weight: 800;
        color: #94acbf;
        margin-bottom: 12px;
    }
    .sb-side-value {
        color: #83f0da;
        font-size: clamp(1.15rem,2vw,1.85rem);
        font-weight: 800;
        overflow-wrap: anywhere;
        line-height: 1.35;
    }
    .sb-side-sentence {
        font-size: clamp(1.05rem,1.65vw,1.45rem);
        color: #f5fbff;
        font-weight: 700;
        line-height: 1.6;
        overflow-wrap: anywhere;
        min-height: 55px;
    }
    .sb-side-muted {
        color: #adc2d6;
        font-size: .82rem;
        margin-top: 10px;
        line-height: 1.5;
        overflow-wrap: anywhere;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="sb-side-card">'
        '<div class="sb-side-label">LIVE DETECTION</div>'
        f'<div class="sb-side-value">{escape(current)}</div>'
        '<div class="sb-side-muted">'
        f'Last confirmed: {escape(latest)}'
        '</div></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sb-side-card">'
        '<div class="sb-side-label">FORMING SENTENCE</div>'
        '<div class="sb-side-sentence">'
        f'{escape(sentence or "Waiting for signs...")}'
        '</div></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sb-side-card">'
        '<div class="sb-side-label">RECENT SIGNS</div>'
        '<div class="sb-side-muted">'
        f'{escape(recent)}'
        '</div></div>',
        unsafe_allow_html=True
    )

    left, middle, right = st.columns(3, gap="small")

    with left:
        if st.button(
            "Finish",
            key="sb_side_finish",
            disabled=not words,
            use_container_width=True
        ):
            processor.finish_sentence()
            st.rerun(scope="fragment")

    with middle:
        if st.button(
            "Undo",
            key="sb_side_undo",
            disabled=not words,
            use_container_width=True
        ):
            processor.undo_last()
            st.rerun(scope="fragment")

    with right:
        if st.button(
            "Clear",
            key="sb_side_clear",
            disabled=not words,
            use_container_width=True
        ):
            processor.clear_sentence()
            st.rerun(scope="fragment")

    sentences = data.get("sentences", [])

    if sentences:
        st.markdown("**Last interpreted sentence**")
        st.success(sentences[-1]["translation"])

    st.caption(
        "The panel refreshes every second. "
        "Recognition still depends on the model "
        "confirming each sign."
    )


def show_webcam():
    st.subheader("Live ASL to Sentence Translation")

    if not MODEL_PATH.exists():
        st.error(
            "Model not found. Run "
            "python -m recognition.train"
        )
        return

    st.info(
        "Perform signs one at a time. Change directly to a different "
        "sign and hold it briefly until recognized. To repeat the same "
        "sign, briefly remove your hand. After the last sign, keep "
        "your hands out of view briefly (about one second) to "
        "speak the recognized words immediately. Gemini will refine "
        "the displayed sentence afterward."
    )


    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        model_name = st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")
    except st.errors.StreamlitSecretNotFoundError:
        api_key = os.getenv("GEMINI_API_KEY", "")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        st.warning(
            "Gemini API key not configured. "
            "The app will speak the recognized "
            "words without AI interpretation."
        )


    quality = st.selectbox(
        "Camera quality and smoothness",
        [
            "4K UHD - 30 FPS",
            "Full HD - 60 FPS",
            "Full HD - 30 FPS",
            "HD - 30 FPS",
            "HD - 60 FPS",
            "HD - 30 FPS",
        ],
        index=4,
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
        "HD - 30 FPS": (1280, 720, 30),
        "HD - 60 FPS": (1280, 720, 60),
        "HD - 30 FPS": (1280, 720, 30),
    }[quality]

    st.caption(
        "Requested: "
        f"{target_width} x {target_height} "
        f"at {target_fps} FPS. "
        "Actual camera settings may vary. "
        "Stop and restart the webcam "
        "after changing this option."
    )

    camera_col, info_col = st.columns([1.65, 1], gap='medium')

    with camera_col:
        ctx = webrtc_streamer(
            # Browser displays its own local camera preview.
            # Python continues processing frames for recognition.
            mode=WebRtcMode.SENDRECV,
            key="signbridge-webcam",
            video_processor_factory=lambda: SignVideoProcessor(
                api_key=api_key,
                model_name=model_name,
            ),
            media_stream_constraints={
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
            async_processing=False,
        )

    with info_col:
        if ctx.state.playing:
            show_live_side_panel(ctx)
        else:
            st.info('Start webcam to view live recognition.')

    if ctx.state.playing:
        with st.expander('Advanced controls and full history', expanded=False):
            show_live_results(ctx)
