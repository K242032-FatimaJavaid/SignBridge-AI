const fs = await import("node:fs/promises");
const file = "./src/main.js";
let s = await fs.readFile(file, "utf8");

s = s.replace(
  "let avatar, mixer, clipAction;",
  "let avatar, mixer, clipAction;\nlet restPose = new Map();"
);

s = s.replace(
  'bonesOutput.textContent = bones.length ? bones.join("\\n") : "No bones found";',
  'bonesOutput.textContent = bones.length ? bones.join("\\n") : "No bones found";\n    restPose.clear();\n    avatar.traverse((obj) => restPose.set(obj, { position: obj.position.clone(), quaternion: obj.quaternion.clone(), scale: obj.scale.clone() }));'
);

const old = `    const output = compileUtterance(text, { signs: signLookup() });
    const source = convertSourceClip(output.clip);
    const retargeted = retargetClipToObject(source, avatar);

    if (clipAction) {
      clipAction.stop();
      mixer.uncacheAction(clipAction.getClip());
      clipAction = null;
    }`;

const replacement = `    mixer.stopAllAction();
    if (clipAction) {
      mixer.uncacheAction(clipAction.getClip());
      clipAction = null;
    }

    for (const [obj, pose] of restPose) {
      obj.position.copy(pose.position);
      obj.quaternion.copy(pose.quaternion);
      obj.scale.copy(pose.scale);
    }

    const output = compileUtterance(text, { signs: signLookup() });
    const source = convertSourceClip(output.clip);
    const retargeted = retargetClipToObject(source, avatar);`;

if (!s.includes(old)) {
  console.error("Could not find the expected code section. No changes made.");
  process.exit(1);
}

s = s.replace(old, replacement);
await fs.writeFile(file, s, "utf8");
console.log("Updated successfully.");
