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
let asteroidBelts = [];
let comets = [];
const tempDir = new THREE.Vector3();
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const creatures = {}; // { jid: { mesh, data, target } }
let foodMeshes = [];
let worldSize = { w: 30, h: 30 };
let timeScale = 1.0;
let simTime = 0;
let realTime = 0;
let currentGeneration = 0;
// Bloqueo visual de movimiento al inicio de cada generación
let movementLockedVisual = false;
let lastGenForLock = null;
let lastCreatureCount = 0;
let lastCreatureCountChangeTime = 0;
let selectedCreatureJid = null;
let selectionOutline = null;
let selectionOutlineParent = null;
let fetchIntervalId = null; // Para controlar el intervalo de polling dinámicamente
let bloodStains = []; // Array para trackear manchas de sangre y limpiarlas


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

  // Selección de blobs con click en la escena
  renderer.domElement.addEventListener('click', onSceneClick);

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

  const platformSize = worldSize.w * SCALE * 1.05;
  const cornerRadius = platformSize * 0.07;

  function createRoundedRectShape(width, height, radius) {
    const shape = new THREE.Shape();
    const x = -width / 2;
    const y = -height / 2;

    shape.moveTo(x + radius, y);
    shape.lineTo(x + width - radius, y);
    shape.quadraticCurveTo(x + width, y, x + width, y + radius);
    shape.lineTo(x + width, y + height - radius);
    shape.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    shape.lineTo(x + radius, y + height);
    shape.quadraticCurveTo(x, y + height, x, y + height - radius);
    shape.lineTo(x, y + radius);
    shape.quadraticCurveTo(x, y, x + radius, y);

    return shape;
  }

  const platformShape = createRoundedRectShape(platformSize, platformSize, cornerRadius);
  const planeGeometry = new THREE.ShapeGeometry(platformShape);
  const planeMaterial = new THREE.MeshStandardMaterial({
    color: 0xfafafa,
    roughness: 0.85,
    metalness: 0.1,
  });
  groundPlane = new THREE.Mesh(planeGeometry, planeMaterial);
  groundPlane.rotation.x = -Math.PI / 2;
  groundPlane.receiveShadow = true;
  scene.add(groundPlane);


  createStarField();
  createGalaxies();
  createAsteroidBelts();
  createComets();

  window.addEventListener('resize', onWindowResize, false);

  lastTime = performance.now();
  animate();
  fetchData();
  startDynamicPolling();
}

function startDynamicPolling() {
  // Detener polling anterior si existe
  if (fetchIntervalId) {
    clearInterval(fetchIntervalId);
  }
  
  // Calcular intervalo basado en timeScale:
  // A mayor velocidad, polling más frecuente para mantener sincronía
  // 1x = 250ms, 1.5x = 167ms, 2x = 125ms
  const baseInterval = 250; // ms
  const interval = Math.max(100, baseInterval / timeScale); // Mínimo 100ms
  
  fetchIntervalId = setInterval(fetchData, interval);
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
    // Espiral azulada tipo Vía Láctea
    {
      center: new THREE.Vector3(-110, 90, -140),
      innerColor: 0xfff7c2,
      outerColor: 0x60a5fa,
      radius: 95,
      arms: 4,
      twist: 2.6,
      verticalScatter: 6,
    },
    // Galaxia morada
    {
      center: new THREE.Vector3(130, 95, -110),
      innerColor: 0xf9fafb,
      outerColor: 0xa855f7,
      radius: 80,
      arms: 3,
      twist: -2.1,
      verticalScatter: 5,
    },
    // Galaxia anaranjada más pequeña
    {
      center: new THREE.Vector3(-60, 40, -160),
      innerColor: 0xfff7c2,
      outerColor: 0xf97316,
      radius: 55,
      arms: 2,
      twist: 1.7,
      verticalScatter: 4,
    },
    // Galaxia lejana casi de canto
    {
      center: new THREE.Vector3(0, 60, -200),
      innerColor: 0xe5e7eb,
      outerColor: 0x22d3ee,
      radius: 70,
      arms: 2,
      twist: 3.0,
      verticalScatter: 12,
    },
  ];

  configs.forEach((cfg) => {
    const count = 2600;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    const inner = new THREE.Color(cfg.innerColor);
    const outer = new THREE.Color(cfg.outerColor);

    for (let i = 0; i < count; i++) {
      const rNorm = Math.pow(Math.random(), 0.4); // más denso en el núcleo
      const radius = rNorm * cfg.radius;

      const armIndex = Math.floor(Math.random() * cfg.arms);
      const armAngle = (armIndex / cfg.arms) * Math.PI * 2;

      const twistAngle = (radius / cfg.radius) * cfg.twist * Math.PI;
      const jitter = (Math.random() - 0.5) * 0.4;
      const angle = armAngle + twistAngle + jitter;

      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = (Math.random() - 0.5) * cfg.verticalScatter * (1.0 - rNorm * 0.6);

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      const c = inner.clone().lerp(outer, rNorm);
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 1.2,
      sizeAttenuation: true,
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    const galaxy = new THREE.Points(geometry, material);
    galaxy.position.copy(cfg.center);
    galaxy.renderOrder = -1;
    scene.add(galaxy);
    galaxyGroups.push(galaxy);
  });
}

