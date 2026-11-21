from pathlib import Path
from datetime import datetime
import re
import shutil

ROOT = Path(__file__).resolve().parent

WEBCAM = ROOT / "recognition" / "webcam_streamlit.py"
SEQ = ROOT / "recognition" / "sequence_realtime.py"

if not WEBCAM.exists():
    raise SystemExit("Missing recognition/webcam_streamlit.py")

if not SEQ.exists():
    raise SystemExit("Missing recognition/sequence_realtime.py")

webcam_code = WEBCAM.read_text(encoding="utf-8")
seq_code = SEQ.read_text(encoding="utf-8")

# ---------------------------------------------------
# 1. Remove the 24-frame counter style text
# ---------------------------------------------------

seq_code = seq_code.replace(
    'self.last_label = (\n                f"ANALYZING {len(self.window)}/{LENGTH}"\n            )',
    'self.last_label = "READING SIGN..."'
)

seq_code = seq_code.replace(
    'return self.last_label, None, False',
    'return self.last_label, None, False',
    1
)

seq_code = seq_code.replace(
    'self.last_label = "NO HAND"',
    'self.last_label = "READY FOR SIGN"'
)

# ---------------------------------------------------
# 2. Make sure numpy exists in webcam file
# ---------------------------------------------------

if "import numpy as np" not in webcam_code:
    webcam_code = webcam_code.replace(
        "import cv2\n",
        "import cv2\nimport numpy as np\n",
        1
    )

# ---------------------------------------------------
# 3. Replace the overlay drawing method
# ---------------------------------------------------

pattern = re.compile(
    r"(?ms)^    def _draw_sign_label\(self, frame\):\n.*?(?=^    def )"
)

new_method = '''
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
'''

match = pattern.search(webcam_code)

if not match:
    raise SystemExit("Could not find _draw_sign_label() in webcam_streamlit.py")

webcam_code = webcam_code[:match.start()] + new_method + webcam_code[match.end():]

# ---------------------------------------------------
# 4. Save backups and updated files
# ---------------------------------------------------

compile(seq_code, str(SEQ), "exec")
compile(webcam_code, str(WEBCAM), "exec")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

seq_backup = SEQ.with_name(f"sequence_realtime_before_ui_{stamp}.py")
webcam_backup = WEBCAM.with_name(f"webcam_streamlit_before_ui_{stamp}.py")

shutil.copy2(SEQ, seq_backup)
shutil.copy2(WEBCAM, webcam_backup)

SEQ.write_text(seq_code, encoding="utf-8")
WEBCAM.write_text(webcam_code, encoding="utf-8")

print("======================================")
print("AESTHETIC UI OVERLAY INSTALLED")
print("======================================")
print("Removed 24-frame counter display")
print("Top-left status chip upgraded")
print("Bottom-left glassmorphism sentence panel added")
print("Backups created:")
print(" -", seq_backup.name)
print(" -", webcam_backup.name)
print()
print("Next: python -m streamlit run app.py")