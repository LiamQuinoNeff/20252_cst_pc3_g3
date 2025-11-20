// Controles de órbita sencillos (sin dependencia externa)
class SimpleOrbitControls {
  constructor(camera, domElement) {
    this.camera = camera;
    this.domElement = domElement;
    this.target = new THREE.Vector3(0, 0, 0);

    const offset = new THREE.Vector3().subVectors(this.camera.position, this.target);
    this.spherical = new THREE.Spherical().setFromVector3(offset);

    this.rotateSpeed = 0.005;
    this.zoomScale = 0.95;
    this.minPolarAngle = 0.1;
    this.maxPolarAngle = Math.PI / 2.05;
    this.minRadius = 15;
    this.maxRadius = 140;

    this.state = null; // 'rotate'
    this.pointer = new THREE.Vector2();
    this.pointerOld = new THREE.Vector2();

    this._onPointerDown = this.onPointerDown.bind(this);
    this._onPointerMove = this.onPointerMove.bind(this);
    this._onPointerUp = this.onPointerUp.bind(this);
    this._onWheel = this.onWheel.bind(this);

    domElement.addEventListener('pointerdown', this._onPointerDown);
    domElement.addEventListener('wheel', this._onWheel, { passive: false });
  }

  dispose() {
    this.domElement.removeEventListener('pointerdown', this._onPointerDown);
    this.domElement.removeEventListener('wheel', this._onWheel);
    window.removeEventListener('pointermove', this._onPointerMove);
    window.removeEventListener('pointerup', this._onPointerUp);
  }

  onPointerDown(event) {
    event.preventDefault();
    this.state = 'rotate';
    this.pointerOld.set(event.clientX, event.clientY);
    window.addEventListener('pointermove', this._onPointerMove);
    window.addEventListener('pointerup', this._onPointerUp);
  }

  onPointerMove(event) {
    if (this.state === 'rotate') {
      event.preventDefault();
      this.pointer.set(event.clientX, event.clientY);
      const dx = this.pointer.x - this.pointerOld.x;
      const dy = this.pointer.y - this.pointerOld.y;

      this.spherical.theta -= dx * this.rotateSpeed;
      this.spherical.phi -= dy * this.rotateSpeed;

      this.spherical.phi = Math.max(this.minPolarAngle, Math.min(this.maxPolarAngle, this.spherical.phi));

      this.pointerOld.copy(this.pointer);
    }
  }

  onPointerUp(event) {
    event.preventDefault();
    this.state = null;
    window.removeEventListener('pointermove', this._onPointerMove);
    window.removeEventListener('pointerup', this._onPointerUp);
  }

  onWheel(event) {
    event.preventDefault();
    const delta = event.deltaY > 0 ? 1 / this.zoomScale : this.zoomScale;
    this.spherical.radius *= delta;
    this.spherical.radius = Math.max(this.minRadius, Math.min(this.maxRadius, this.spherical.radius));
  }

  update() {
    const offset = new THREE.Vector3().setFromSpherical(this.spherical);
    this.camera.position.copy(this.target).add(offset);
    this.camera.lookAt(this.target);
  }
}

let scene, camera, renderer, controls;
let groundPlane;
let starField;
let galaxyGroups = [];
const creatures = {}; // { jid: { mesh, data, target } }
let foodMeshes = [];
let worldSize = { w: 30, h: 30 };

const SCALE = 2; // escala mundo -> escena
let lastTime = performance.now();

function init() {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x00010a);
  scene.fog = new THREE.Fog(0x00010a, 80, 260);

  const container = document.getElementById('container');
  camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(45, 60, 45);
  camera.lookAt(0, 0, 0);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  controls = new SimpleOrbitControls(camera, renderer.domElement);

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.35);
  scene.add(ambientLight);

  const keyLight = new THREE.DirectionalLight(0xffffff, 0.9);
  keyLight.position.set(35, 70, 25);
  keyLight.castShadow = true;
  keyLight.shadow.camera.left = -60;
  keyLight.shadow.camera.right = 60;
  keyLight.shadow.camera.top = 60;
  keyLight.shadow.camera.bottom = -60;
  keyLight.shadow.mapSize.width = 2048;
  keyLight.shadow.mapSize.height = 2048;
  scene.add(keyLight);

  const rimLight = new THREE.DirectionalLight(0x7dd3fc, 0.45);
  rimLight.position.set(-40, 30, -20);
  scene.add(rimLight);

  const planeGeometry = new THREE.CircleGeometry(worldSize.w * SCALE * 0.75, 64);
  const planeMaterial = new THREE.MeshStandardMaterial({
    color: 0xfafafa,
    roughness: 0.85,
    metalness: 0.1,
  });
  groundPlane = new THREE.Mesh(planeGeometry, planeMaterial);
  groundPlane.rotation.x = -Math.PI / 2;
  groundPlane.receiveShadow = true;
  scene.add(groundPlane);

  const gridHelper = new THREE.GridHelper(worldSize.w * SCALE, 30, 0x94a3b8, 0xe5e7eb);
  gridHelper.position.y = 0.01;
  gridHelper.material.opacity = 0.22;
  gridHelper.material.transparent = true;
  scene.add(gridHelper);

  createStarField();
  createGalaxies();

  window.addEventListener('resize', onWindowResize, false);

  lastTime = performance.now();
  animate();
  fetchData();
  setInterval(fetchData, 250);
}