function createAsteroidBelts() {
  asteroidBelts = [];

  const beltConfigs = [
    { center: new THREE.Vector3(0, -10, -110), innerRadius: 60, outerRadius: 100, density: 650 },
    { center: new THREE.Vector3(-90, -5, -40), innerRadius: 35, outerRadius: 65, density: 380 },
  ];

  beltConfigs.forEach((cfg) => {
    const geometry = new THREE.BufferGeometry();
    const count = cfg.density;
    const positions = new Float32Array(count * 3);
    const sizes = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      const radius = cfg.innerRadius + Math.random() * (cfg.outerRadius - cfg.innerRadius);
      const angle = Math.random() * Math.PI * 2;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = (Math.random() - 0.5) * 4;

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      sizes[i] = 0.4 + Math.random() * 0.6;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
      size: 1.0,
      sizeAttenuation: true,
      color: 0x9ca3af,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
    });

    const belt = new THREE.Points(geometry, material);
    belt.position.copy(cfg.center);
    belt.renderOrder = -1;
    scene.add(belt);
    asteroidBelts.push({ points: belt, cfg });
  });
}

function createComets() {
  comets = [];

  const cometConfigs = [
    {
      color: 0xf9fafb,
      tailColor: 0x93c5fd,
      orbitRadius: 180,
      height: 90,
      speed: 0.03,
      phase: 0.0,
    },
    {
      color: 0xfef3c7,
      tailColor: 0xf97316,
      orbitRadius: 150,
      height: 70,
      speed: -0.02,
      phase: Math.PI,
    },
  ];

  cometConfigs.forEach((cfg) => {
    const geom = new THREE.SphereGeometry(1.5, 12, 12);
    const mat = new THREE.MeshBasicMaterial({
      color: cfg.color,
      transparent: true,
      opacity: 1.0,
    });
    const head = new THREE.Mesh(geom, mat);

    const tailGeom = new THREE.BufferGeometry();
    const tailCount = 40;
    const tailPositions = new Float32Array(tailCount * 3);
    tailGeom.setAttribute('position', new THREE.BufferAttribute(tailPositions, 3));
    const tailMat = new THREE.PointsMaterial({
      size: 1.4,
      color: cfg.tailColor,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    const tail = new THREE.Points(tailGeom, tailMat);

    scene.add(head);
    scene.add(tail);

    comets.push({ cfg, head, tail, tailPositions, tailCount });
  });
}



function createCreatureBlob(data) {
  const speed = data.speed || 1.0;
  const color = getColorFromSpeed(speed);

  // Geometría base: esfera suave con base plana, tipo gelatina redondita
  const geometry = new THREE.SphereGeometry(1, 48, 48);
  const positionAttr = geometry.attributes.position;
  const v = new THREE.Vector3();

  for (let i = 0; i < positionAttr.count; i++) {
    v.fromBufferAttribute(positionAttr, i);

    // Aplanar ligeramente la parte inferior para que apoye bien en la plataforma
    if (v.y < 0.0) {
      v.y = 0.0;
    }

    // Suavizar el perfil (más redondito, sin picos)
    const r = Math.sqrt(v.x * v.x + v.z * v.z + v.y * v.y);
    if (r > 0) {
      const t = Math.min(r, 1.0);
      const smooth = 0.8 + 0.2 * t; // acercar un poco hacia el centro
      v.x *= smooth;
      v.z *= smooth;
    }

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

  const eyeOffsetY = 0.25;
  const eyeOffsetZ = 0.9;
  const eyeOffsetX = 0.22;

  leftEye.position.set(-eyeOffsetX, eyeOffsetY, eyeOffsetZ);
  rightEye.position.set(eyeOffsetX, eyeOffsetY, eyeOffsetZ);

  mesh.add(leftEye);
  mesh.add(rightEye);

  const size = Math.max(0.3, data.size || 1) * 1.2;
  const radiusX = size * 0.85;
  const radiusZ = size * 1.25;
  mesh.scale.set(radiusX, size, radiusZ);

  const pos = worldToScene(data.x, data.y);
  const baseY = 0.05;
  mesh.position.set(pos.x, baseY, pos.z);

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


function getColorFromSpeed(speed) {
  // Default speed = 1.0 -> cyan
  // Faster -> amarillo/rojo, más lento -> azul/morado
  const defaultSpeed = 1.0;
  const minSpeed = 0.3;
  const maxSpeed = 2.5;

  // paleta de 11 tonos de más lento a más rápido
  const palette = [
    0x382d24,
    0x4c230e,
    0x59392a,
    0x7d4f37,
    0x90654a,
    0xac7b50,
    0xcba17d,
    0xefcc9d,
    0xf5beb5,
    0xfcd4d6,
    0xf8ebeb,
  ];

  const s = typeof speed === 'number' && Number.isFinite(speed) ? speed : defaultSpeed;
  const clamped = Math.max(minSpeed, Math.min(maxSpeed, s));
  const t = (clamped - minSpeed) / (maxSpeed - minSpeed); // 0..1

  const idx = t * (palette.length - 1);
  const i0 = Math.floor(idx);
  const i1 = Math.min(palette.length - 1, i0 + 1);
  const localT = idx - i0;

  if (i0 === i1) {
    return palette[i0];
  }

  return lerpColor(palette[i0], palette[i1], localT);
}

function lerpColor(color1, color2, t) {
  const r1 = (color1 >> 16) & 0xff;
  const g1 = (color1 >> 8) & 0xff;
  const b1 = color1 & 0xff;

  const r2 = (color2 >> 16) & 0xff;
  const g2 = (color2 >> 8) & 0xff;
  const b2 = color2 & 0xff;

  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);

  return (r << 16) | (g << 8) | b;
}

function updateVelocityChart() {
  const speeds = [];
  for (const jid in creatures) {
    const entry = creatures[jid];
    if (entry.data && entry.data.speed != null) {
      speeds.push(entry.data.speed);
    }
  }
  
  if (speeds.length === 0) return;
  
  // Create histogram bins
  const minSpeed = 0.3;
  const maxSpeed = 2.5;
  const binCount = 11;
  const binSize = (maxSpeed - minSpeed) / binCount;
  const bins = new Array(binCount).fill(0);
  
  speeds.forEach(speed => {
    const binIndex = Math.floor((speed - minSpeed) / binSize);
    const clampedIndex = Math.max(0, Math.min(binCount - 1, binIndex));
    bins[clampedIndex]++;
  });
  
  const maxCount = Math.max(...bins, 1);
  
  // Update chart bars
  const container = document.getElementById('velocity-chart-bars');
  if (container == null) return;
  
  // asegurar que reutilizamos barras existentes para evitar parpadeos al hacer hover
  while (container.children.length < binCount) {
    const bar = document.createElement('div');
    bar.className = 'chart-bar';
    container.appendChild(bar);
  }
  while (container.children.length > binCount) {
    container.removeChild(container.lastChild);
  }

  bins.forEach((count, i) => {
    const binSpeed = minSpeed + i * binSize + binSize / 2;
    const height = (count / maxCount) * 100;
    const color = speedToColorHex(binSpeed);

    const bar = container.children[i];
    if (!bar) return;

    bar.style.height = height + '%';
    bar.style.backgroundColor = color;
    bar.title = `Speed ${binSpeed.toFixed(2)}: ${count} blobs`;
  });
}

function speedToColorHex(speed) {
  // Reutiliza el mismo mapa de color que los blobs para que el gráfico coincida
  const colorInt = getColorFromSpeed(speed);
  return '#' + colorInt.toString(16).padStart(6, '0');
}

async function fetchData() {
  try {
    const response = await fetch('/fishes');
    const data = await response.json();

    const creatureCount = data.fishes.length;
    document.getElementById('creatures').textContent = creatureCount;
    document.getElementById('food').textContent = data.foods.length;
    if (data.generation != null) {
      document.getElementById('gen').textContent = data.generation;
      // detectar cambio de generación para activar el bloqueo visual
      if (lastGenForLock === null || data.generation !== lastGenForLock) {
        lastGenForLock = data.generation;
        movementLockedVisual = true;
        lastCreatureCount = 0;
        lastCreatureCountChangeTime = performance.now();
        
        // Limpiar todas las manchas de sangre de la generación anterior
        cleanupBloodStains();
      }
      currentGeneration = data.generation;
    }

    if (data.space_size) {
      worldSize.w = data.space_size[0];
      worldSize.h = data.space_size[1];
    }

    // lógica para detectar cuándo han aparecido "todos" los blobs de la generación:
    // mientras el número de criaturas siga aumentando, seguimos bloqueando; cuando
    // el conteo se estabiliza durante unos 500 ms, liberamos el movimiento visual.
    const now = performance.now();
    if (creatureCount !== lastCreatureCount) {
      lastCreatureCount = creatureCount;
      lastCreatureCountChangeTime = now;
    } else {
      if (movementLockedVisual && (now - lastCreatureCountChangeTime) > 500) {
        movementLockedVisual = false;
      }
    }

    if (data.removals) {
      handleRemovals(data.removals);
    }

    updateCreatures(data.fishes);
    updateFood(data.foods);
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
    const baseY = 0.05;

    if (creatures[fish.jid] == null) {
      const mesh = createCreatureBlob(fish);
      mesh.position.set(pos.x, baseY, pos.z);
      mesh.userData = mesh.userData || {};
      mesh.userData.jid = fish.jid;
      scene.add(mesh);
      const bobPhase = Math.random() * Math.PI * 2;
      const breathPhase = Math.random() * Math.PI * 2;
      creatures[fish.jid] = {
        mesh,
        data: fish,
        target: new THREE.Vector3(pos.x, baseY, pos.z),
        heading: mesh.rotation.y || 0,
        bobPhase,
        breathPhase,
        baseSize: size,
      };
    } else {
      const entry = creatures[fish.jid];
      const mesh = entry.mesh;
      mesh.userData = mesh.userData || {};
      mesh.userData.jid = fish.jid;

      mesh.scale.set(size, size, size);
      mesh.position.y = baseY;
      if (!entry.target) {
        entry.target = new THREE.Vector3(pos.x, baseY, pos.z);
      } else {
        entry.target.set(pos.x, baseY, pos.z);
      }

      if (typeof entry.bobPhase !== 'number') {
        entry.bobPhase = Math.random() * Math.PI * 2;
      }
      if (typeof entry.breathPhase !== 'number') {
        entry.breathPhase = Math.random() * Math.PI * 2;
      }
      if (typeof entry.heading !== 'number') {
        entry.heading = mesh.rotation.y || 0;
      }

      entry.baseSize = size;

      const energyNorm = Math.max(0, Math.min(1, fish.energy / 10));
      mesh.material.emissiveIntensity = 0.15 + energyNorm * 0.2;

      // Actualizar datos primero
      entry.data = fish;
      
      // DESPUÉS actualizar panel si está seleccionado (para reflejar kills actualizados)
      if (selectedCreatureJid === fish.jid) {
        updateSelectedBlobPanel(entry);
      }
    }
  });
  
  // actualizar panel y contorno si hay un blob seleccionado
  if (selectedCreatureJid && creatures[selectedCreatureJid]) {
    const entry = creatures[selectedCreatureJid];
    updateSelectedBlobPanel(entry);
    updateSelectionOutline(entry);
  } else if (selectedCreatureJid) {
    selectedCreatureJid = null;
    updateSelectedBlobPanel(null);
    updateSelectionOutline(null);
  }

  updateVelocityChart();
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

function updateSelectionOutline(entry) {
  // Eliminar contorno previo si existe
  if (selectionOutline && selectionOutlineParent) {
    selectionOutlineParent.remove(selectionOutline);
    if (selectionOutline.geometry) selectionOutline.geometry.dispose();
    if (selectionOutline.material) selectionOutline.material.dispose();
  }
  selectionOutline = null;
  selectionOutlineParent = null;

  if (!entry || !entry.mesh) return;

  const baseMesh = entry.mesh;
  const outlineGeom = baseMesh.geometry.clone();
  const outlineMat = new THREE.MeshBasicMaterial({
    color: 0xfacc15, // dorado intenso
    transparent: true,
    opacity: 0.9,
    depthWrite: false,
    depthTest: true,
    side: THREE.BackSide,
    blending: THREE.AdditiveBlending,
  });

  const outline = new THREE.Mesh(outlineGeom, outlineMat);
  const scaleFactor = 1.08;
  outline.scale.set(scaleFactor, scaleFactor, scaleFactor);

  baseMesh.add(outline);
  selectionOutline = outline;
  selectionOutlineParent = baseMesh;
}

function updateSelectedBlobPanel(entry) {
  const noneEl = document.getElementById('blob-none');
  const statsEl = document.getElementById('blob-stats');
  if (!noneEl || !statsEl) return;

  if (!entry || !entry.data) {
    noneEl.style.display = '';
    statsEl.style.display = 'none';
    return;
  }

  noneEl.style.display = 'none';
  statsEl.style.display = 'block';

  const d = entry.data;

  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  setText('blob-id', d.jid || '-');
  setText('blob-gen', currentGeneration != null ? currentGeneration : '-');
  setText('blob-speed', d.speed != null ? d.speed.toFixed(2) : '-');
  setText('blob-energy', d.energy != null ? d.energy.toFixed(2) : '-');
  setText('blob-size', d.size != null ? d.size.toFixed(2) : '-');
  setText('blob-sense', d.sense != null ? d.sense.toFixed(2) : '-');
  setText('blob-foods', d.foods_eaten != null ? d.foods_eaten : '-');
  setText('blob-kills', d.kills != null ? d.kills : 0);
}

function onSceneClick(event) {
  if (!renderer || !camera) return;

  const rect = renderer.domElement.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  mouse.set(x, y);
  raycaster.setFromCamera(mouse, camera);

  const meshes = [];
  for (const jid in creatures) {
    const entry = creatures[jid];
    if (entry && entry.mesh) {
      meshes.push(entry.mesh);
    }
  }
  if (!meshes.length) {
    selectedCreatureJid = null;
    updateSelectedBlobPanel(null);
    updateSelectionOutline(null);
    return;
  }

  const intersects = raycaster.intersectObjects(meshes, true);
  if (!intersects.length) {
    selectedCreatureJid = null;
    updateSelectedBlobPanel(null);
    updateSelectionOutline(null);
    return;
  }

  let obj = intersects[0].object;
  let targetJid = null;
  while (obj && !targetJid) {
    if (obj.userData && obj.userData.jid) {
      targetJid = obj.userData.jid;
      break;
    }
    obj = obj.parent;
  }

  if (targetJid && creatures[targetJid]) {
    selectedCreatureJid = targetJid;
    const entry = creatures[targetJid];
    updateSelectedBlobPanel(entry);
    updateSelectionOutline(entry);
  } else {
    selectedCreatureJid = null;
    updateSelectedBlobPanel(null);
    updateSelectionOutline(null);
  }
}

function handleRemovals(removals) {
  removals.forEach((removal) => {
    const entry = creatures[removal.jid];
    if (entry == null) return;

    const mesh = entry.mesh;
    const reason = removal.reason || 'finished';
    const killedBy = removal.killed_by || null;
    
    // Solo las criaturas satisfechas desaparecen sin sangre
    if (reason === 'finished') {
      playFadeOut(mesh, removal.jid);
    } else {
      // Todas las demás muertes (killed, exhausted, etc.) con sangre
      const isPredation = reason === 'killed' || !!killedBy;
      playBloodDeath(mesh, removal.jid, isPredation);
    }
  });
}

function cleanupBloodStains() {
  // Eliminar todas las manchas de sangre de la escena
  bloodStains.forEach((stain) => {
    if (stain && stain.parent) {
      scene.remove(stain);
      if (stain.geometry) stain.geometry.dispose();
      if (stain.material) stain.material.dispose();
    }
  });
  bloodStains = [];
}

function playFadeOut(mesh, jid) {
  // Animación simple de desvanecimiento sin efectos de sangre
  const startScale = mesh.scale.clone();
  const startTime = performance.now();
  const duration = 400; // Desvanecimiento rápido y limpio

  function step(t) {
    const progress = Math.min(1, (t - startTime) / duration);
    const ease = progress; // Lineal

    // Reducir tamaño y opacidad
    const scale = 1 - progress * 0.5; // Reducir a 50%
    mesh.scale.set(
      startScale.x * scale,
      startScale.y * scale,
      startScale.z * scale,
    );

    if (mesh.material) {
      mesh.material.transparent = true;
      mesh.material.opacity = 1 - progress;
    }

    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      scene.remove(mesh);
      delete creatures[jid];
    }
  }

  requestAnimationFrame(step);
}

function playBloodDeath(mesh, jid, isPredation) {
  const center = mesh.position.clone();
  const startScale = mesh.scale.clone();
  const startTime = performance.now();
  const duration = isPredation ? 750 : 580;

  // Spray de sangre muy denso alrededor del blob (modo DOOM)
  const count = isPredation ? 220 : 120;
  const positions = new Float32Array(count * 3);
  const offsets = new Float32Array(count * 3);

  for (let i = 0; i < count; i++) {
    const i3 = i * 3;
    const angle = Math.random() * Math.PI * 2;
    const radiusBase = isPredation ? 0.7 : 0.5;
    const radiusVar = isPredation ? 0.9 : 0.5;
    const radius = radiusBase + Math.random() * radiusVar;
    const up = 0.2 + Math.random() * 0.4;

    offsets[i3] = Math.cos(angle) * radius;
    offsets[i3 + 1] = up;
    offsets[i3 + 2] = Math.sin(angle) * radius;

    positions[i3] = center.x;
    positions[i3 + 1] = center.y;
    positions[i3 + 2] = center.z;
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    color: 0xff0000,
    size: isPredation ? 0.9 : 0.6,
    sizeAttenuation: true,
    transparent: true,
    opacity: 1.0,
    depthWrite: false,
    depthTest: false,
    blending: THREE.AdditiveBlending,
  });
  const spray = new THREE.Points(geo, mat);
  scene.add(spray);

  // Mancha de sangre en el suelo que queda visible
  const stainRadius = isPredation ? 1.6 : 1.1;
  const stainGeom = new THREE.CircleGeometry(stainRadius, 40);
  const stainMat = new THREE.MeshBasicMaterial({
    color: 0x7f1d1d,
    transparent: true,
    opacity: 1.0,
  });
  const stain = new THREE.Mesh(stainGeom, stainMat);
  stain.rotation.x = -Math.PI / 2;
  stain.position.set(center.x, 0.02, center.z);
  stain.renderOrder = 0.5;
  scene.add(stain);
  
  // Guardar referencia para limpiar después
  bloodStains.push(stain);

  // Trozos (gibs) que salen disparados
  const gibGeom = new THREE.SphereGeometry(0.16, 10, 10);
  const gibMat = new THREE.MeshBasicMaterial({ color: 0x991b1b });
  const gibs = [];
  const gibVels = [];
  const gibCount = isPredation ? 8 : 4;
  for (let i = 0; i < gibCount; i++) {
    const gib = new THREE.Mesh(gibGeom, gibMat);
    gib.position.copy(center);
    scene.add(gib);
    gibs.push(gib);

    const a = Math.random() * Math.PI * 2;
    const r = 0.5 + Math.random() * 0.6;
    const vy = 0.6 + Math.random() * 0.6;
    gibVels.push(new THREE.Vector3(Math.cos(a) * r, vy, Math.sin(a) * r));
  }

  if (mesh.material) {
    mesh.material.emissive = new THREE.Color(0x991b1b);
    mesh.material.emissiveIntensity = 1.0;
  }

  function step(t) {
    const progress = Math.min(1, (t - startTime) / duration);
    const ease = 1 - Math.pow(1 - progress, 2);

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const fall = Math.max(0, (progress - 0.3) * 2.0);
      positions[i3] = center.x + offsets[i3] * ease;
      positions[i3 + 1] = center.y + offsets[i3 + 1] * (1 - fall) - fall * 0.6;
      positions[i3 + 2] = center.z + offsets[i3 + 2] * ease;
    }
    geo.attributes.position.needsUpdate = true;

    // Actualizar gibs con una gravedad simple
    for (let i = 0; i < gibs.length; i++) {
      const gib = gibs[i];
      const v = gibVels[i];
      v.y -= 0.05; // gravedad
      gib.position.add(v.clone().multiplyScalar(0.06));
    }

    const bodyShrink = 1 - progress * 0.7;
    mesh.scale.set(
      startScale.x * bodyShrink,
      startScale.y * bodyShrink,
      startScale.z * bodyShrink,
    );

    if (mesh.material) {
      mesh.material.transparent = true;
      mesh.material.opacity = 1 - progress;
    }

    // La mancha se atenúa un poco pero sigue visible
    stainMat.opacity = 1.0 * (1 - progress * 0.35);

    mat.opacity = 1.0 * (1 - progress);

    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      scene.remove(mesh);
      scene.remove(spray);
      geo.dispose();
      mat.dispose();
      // dejar gibs y la mancha un ratito en el suelo
      setTimeout(() => {
        gibs.forEach((g) => scene.remove(g));
      }, 2500);
      delete creatures[jid];
    }
  }

  requestAnimationFrame(step);
}


