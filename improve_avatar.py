
from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "avatar-engine"
MAIN = ENGINE / "src" / "main.js"
SPEECH = ENGINE / "src" / "sign-speech.js"

if not MAIN.is_file():
    raise SystemExit("Missing avatar-engine/src/main.js")

if not SPEECH.is_file():
    raise SystemExit("Missing avatar-engine/src/sign-speech.js")

source = MAIN.read_text(encoding="utf-8")
speech = SPEECH.read_text(encoding="utf-8")

MARK = "SIGNBRIDGE_LIVE_CAPTION_V1"

if MARK in source:
    raise SystemExit(
        "The live sign label is already installed."
    )

def insert_after(text, marker, addition):
    if marker not in text:
        raise ValueError("Required code not found: " + marker)
    return text.replace(marker, marker + addition, 1)

# ---------------------------------------------------
# 1. Create floating label in the avatar viewer
# ---------------------------------------------------

caption_code = r"""

// SIGNBRIDGE_LIVE_CAPTION_V1
// Display the sign synchronized with its real timeline.

let signSegments = [];
const headPosition = new THREE.Vector3();

const liveCaption = document.createElement("div");
liveCaption.id = "signbridge-live-caption";

liveCaption.style.cssText = `
    position:absolute;
    z-index:100;
    display:none;
    transform:translate(-50%,-100%);
    background:rgba(8,20,38,0.92);
    border:2px solid #65e6d8;
    border-radius:14px;
    color:white;
    font:700 20px Arial,sans-serif;
    text-align:center;
    padding:12px 22px;
    max-width:90%;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    pointer-events:none;
    box-shadow:0 8px 25px rgba(0,0,0,0.35);
`;

viewer.style.position = "relative";
viewer.appendChild(liveCaption);

function setLiveCaption(value) {
    if (liveCaption.textContent !== value) {
        liveCaption.textContent = value;
    }
    liveCaption.style.display = value ? "block" : "none";
}

function updateLiveCaption() {
    if (!avatar || !clipAction || !signSegments.length) {
        return;
    }

    const t = clipAction.time;
    const finalSegment = signSegments[signSegments.length - 1];

    if (clipAction.paused && t >= finalSegment.end - 0.02) {
        setLiveCaption("SIGNING COMPLETE");
    } else {
        const segment = signSegments.find(
            item => t >= item.start && t < item.end
        );

        if (!segment) {
            if (t >= finalSegment.end) {
                setLiveCaption("SIGNING COMPLETE");
            } else {
                setLiveCaption("NEXT SIGN...");
            }
        } else if (segment.signed) {
            setLiveCaption(
                "SIGNING: " + segment.word.toUpperCase()
            );
        } else {
            const letter = segment.letters?.find(
                item => t >= item.start && t < item.end
            );

            const currentLetter = letter
                ? " | " + letter.letter.toUpperCase()
                : "";

            setLiveCaption(
                "FINGERSPELLING: " +
                segment.word.toUpperCase() +
                currentLetter
            );
        }
    }

    // Position the caption directly above the avatar's head.
    camera.updateMatrixWorld();

    const p = headPosition.clone().project(camera);
    const width = viewer.clientWidth;
    const height = viewer.clientHeight;

    const x = (p.x * 0.5 + 0.5) * width;
    const y = (-p.y * 0.5 + 0.5) * height;

    liveCaption.style.left =
        Math.max(20, Math.min(width - 20, x)) + "px";

    liveCaption.style.top =
        Math.max(45, Math.min(height - 10, y)) + "px";
}
"""

source = insert_after(
    source,
    "const restPose = new Map();",
    caption_code
)

# ---------------------------------------------------
# 2. Calculate the position above the avatar's head
# ---------------------------------------------------

head_code = """

  const updatedBox = new THREE.Box3().setFromObject(avatar);
  const updatedCenter = updatedBox.getCenter(new THREE.Vector3());

  headPosition.set(
    updatedCenter.x,
    updatedBox.max.y + size.y * 0.06,
    updatedCenter.z
  );
"""

source = insert_after(
    source,
    "avatar.position.z -= center.z;",
    head_code
)

# ---------------------------------------------------
# 3. Reset the label when a new phrase begins
# ---------------------------------------------------

source = insert_after(
    source,
    "mixer.stopAllAction();",
    """
    signSegments = [];
    setLiveCaption("");
"""
)

# ---------------------------------------------------
# 4. Use the real timing supplied by the sign compiler
# ---------------------------------------------------

source = insert_after(
    source,
    "clipAction = mixer.clipAction(retargeted.clip);",
    """

    signSegments = output.segments || [];
"""
)

# ---------------------------------------------------
# 5. Slow the animation for clearer movement
# ---------------------------------------------------

source = insert_after(
    source,
    "clipAction.reset();",
    """
    clipAction.setEffectiveTimeScale(0.75);
"""
)

# ---------------------------------------------------
# 6. Update the label with every animation frame
# ---------------------------------------------------

old_render = """  controls.update();
  renderer.render(scene, camera);"""

new_render = """  controls.update();
  updateLiveCaption();
  renderer.render(scene, camera);"""

if old_render not in source:
    raise SystemExit("Cannot find the animation render loop.")

source = source.replace(old_render, new_render, 1)

# ---------------------------------------------------
# 7. Increase spacing between consecutive signs
# ---------------------------------------------------

old_gap = "const WORD_GAP_SECONDS = 0.18;"
new_gap = "const WORD_GAP_SECONDS = 0.28;"

if old_gap in speech:
    speech = speech.replace(old_gap, new_gap, 1)
else:
    print("Word gap already customized; leaving it unchanged.")

# ---------------------------------------------------
# 8. Save backups and updated files
# ---------------------------------------------------

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

shutil.copy2(
    MAIN,
    MAIN.with_name(f"main_before_caption_{timestamp}.js")
)

shutil.copy2(
    SPEECH,
    SPEECH.with_name(f"sign_speech_before_caption_{timestamp}.js")
)

MAIN.write_text(source, encoding="utf-8")
SPEECH.write_text(speech, encoding="utf-8")

print()
print("Avatar improvements installed.")
print("1. Current sign displayed above avatar.")
print("2. Fingerspelled letters displayed.")
print("3. Playback slowed to 75%.")
print("4. Word spacing increased.")
print("5. Existing signing dictionary preserved.")
print()
print("Next: rebuild the avatar engine using npm run build.")