function createStarField() {
  const starCount = 1500;
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(starCount * 3);

  for (let i = 0; i < starCount; i++) {
    const radius = 170 + Math.random() * 160;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.random() * Math.PI;

    const x = radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.cos(phi) * 0.35 + 40;
    const z = radius * Math.sin(phi) * Math.sin(theta);

    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  const material = new THREE.PointsMaterial({
    color: 0xffffff,
    size: 0.9,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.85,
    depthWrite: false,
  });

  starField = new THREE.Points(geometry, material);
  starField.renderOrder = -2;
  scene.add(starField);
}

function createGalaxies() {
  galaxyGroups = [];

  const configs = [
    { center: new THREE.Vector3(-140, 70, -90), color: 0x4f46e5 },
    { center: new THREE.Vector3(150, 80, 70), color: 0x22d3ee },
  ];

  configs.forEach((cfg, idx) => {
    const count = 900;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const baseColor = new THREE.Color(cfg.color);

    for (let i = 0; i < count; i++) {
      const radius = Math.random() * 40;
      let angle = Math.random() * Math.PI * 2;
      const armOffset = (radius / 40) * 1.4;
      angle += armOffset * (idx === 0 ? 1 : -1);

      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = (Math.random() - 0.5) * 7;

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      colors[i * 3] = baseColor.r;
      colors[i * 3 + 1] = baseColor.g;
      colors[i * 3 + 2] = baseColor.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 1.3,
      sizeAttenuation: true,
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      depthWrite: false,
    });

    const galaxy = new THREE.Points(geometry, material);
    galaxy.position.copy(cfg.center);
    galaxy.renderOrder = -1;
    scene.add(galaxy);
    galaxyGroups.push(galaxy);
  });
}

function createCreatureBlob(data) {
  const color = getColorFromJID(data.jid);

  // geometría base tipo gota usando una esfera deformada
  const geometry = new THREE.SphereGeometry(1, 32, 32);
  const positionAttr = geometry.attributes.position;
  const v = new THREE.Vector3();

  for (let i = 0; i < positionAttr.count; i++) {
    v.fromBufferAttribute(positionAttr, i);
    // y en [-1, 1] -> normalizado [0, 1]
    const ny = (v.y + 1) / 2;
    // ensanchar parte baja y afinar parte alta
    const radiusScale = 0.8 + (1.4 - 0.8) * (1 - ny);
    v.x *= radiusScale;
    v.z *= radiusScale;
    // estirar ligeramente en vertical
    v.y *= 1.3;
    positionAttr.setXYZ(i, v.x, v.y, v.z);
  }
  positionAttr.needsUpdate = true;
  geometry.computeVertexNormals();

  const material = new THREE.MeshStandardMaterial({
    color: color,
    roughness: 0.35,
    metalness: 0.05,
    emissive: color,
    emissiveIntensity: 0.18,
  });

  const mesh = new THREE.Mesh(geometry, material);

  // ojitos negros
  const eyeGeometry = new THREE.SphereGeometry(0.08, 12, 12);
  const eyeMaterial = new THREE.MeshStandardMaterial({
    color: 0x000000,
    roughness: 0.4,
    metalness: 0.0,
  });

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);

  const eyeOffsetY = 0.35;
  const eyeOffsetZ = 0.85;
  const eyeOffsetX = 0.22;

  leftEye.position.set(-eyeOffsetX, eyeOffsetY, eyeOffsetZ);
  rightEye.position.set(eyeOffsetX, eyeOffsetY, eyeOffsetZ);

  mesh.add(leftEye);
  mesh.add(rightEye);

  const size = Math.max(0.3, data.size || 1) * 1.4;
  mesh.scale.set(size, size * 1.5, size);

  const pos = worldToScene(data.x, data.y);
  const y = size * 1.2;
  mesh.position.set(pos.x, y, pos.z);

  mesh.castShadow = true;
  mesh.receiveShadow = true;

  return mesh;
}


function createFoodBall(x, y) {
  const geometry = new THREE.SphereGeometry(0.35, 10, 10);
  const material = new THREE.MeshStandardMaterial({
    color: 0x22c55e,
    roughness: 0.4,
    metalness: 0.2,
    emissive: 0x22c55e,
    emissiveIntensity: 0.5,
  });

  const mesh = new THREE.Mesh(geometry, material);
  const pos = worldToScene(x, y);
  mesh.position.set(pos.x, 0.35, pos.z);
  mesh.castShadow = true;

  return mesh;
}

