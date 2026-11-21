import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

const data = await readFile("./public/models/avatar.glb");
const url = pathToFileURL(process.cwd() + "/public/models/avatar.glb").href;
const loader = new GLTFLoader();
loader.setMeshoptDecoder(MeshoptDecoder);

loader.parse(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength), url, (gltf) => {
  let count = 0;
  gltf.scene.traverse((obj) => {
    if (obj.isBone) {
      console.log(obj.name);
      count++;
    }
  });
  console.log("Total bones:", count);
}, console.error);