function setupTimeControls() {
  const slow = document.getElementById('time-slow');    // 0.25x
  const half = document.getElementById('time-half');    // 0.5x
  const normal = document.getElementById('time-normal'); // 1x
  const fast = document.getElementById('time-fast');    // 1.5x
  const max = document.getElementById('time-max');      // 2x

  const buttons = [slow, half, normal, fast, max];

  async function setScale(scale, activeBtn) {
    // Actualizar el timeScale local para la animación visual
    timeScale = scale;
    
    // Reiniciar el polling dinámico con el nuevo intervalo
    startDynamicPolling();
    
    // Llamar al backend para sincronizar la velocidad de simulación
    try {
      await fetch('/set_speed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed: scale }),
      });
    } catch (err) {
      console.error('Error setting speed:', err);
    }
    
    // Actualizar UI
    buttons.forEach((btn) => {
      if (btn) {
        btn.classList.toggle('time-btn--active', btn === activeBtn);
      }
    });
  }

  if (slow) slow.addEventListener('click', () => setScale(0.25, slow));
  if (half) half.addEventListener('click', () => setScale(0.5, half));
  if (normal) normal.addEventListener('click', () => setScale(1.0, normal));
  if (fast) fast.addEventListener('click', () => setScale(1.5, fast));
  if (max) max.addEventListener('click', () => setScale(2.0, max));

  // estado inicial: 1x
  setScale(1.0, normal);
}



