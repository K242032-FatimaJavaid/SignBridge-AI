
from pathlib import Path
from datetime import datetime
import ast
import queue
import shutil
import textwrap

ROOT = Path(__file__).resolve().parent

WEBCAM = ROOT / "recognition" / "webcam_streamlit.py"
SEQUENCE = ROOT / "recognition" / "sequence_realtime.py"

for file in (WEBCAM, SEQUENCE):
    if not file.is_file():
        raise SystemExit(f"Missing file: {file}")

webcam_original = WEBCAM.read_text(encoding="utf-8-sig")
sequence_original = SEQUENCE.read_text(encoding="utf-8-sig")


# ==========================================
# FIX 1: FINISH SENTENCE
# ==========================================

def replace_class_method(source, class_name, method_name, code):
    tree = ast.parse(source)

    classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == class_name
    ]

    if len(classes) != 1:
        raise RuntimeError(f"Class not found: {class_name}")

    methods = [
        node for node in classes[0].body
        if isinstance(node, ast.FunctionDef)
        and node.name == method_name
    ]

    if len(methods) != 1:
        raise RuntimeError(f"Method not found: {method_name}")

    method = methods[0]
    lines = source.splitlines(keepends=True)

    indentation = len(
        lines[method.lineno - 1]
    ) - len(lines[method.lineno - 1].lstrip())

    replacement = textwrap.indent(
        textwrap.dedent(code).strip() + "\n",
        " " * indentation
    )

    lines[method.lineno - 1:method.end_lineno] = [
        replacement
    ]

    updated = "".join(lines)
    compile(updated, "webcam_streamlit.py", "exec")
    return updated


new_finish_method = '''
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
'''

webcam_updated = replace_class_method(
    webcam_original,
    "SignVideoProcessor",
    "finish_sentence",
    new_finish_method,
)

# Allow the button to work even while Gemini
# is processing a previous sentence.
if "Finish Sentence" not in webcam_updated:
    raise RuntimeError("Finish Sentence button not found")

if "disabled=not words or pending" in webcam_updated:
    webcam_updated = webcam_updated.replace(
        "disabled=not words or pending",
        "disabled=not words"
    )
elif "disabled=not words" not in webcam_updated:
    raise RuntimeError(
        "Unexpected Finish Sentence button code. "
        "Original files unchanged."
    )


# ==========================================
# FIX 2: AUTOMATIC HAND-REMOVAL DETECTION
# ==========================================

sequence_updated = sequence_original

# Do not install the same fix twice.
if "self._sentence_end_sent" in sequence_updated:
    raise RuntimeError(
        "Time-based sentence detection appears "
        "to be installed already. "
        "Original files unchanged."
    )

initialization = 'self.last_label = "READY FOR SIGN"'

if sequence_updated.count(initialization) < 1:
    raise RuntimeError("Recognizer initialization not found")

sequence_updated = sequence_updated.replace(
    initialization,
    initialization
    + "\n        self._no_hand_since = None"
    + "\n        self._sentence_end_sent = False",
    1
)

old_no_hand = (
    "        if not hands_present(result):\n"
    "            self.missing_frames += 1"
)

new_no_hand = (
    "        if not hands_present(result):\n"
    "            self.missing_frames += 1\n"
    "\n"
    "            if self._no_hand_since is None:\n"
    "                self._no_hand_since = now"
)

if sequence_updated.count(old_no_hand) != 1:
    raise RuntimeError("No-hand detection block not found")

sequence_updated = sequence_updated.replace(
    old_no_hand,
    new_no_hand,
    1
)

old_end = (
    "            if self.missing_frames == 12:\n"
    "                return self.last_label, None, True"
)

new_end = (
    "            if (\n"
    "                not self._sentence_end_sent\n"
    "                and now - self._no_hand_since >= 1.0\n"
    "            ):\n"
    "                self._sentence_end_sent = True\n"
    "                print(\n"
    '                    "[AUTO SENTENCE END]",\n'
    "                    flush=True\n"
    "                )\n"
    "                return self.last_label, None, True"
)

if sequence_updated.count(old_end) != 1:
    raise RuntimeError("Original sentence-end block not found")

sequence_updated = sequence_updated.replace(
    old_end,
    new_end,
    1
)

old_reset = (
    "            return self.last_label, None, False\n"
    "\n"
    "        self.missing_frames = 0"
)

new_reset = (
    "            return self.last_label, None, False\n"
    "\n"
    "        self.missing_frames = 0\n"
    "        self._no_hand_since = None\n"
    "        self._sentence_end_sent = False"
)

if sequence_updated.count(old_reset) != 1:
    raise RuntimeError("Hand detection reset not found")

sequence_updated = sequence_updated.replace(
    old_reset,
    new_reset,
    1
)


# ==========================================
# SAFETY CHECKS BEFORE CHANGING FILES
# ==========================================

compile(
    webcam_updated,
    str(WEBCAM),
    "exec"
)

compile(
    sequence_updated,
    str(SEQUENCE),
    "exec"
)

stamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

webcam_backup = WEBCAM.with_name(
    f"webcam_before_sentence_fix_{stamp}.py"
)

sequence_backup = SEQUENCE.with_name(
    f"sequence_before_sentence_fix_{stamp}.py"
)

shutil.copy2(WEBCAM, webcam_backup)
shutil.copy2(SEQUENCE, sequence_backup)

WEBCAM.write_text(
    webcam_updated,
    encoding="utf-8"
)

SEQUENCE.write_text(
    sequence_updated,
    encoding="utf-8"
)

print()
print("======================================")
print("SIGNBRIDGE SENTENCE SYSTEM UPDATED")
print("======================================")
print("Finish Sentence no longer waits for Gemini.")
print("Confirmed words can form new sentences.")
print("Automatic ending uses a 1-second hand pause.")
print("Original recognition model unchanged.")
print("Webcam and Precise Mode preserved.")
print()
print("Backups:")
print(webcam_backup)
print(sequence_backup)
