
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { applyLanternStage } from "./lantern/stage.js";
import {
  canonicalizeGLBBones,
  retargetClipToObject
} from "@three-ws/retarget";
import { compileUtterance, signLookup } from "../dist/sign-language.mjs";

const viewer = document.querySelector("#viewer");
const status = document.querySelector("#status");
const bonesOutput = document.querySelector("#bones");
const resultOutput = document.querySelector("#result");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xe8edf5);

const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
camera.position.set(0, 1.4, 3.5);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(viewer.clientWidth, viewer.clientHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
viewer.appendChild(renderer.domElement);

// Fallback lights; Lantern Stage adds its own lighting.
scene.add(new THREE.HemisphereLight(0xffffff, 0x667085, 2));

const light = new THREE.DirectionalLight(0xffffff, 2);
light.position.set(2, 4, 3);
scene.add(light);

const controls = new OrbitControls(camera, renderer.domElement);

let avatar;
let mixer;
let clipAction;
let disposeLanternStage;
const restPose = new Map();

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


async function loadAvatar() {
  try {
    status.textContent = "Loading and preparing avatar...";

    const response = await fetch("/models/avatar.glb");
    if (!response.ok) {
      throw new Error(`Avatar request failed: ${response.status}`);
    }

    const raw = await response.arrayBuffer();
    const { buffer } = canonicalizeGLBBones(raw);

    const loader = new GLTFLoader();
    loader.setMeshoptDecoder(MeshoptDecoder);

    const gltf = await loader.parseAsync(buffer, "");

    avatar = gltf.scene;
    scene.add(avatar);

    // Center the avatar and place its feet at ground level.
    const box = new THREE.Box3().setFromObject(avatar);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());

    avatar.position.x -= center.x;
    avatar.position.y -= box.min.y;
    avatar.position.z -= center.z;

  const updatedBox = new THREE.Box3().setFromObject(avatar);
  const updatedCenter = updatedBox.getCenter(new THREE.Vector3());

  headPosition.set(
    updatedCenter.x,
    updatedBox.max.y + size.y * 0.06,
    updatedCenter.z
  );


    // Apply the studio background, lighting, and floor.
    try {
      disposeLanternStage = applyLanternStage({
        renderer,
        scene,
        camera,
        avatar
      });
    } catch (error) {
      console.error("Lantern Stage setup failed:", error);
      status.textContent =
        "Studio stage failed; loading avatar with normal lighting.";
    }

    // Frame the avatar.
    camera.position.set(
      0,
      Math.max(size.y * 0.55, 1),
      Math.max(size.y * 2.2, 3)
    );

    controls.target.set(0, size.y * 0.48, 0);
    controls.update();

    const bones = [];
    avatar.traverse((obj) => {
      if (obj.isBone) bones.push(obj.name);
    });

    bonesOutput.textContent = bones.length
      ? bones.join("\n")
      : "No bones found";

    // Save the original pose for resetting before each sign.
    restPose.clear();

    avatar.traverse((obj) => {
      restPose.set(obj, {
        position: obj.position.clone(),
        quaternion: obj.quaternion.clone(),
        scale: obj.scale.clone()
      });
    });

    mixer = new THREE.AnimationMixer(avatar);

    status.textContent = `Avatar ready. ${bones.length} bones found.`;

    if (window.__signbridgePendingText) {
      const pending = window.__signbridgePendingText;
      window.__signbridgePendingText = null;

      const input = document.querySelector("#words");

      if (input) {
        input.value = pending;
        document.querySelector("#compile")?.click();
      }
    }

  } catch (err) {
    status.textContent = "Avatar loading failed: " + err.message;
    console.error(err);
  }
}

function convertSourceClip(source) {
  const tracks = source.tracks.map((track) => {
    const times = Float32Array.from(track.times);
    const values = Float32Array.from(track.values);

    if (track.type === "quaternion") {
      return new THREE.QuaternionKeyframeTrack(
        track.name,
        times,
        values
      );
    }

    if (track.type === "vector") {
      return new THREE.VectorKeyframeTrack(
        track.name,
        times,
        values
      );
    }

    if (track.type === "number") {
      return new THREE.NumberKeyframeTrack(
        track.name,
        times,
        values
      );
    }

    throw new Error(
      `Unsupported track type "${track.type}" in ${track.name}`
    );
  });

  return new THREE.AnimationClip(
    source.name || "ASL Signing",
    source.duration,
    tracks
  );
}

document.querySelector("#compile").addEventListener("click", () => {
  try {
    if (!avatar || !mixer) {
      resultOutput.textContent =
        "Wait for the avatar to finish loading.";
      return;
    }

    const text = document.querySelector("#words").value.trim();

    if (!text) {
      resultOutput.textContent = "Enter a sentence first.";
      return;
    }

    mixer.stopAllAction();
    signSegments = [];
    setLiveCaption("");


    if (clipAction) {
      mixer.uncacheAction(clipAction.getClip());
      clipAction = null;
    }

    // Restore the avatar's original pose.
    for (const [obj, pose] of restPose) {
      obj.position.copy(pose.position);
      obj.quaternion.copy(pose.quaternion);
      obj.scale.copy(pose.scale);
    }

    const output = compileUtterance(text, {
      signs: signLookup()
    });

    const source = convertSourceClip(output.clip);
    const retargeted = retargetClipToObject(source, avatar);

    if (!retargeted.clip) {
      resultOutput.textContent = JSON.stringify(
        {
          signed: output.signed,
          fingerspelled: output.spelled,
          coverage: retargeted.coverage,
          matched: retargeted.matched,
          total: retargeted.total,
          dropped: retargeted.dropped,
          note: "Retargeting did not meet the coverage threshold."
        },
        null,
        2
      );
      return;
    }

    clipAction = mixer.clipAction(retargeted.clip);

    signSegments = output.segments || [];

    clipAction.reset();
    clipAction.setEffectiveTimeScale(0.75);

    clipAction.setLoop(THREE.LoopOnce, 1);
    clipAction.clampWhenFinished = true;
    clipAction.play();

    resultOutput.textContent = JSON.stringify(
      {
        signed: output.signed,
        fingerspelled: output.spelled,
        durationSeconds: retargeted.clip.duration,
        coverage: retargeted.coverage,
        matched: retargeted.matched,
        total: retargeted.total,
        dropped: retargeted.dropped,
        note: "Retargeted animation started. Check the avatar's hands and arms."
      },
      null,
      2
    );
  } catch (err) {
    resultOutput.textContent = err.stack || err.message;
    console.error(err);
  }
});

// Allow the Streamlit Speech-to-ASL page to send typed or recognized speech.
window.addEventListener("message", (event) => {
  const data = event.data;
  if (!data || data.type !== "SIGNBRIDGE_TEXT" || typeof data.text !== "string") return;
  const input = document.querySelector("#words");
  if (!input) return;
  input.value = data.text;
  if (avatar && mixer) {
    document.querySelector("#compile")?.click();
  } else {
    window.__signbridgePendingText = data.text;
  }
});

const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);

  if (mixer) {
    mixer.update(clock.getDelta());
  }

  controls.update();
  updateLiveCaption();
  renderer.render(scene, camera);
}

function resizeViewer() {
  const width = viewer.clientWidth;
  const height = viewer.clientHeight;

  if (!width || !height) return;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

window.addEventListener("resize", resizeViewer);

if ("ResizeObserver" in window) {
  new ResizeObserver(resizeViewer).observe(viewer);
}

window.addEventListener("beforeunload", () => {
  disposeLanternStage?.();
});

animate();
loadAvatar();