function worldToScene(wx, wy) {
  return {
    x: (wx - worldSize.w / 2) * SCALE,
    z: (wy - worldSize.h / 2) * SCALE,
  };
}

function getColorFromJID(jid) {
  let hash = 0;
  for (let i = 0; i < jid.length; i++) {
    hash = jid.charCodeAt(i) + ((hash << 5) - hash);
  }

  const colors = [
    0x4ade80,
    0x60a5fa,
    0xa78bfa,
    0xfbbf24,
    0xf472b6,
    0x22c55e,
    0x818cf8,
    0xf97316,
  ];

  return colors[Math.abs(hash) % colors.length];
}

async function fetchData() {
  try {
    const response = await fetch('/fishes');
    const data = await response.json();

    document.getElementById('creatures').textContent = data.fishes.length;
    document.getElementById('food').textContent = data.foods.length;

    if (data.space_size) {
      worldSize.w = data.space_size[0];
      worldSize.h = data.space_size[1];
    }

    updateCreatures(data.fishes);
    updateFood(data.foods);
    if (data.removals) {
      handleRemovals(data.removals);
    }
  } catch (err) {
    console.error('Error fetching /fishes:', err);
  }
}

function updateCreatures(fishesData) {
  const currentJIDs = new Set(fishesData.map((f) => f.jid));

  for (const jid in creatures) {
    if (currentJIDs.has(jid) === false) {
      scene.remove(creatures[jid].mesh);
      delete creatures[jid];
    }
  }

  fishesData.forEach((fish) => {
    const pos = worldToScene(fish.x, fish.y);
    const size = Math.max(0.3, fish.size || 1) * 1.4;
    const y = size * 1.2;

    if (creatures[fish.jid] == null) {
      const mesh = createCreatureBlob(fish);
      mesh.position.set(pos.x, y, pos.z);
      scene.add(mesh);
      creatures[fish.jid] = {
        mesh,
        data: fish,
        target: new THREE.Vector3(pos.x, y, pos.z),
      };
    } else {
      const entry = creatures[fish.jid];
      const mesh = entry.mesh;

      mesh.scale.set(size, size * 1.5, size);
      mesh.position.y = y;
      entry.target.set(pos.x, y, pos.z);

      const energyNorm = Math.max(0, Math.min(1, fish.energy / 10));
      mesh.material.emissiveIntensity = 0.15 + energyNorm * 0.2;

      entry.data = fish;
    }
  });
}

function updateFood(foodsData) {
  foodMeshes.forEach((m) => scene.remove(m));
  foodMeshes = [];

  foodsData.forEach(([x, y]) => {
    const mesh = createFoodBall(x, y);
    scene.add(mesh);
    foodMeshes.push(mesh);
  });
}

function handleRemovals(removals) {
  removals.forEach((removal) => {
    const entry = creatures[removal.jid];
    if (entry == null) return;

    const mesh = entry.mesh;
    let progress = 0;
    const startScale = mesh.scale.clone();
    const startY = mesh.position.y;
    const startTime = performance.now();
    const duration = 450;

    function step(t) {
      progress = Math.min(1, (t - startTime) / duration);
      const s = 1 - progress * 0.5;
      mesh.scale.set(startScale.x * s, startScale.y * s, startScale.z * s);
      mesh.position.y = startY + progress * 2.5;
      mesh.material.transparent = true;
      mesh.material.opacity = 1 - progress;

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        scene.remove(mesh);
        delete creatures[removal.jid];
      }
    }

    requestAnimationFrame(step);
  });
}

function animate() {
  requestAnimationFrame(animate);

  const now = performance.now();
  const dt = (now - lastTime) / 1000;
  lastTime = now;

  const time = now * 0.001;

  if (starField) {
    starField.rotation.y += 0.0004;
  }

  if (Array.isArray(galaxyGroups)) {
    galaxyGroups.forEach((g, idx) => {
      if (g == null) return;
      g.rotation.y += idx === 0 ? 0.00025 : -0.0002;
    });
  }

  const moveSpeed = 6;
  const smoothing = 1 - Math.exp(-moveSpeed * dt);

  for (const jid in creatures) {
    const entry = creatures[jid];
    const mesh = entry.mesh;
    const target = entry.target;

    if (target) {
      mesh.position.lerp(target, smoothing);
    }

    mesh.rotation.y = Math.sin(time + mesh.position.x * 0.05) * 0.2;
    mesh.position.y += Math.sin(time * 3 + mesh.position.x) * 0.0025;
  }

  foodMeshes.forEach((mesh, i) => {
    mesh.position.y = 0.35 + Math.sin(time * 4 + i * 0.7) * 0.06;
  });

  controls.update();
  renderer.render(scene, camera);
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

window.addEventListener('DOMContentLoaded', init);
