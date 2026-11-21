
from pathlib import Path
from datetime import datetime
import shutil

file = Path("recognition/webcam_streamlit.py")

if not file.exists():
    raise SystemExit("Webcam module not found.")

original = file.read_text(encoding="utf-8")

old = "        return self._draw_sign_label(frame)"

new = """        # Keep 4K video flowing without expensive overlays.
        # Recognition continues independently.
        if frame.width >= 3000:
            return frame

        # Preserve the glass overlay at lower resolutions.
        # Do not terminate the video stream if it fails.
        try:
            return self._draw_sign_label(frame)
        except Exception as exc:
            print("Video overlay error:", repr(exc), flush=True)
            return frame"""

if original.count(old) != 1:
    raise SystemExit(
        "Expected webcam return statement not found. "
        "No changes made."
    )

updated = original.replace(old, new, 1)

compile(updated, str(file), "exec")

backup = file.with_name(
    "webcam_before_stability_fix_"
    + datetime.now().strftime("%Y%m%d_%H%M%S")
    + ".py"
)

shutil.copy2(file, backup)
file.write_text(updated, encoding="utf-8")

print("Camera stability test patch installed.")
print("4K overlay temporarily bypassed.")
print("19-sign model and speech logic unchanged.")
print("Backup:", backup)
