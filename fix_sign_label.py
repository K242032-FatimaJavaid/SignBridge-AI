
from pathlib import Path
from datetime import datetime
import re
import shutil

FILE = Path("recognition/webcam_streamlit.py")

if not FILE.is_file():
    raise SystemExit("ERROR: webcam_streamlit.py not found.")

code = FILE.read_text(encoding="utf-8")

if "def _draw_sign_label(self, frame):" in code:
    raise SystemExit("The sign-label fix is already installed.")

if "def _recognize_small_frame(self, frame):" not in code:
    raise SystemExit(
        "The optimized webcam code was not found. "
        "No changes were made."
    )

# The optimized version uses NumPy-compatible PyAV planes.
if not re.search(r"^import numpy as np\s*$", code, re.M):
    code = code.replace(
        "import cv2\n",
        "import cv2\nimport numpy as np\n",
        1
    )

# Locate only the camera preview method.
pattern = (
    r"(?ms)(    def recv\(self, frame\):\n.*?)"
    r"(?=    def _recognize_small_frame\(self, frame\):)"
)

match = re.search(pattern, code)

if not match:
    raise SystemExit("Could not locate the webcam preview method.")

section = match.group(1)

if section.count("        return frame\n") != 1:
    raise SystemExit(
        "Unexpected webcam preview structure. "
        "No changes were made."
    )

section = section.replace(
    "        return frame\n",
    "        return self._draw_sign_label(frame)\n",
    1
)

# Fast label renderer: draw on the existing luminance
# plane when possible, avoiding full 4K BGR conversion.
# Fallback to regular OpenCV drawing for other formats.

helper = '''
    def _draw_sign_label(self, frame):
        with self.lock:
            label = str(self.current_label or "SHOW A SIGN")

        width = frame.width

        scale = max(0.85, min(2.4, width / 1600))
        thickness = max(2, round(scale * 2))

        font = cv2.FONT_HERSHEY_SIMPLEX

        text_size, baseline = cv2.getTextSize(
            label, font, scale, thickness
        )

        text_width, text_height = text_size

        x = 18
        y = 18
        bottom = y + text_height + baseline + 24
        right = x + text_width + 34

        # Prefer a small overlay on the YUV luminance
        # plane. The full video does not need conversion.
        try:
            if frame.format.name in ("yuv420p", "nv12"):
                plane = frame.planes[0]
                pixels = np.frombuffer(
                    plane, dtype=np.uint8
                )

                if pixels.flags.writeable:
                    luminance = pixels.reshape(
                        plane.height, plane.line_size
                    )

                    cv2.rectangle(
                        luminance,
                        (x, y),
                        (min(right, frame.width - 1), bottom),
                        16,
                        -1
                    )

                    cv2.putText(
                        luminance,
                        label,
                        (x + 14, y + text_height + 10),
                        font,
                        scale,
                        235,
                        thickness,
                        cv2.LINE_AA
                    )

                    return frame
        except (ValueError, TypeError, cv2.error) as exc:
            print("Using fallback video label:", exc)

        # Fallback for other video formats or
        # read-only pixel buffers.
        image = frame.to_ndarray(format="bgr24")

        cv2.rectangle(
            image,
            (x, y),
            (min(right, image.shape[1] - 1), bottom),
            (15, 20, 30),
            -1
        )

        cv2.putText(
            image,
            label,
            (x + 14, y + text_height + 10),
            font,
            scale,
            (75, 255, 110),
            thickness,
            cv2.LINE_AA
        )

        return av.VideoFrame.from_ndarray(
            image, format="bgr24"
        )

'''

updated_section = section + helper

code = (
    code[:match.start()]
    + updated_section
    + code[match.end():]
)

# Verify syntax before changing the original.
compile(code, str(FILE), "exec")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = FILE.with_name(
    f"webcam_before_label_fix_{timestamp}.py"
)

shutil.copy2(FILE, backup)
FILE.write_text(code, encoding="utf-8")

print("Sign label restored inside webcam preview.")
print("4K camera settings preserved.")
print("Recognition logic preserved.")
print("Backup:", backup)