function animate() {
  requestAnimationFrame(animate);

  const now = performance.now();
  const dtRaw = (now - lastTime) / 1000;
  lastTime = now;

  realTime += dtRaw;

  const dt = dtRaw * timeScale;
  simTime += dt;
  const time = simTime;

  const simLabel = document.getElementById('simtime');
  const realLabel = document.getElementById('realtime');
  if (simLabel) simLabel.textContent = simTime.toFixed(1) + ' s';
  if (realLabel) realLabel.textContent = realTime.toFixed(1) + ' s';

  if (starField) {
    starField.rotation.y += 0.0004 * timeScale;
  }

  if (Array.isArray(galaxyGroups)) {
    galaxyGroups.forEach((g, idx) => {
      if (g == null) return;
      g.rotation.y += (idx === 0 ? 0.00025 : -0.0002) * timeScale;
    });
  }

  // Movimiento de blobs: la velocidad visual debe coincidir EXACTAMENTE con el backend
  // Para que la interpolación visual sincronice con la simulación real
  const baseMoveSpeed = 8.0; // Aumentado para movimiento más fluido y visible
  const movementScale = timeScale; // Usar timeScale directamente sin suavizado
  const baseStep = baseMoveSpeed * dtRaw * movementScale;
  const baseY = 0.05;

  for (const jid in creatures) {
    const entry = creatures[jid];
    const mesh = entry.mesh;
    const target = entry.target;

    // velocidad lógica del blob (si no hay dato, usar 1.0)
    const creatureSpeed = entry.data && typeof entry.data.speed === 'number'
      ? entry.data.speed
      : 1.0;

    // Mapear speed directamente: las criaturas con mayor speed se mueven más rápido
    // Usar factor más lineal para que coincida mejor con la lógica del backend
    const minSpeed = 0.3;
    const maxSpeed = 2.5;
    const s = Math.max(minSpeed, Math.min(maxSpeed, creatureSpeed));
    const visualFactor = s; // Factor lineal: speed 1.0 = velocidad base
    let maxStep = baseStep * visualFactor;
    if (movementLockedVisual) {
      // durante el bloqueo visual al inicio de la generación, no avanzar horizontalmente
      maxStep = 0;
    }

    if (target && maxStep > 0) {
      tempDir.subVectors(target, mesh.position);
      tempDir.y = 0;
      const distSq = tempDir.lengthSq();
      if (distSq > 1e-6) {
        const dist = Math.sqrt(distSq);
        const step = Math.min(maxStep, dist);
        tempDir.multiplyScalar(step / dist);
        mesh.position.add(tempDir);

        // orientar el blob con giro suave hacia la dirección de movimiento
        const desiredAngle = Math.atan2(tempDir.x, tempDir.z);
        let heading = typeof entry.heading === 'number' ? entry.heading : (mesh.rotation.y || desiredAngle);
        let delta = desiredAngle - heading;
        // normalizar a rango [-PI, PI]
        delta = ((delta + Math.PI) % (Math.PI * 2)) - Math.PI;
        const rotLerp = 0.15; // factor de suavizado del giro
        heading += delta * rotLerp;
        entry.heading = heading;
        mesh.rotation.y = heading;
      } else {
        mesh.position.copy(target);
      }
    }

    // pequeña oscilación vertical (bobbing) por criatura para dar sensación de vida
    if (typeof entry.bobPhase !== 'number') {
      entry.bobPhase = Math.random() * Math.PI * 2;
    }
    const bobSpeed = (3.0 + creatureSpeed * 0.8) * movementScale;
    entry.bobPhase += bobSpeed * dtRaw;
    const bobAmplitude = 0.03 + 0.01 * Math.min(Math.max(creatureSpeed - 0.5, 0), 1.5);
    const bobOffset = Math.sin(entry.bobPhase) * bobAmplitude;
    mesh.position.y = baseY + bobOffset;

    // efecto de respiración: expansión/compresión suave del modelo
    if (typeof entry.breathPhase !== 'number') {
      entry.breathPhase = Math.random() * Math.PI * 2;
    }
    const energyNorm = entry.data && typeof entry.data.energy === 'number'
      ? Math.max(0, Math.min(1, entry.data.energy / 10))
      : 0.5;
    const breathSpeed = (1.2 + (1.0 - energyNorm) * 0.8) * movementScale; // con poca energía respira un poco más rápido
    entry.breathPhase += breathSpeed * dtRaw;
    const breath = Math.sin(entry.breathPhase);
    const breathAmp = 0.06 + 0.04 * energyNorm; // más energía => respiración un poco más marcada
    const baseSize = typeof entry.baseSize === 'number' ? entry.baseSize : (mesh.scale.x || 1.0);
    const scaleY = baseSize * (1 + breathAmp * breath);
    const scaleXZ = baseSize * (1 - breathAmp * 0.5 * breath);
    mesh.scale.set(scaleXZ, scaleY, scaleXZ);
  }

  // Resolución robusta de colisiones entre blobs (hitboxes esféricas con múltiples iteraciones)
  const entries = Object.values(creatures);
  const count = entries.length;
  // Múltiples pasadas para resolver colisiones de forma más estable
  const collisionIterations = 3;
  for (let iter = 0; iter < collisionIterations; iter++) {
    for (let i = 0; i < count; i++) {
      const a = entries[i];
      const meshA = a.mesh;
      const baseSizeA = typeof a.baseSize === 'number' ? a.baseSize : (meshA.scale.x || 1.0);
      const radiusA = baseSizeA * 0.8; // radio aumentado para hitboxes más grandes
      for (let j = i + 1; j < count; j++) {
        const b = entries[j];
        const meshB = b.mesh;
        const baseSizeB = typeof b.baseSize === 'number' ? b.baseSize : (meshB.scale.x || 1.0);
        const radiusB = baseSizeB * 0.8;
        const dx = meshB.position.x - meshA.position.x;
        const dz = meshB.position.z - meshA.position.z;
        const distSq = dx * dx + dz * dz;
        if (distSq <= 1e-6) continue;
        const dist = Math.sqrt(distSq);
        const minDist = radiusA + radiusB;
        if (dist < minDist) {
          const overlap = minDist - dist;
          const nx = dx / dist;
          const nz = dz / dist;
          // Push más fuerte para evitar atravesaje
          const push = overlap * 0.55;
          meshA.position.x -= nx * push;
          meshA.position.z -= nz * push;
          meshB.position.x += nx * push;
          meshB.position.z += nz * push;
        }
      }
    }
  }

  foodMeshes.forEach((mesh, i) => {
    mesh.position.y = 0.35 + Math.sin(time * 4 + i * 0.7) * 0.06;
  });

  // Lento giro de los cinturones de asteroides
  if (Array.isArray(asteroidBelts)) {
    asteroidBelts.forEach((beltObj, idx) => {
      const belt = beltObj.points;
      if (!belt) return;
      belt.rotation.y += (idx === 0 ? 0.00025 : -0.0002) * timeScale;
    });
  }

  // Cometas orbitando en el fondo
  if (Array.isArray(comets)) {
    comets.forEach((c) => {
      const cfg = c.cfg;
      if (!cfg) return;
      cfg.phase += cfg.speed * dt;
      const angle = cfg.phase;
      const x = Math.cos(angle) * cfg.orbitRadius;
      const z = Math.sin(angle) * cfg.orbitRadius;
      const y = cfg.height + Math.sin(angle * 0.5) * 10;

      c.head.position.set(x, y, z);

      // actualizar cola como puntos detrás del cometa
      const tailPositions = c.tailPositions;
      for (let i = c.tailCount - 1; i > 0; i--) {
        tailPositions[i * 3] = tailPositions[(i - 1) * 3];
        tailPositions[i * 3 + 1] = tailPositions[(i - 1) * 3 + 1];
        tailPositions[i * 3 + 2] = tailPositions[(i - 1) * 3 + 2];
      }
      tailPositions[0] = x;
      tailPositions[1] = y;
      tailPositions[2] = z;
      c.tail.geometry.attributes.position.needsUpdate = true;
    });
  }

  controls.update();
  renderer.render(scene, camera);
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

window.addEventListener('DOMContentLoaded', () => { init(); setupTimeControls(); setupCurseTool(); });

function performCurseDrop(event) {
  if (!renderer || !camera) return;
  const rect = renderer.domElement.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  mouse.set(x, y);
  raycaster.setFromCamera(mouse, camera);

  const meshes = [];
  for (const jid in creatures) {
    const entry = creatures[jid];
    if (entry && entry.mesh) {
      meshes.push(entry.mesh);
    }
  }
  if (!meshes.length) return;

  const intersects = raycaster.intersectObjects(meshes, true);
  if (!intersects.length) return;

  let obj = intersects[0].object;
  let targetJid = null;
  while (obj && !targetJid) {
    if (obj.userData && obj.userData.jid) {
      targetJid = obj.userData.jid;
      break;
    }
    obj = obj.parent;
  }

  if (!targetJid) return;

  fetch('/kill', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jid: targetJid }),
  }).catch((err) => {
    console.error('Error calling /kill', err);
  });
}

function setupCurseTool() {
  const tool = document.getElementById('curse-tool');
  if (!tool) return;

  let dragging = false;

  function onPointerMove(event) {
    if (!dragging) return;
    const rect = tool.getBoundingClientRect();
    const x = event.clientX;
    const y = event.clientY;
    tool.style.position = 'fixed';
    tool.style.left = x - rect.width / 2 + 'px';
    tool.style.top = y - rect.height / 2 + 'px';
    tool.style.right = 'auto';
    tool.style.bottom = 'auto';
  }

  function onPointerUp(event) {
    if (!dragging) return;
    dragging = false;
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
    tool.classList.remove('curse-tool--active');
    performCurseDrop(event);
    tool.style.left = '';
    tool.style.top = '';
  }

  function onPointerDown(event) {
    event.preventDefault();
    dragging = true;
    tool.classList.add('curse-tool--active');
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  }

  tool.addEventListener('pointerdown', onPointerDown);
}
