
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

export function applyLanternStage({
  renderer,
  scene,
  camera,
  avatar,
  options = {}
}) {
  if (!renderer || !scene || !camera || !avatar) {
    throw new Error("Lantern Stage: renderer, scene, camera, and avatar are required.");
  }

  const original = {
    background: scene.background,
    environment: scene.environment,
    toneMapping: renderer.toneMapping,
    exposure: renderer.toneMappingExposure,
    shadowMapEnabled: renderer.shadowMap.enabled,
    shadowMapType: renderer.shadowMap.type
  };

  const added = [];
  const originalMaterials = [];
  const originalMeshSettings = [];
  let environmentTarget = null;
  let disposed = false;

  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const world = new THREE.Group();
  world.name = "LanternStage";
  scene.add(world);
  added.push(world);

  const backgroundCanvas = document.createElement("canvas");
  backgroundCanvas.width = 2;
  backgroundCanvas.height = 256;

  const context = backgroundCanvas.getContext("2d");
  const gradient = context.createLinearGradient(0, 0, 0, 256);
  gradient.addColorStop(0, "#102c35");
  gradient.addColorStop(0.55, "#24454a");
  gradient.addColorStop(1, "#b87542");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 2, 256);

  const backgroundTexture = new THREE.CanvasTexture(backgroundCanvas);
  backgroundTexture.colorSpace = THREE.SRGBColorSpace;
  scene.background = backgroundTexture;
  added.push(backgroundTexture);

  try {
    const pmrem = new THREE.PMREMGenerator(renderer);
    environmentTarget = pmrem.fromScene(new RoomEnvironment(), 0.04);
    scene.environment = environmentTarget.texture;
    pmrem.dispose();
  } catch (error) {
    console.warn("Lantern Stage environment setup skipped:", error);
  }

  const bounds = new THREE.Box3().setFromObject(avatar);
  const size = bounds.getSize(new THREE.Vector3());
  const center = bounds.getCenter(new THREE.Vector3());
  const height = Math.max(size.y, 1);

  const floorY = bounds.min.y + 0.015;
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(200, 200),
    new THREE.MeshStandardMaterial({
      color: 0x24373a,
      roughness: 0.88,
      metalness: 0.02
    })
  );

  floor.rotation.x = -Math.PI / 2;
  floor.position.set(center.x, floorY, center.z);
  floor.receiveShadow = true;
  world.add(floor);

  const makeLight = (color, intensity, position, castShadow = false) => {
    const light = new THREE.DirectionalLight(color, intensity);
    light.position.set(...position);
    light.target.position.set(center.x, center.y, center.z);
    light.castShadow = castShadow;

    if (castShadow) {
      light.shadow.mapSize.set(1024, 1024);
      light.shadow.camera.near = 0.1;
      light.shadow.camera.far = height * 8;
      light.shadow.bias = -0.00015;
    }

    world.add(light, light.target);
    return light;
  };

  const key = makeLight(
    0xffe0bd,
    3.0,
    [center.x - height, center.y + height * 1.5, center.z + height * 1.8],
    true
  );

  makeLight(
    0x9bd9e5,
    2.0,
    [center.x + height, center.y + height, center.z - height]
  );

  makeLight(
    0xffad66,
    2.4,
    [center.x + height * 0.6, center.y + height * 0.7, center.z - height * 1.4]
  );

  const fill = new THREE.HemisphereLight(0xc5e9f4, 0x624533, 1.6);
  world.add(fill);

  avatar.traverse((object) => {
    if (!object.isMesh) return;

    originalMeshSettings.push({
      object,
      castShadow: object.castShadow,
      receiveShadow: object.receiveShadow,
      frustumCulled: object.frustumCulled
    });

    object.castShadow = true;
    object.receiveShadow = true;

    if (object.isSkinnedMesh) {
      object.frustumCulled = false;
    }

    const materials = Array.isArray(object.material)
      ? object.material
      : [object.material];

    for (const material of materials) {
      if (!material) continue;

      originalMaterials.push({
        material,
        roughness: material.roughness,
        metalness: material.metalness
      });

      if ("roughness" in material && !material.map) {
        material.roughness = Math.max(material.roughness ?? 0.5, 0.65);
      }

      if ("metalness" in material && !material.map) {
        material.metalness = Math.min(material.metalness ?? 0, 0.12);
      }

      if (material.map) {
        material.map.anisotropy = renderer.capabilities.getMaxAnisotropy();
      }
    }
  });

  return function disposeLanternStage() {
    if (disposed) return;
    disposed = true;

    scene.background = original.background;
    scene.environment = original.environment;
    renderer.toneMapping = original.toneMapping;
    renderer.toneMappingExposure = original.exposure;
    renderer.shadowMap.enabled = original.shadowMapEnabled;
    renderer.shadowMap.type = original.shadowMapType;

    for (const entry of originalMeshSettings) {
      entry.object.castShadow = entry.castShadow;
      entry.object.receiveShadow = entry.receiveShadow;
      entry.object.frustumCulled = entry.frustumCulled;
    }

    for (const entry of originalMaterials) {
      if (entry.roughness !== undefined) {
        entry.material.roughness = entry.roughness;
      }
      if (entry.metalness !== undefined) {
        entry.material.metalness = entry.metalness;
      }
    }

    for (const object of added) {
      if (object.parent) object.parent.remove(object);

      if (object.isTexture) object.dispose();

      if (object.isGroup) {
        object.traverse((child) => {
          child.geometry?.dispose();
          if (Array.isArray(child.material)) {
            child.material.forEach((material) => material.dispose());
          } else {
            child.material?.dispose();
          }
        });
      }
    }

    environmentTarget?.dispose();
  };
}
