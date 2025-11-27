# Simulación SPADE: Selección Natural con Comportamientos Emergentes

------------------------------------------------------------------------------------------------------------------------------------------------
Introducción
------------------------------------------------------------------------------------------------------------------------------------------------

Este proyecto implementa una simulación de selección natural y comportamientos emergentes utilizando agentes autónomos construidos con SPADE (Smart Python Agent Development Environment).

El sistema recrea un ecosistema donde múltiples criaturas operan de manera independiente con comportamientos complejos que incluyen:
- **Satisfacción basada en objetivos**: Las criaturas buscan alimento hasta alcanzar un objetivo de comida consumida
- **Modo supervivencia**: Cuando la energía cae por debajo del 35%, las criaturas reducen su objetivo de 2 a 1 alimento
- **Retorno al hogar**: Una vez satisfechas, las criaturas regresan a su punto de spawn sin gastar energía
- **Movimiento sincronizado**: Todas las criaturas inician su movimiento simultáneamente después de spawnearse
- **Distribución equidistante**: Las criaturas nacen distribuidas uniformemente en el perímetro del mundo

La ejecución completa incluye:
1. Creación de agentes y del entorno
2. Ciclo de vida de cada generación con métricas de supervivencia
3. Visualización 3D en tiempo real mediante interfaz web con Three.js
4. Control de velocidad de simulación (0.25x - 2.0x)
5. Registro detallado de eventos y resultados en CSV

La arquitectura se basa en comunicación asincrónica entre agentes utilizando XMPP y mensajes periódicos de estado, donde HostAgent actúa como punto de observación y sincronización para la UI.

------------------------------------------------------------------------------------------------------------------------------------------------
Conceptos teóricos aplicados
------------------------------------------------------------------------------------------------------------------------------------------------

### 1. **Sistemas Multi-Agente (MAS)**
El proyecto implementa un Sistema Multi-Agente donde cada entidad (criatura, generación, host) opera como un agente autónomo con:
- **Autonomía**: Cada agente toma decisiones independientes sin control centralizado
- **Comunicación asincrónica**: Intercambio de mensajes mediante protocolo XMPP
- **Proactividad**: Los agentes persiguen objetivos (buscar comida, sobrevivir, reproducirse)
- **Reactividad**: Responden a cambios en el entorno (energía baja, comida cercana)

### 2. **Comportamiento Emergente**
El sistema exhibe comportamientos emergentes que surgen de reglas simples:
- **Modo supervivencia**: Las criaturas adaptan su estrategia cuando la energía es crítica
- **Optimización de recursos**: Las criaturas satisfechas retornan al hogar sin gastar energía
- **Convergencia espacial**: La distribución perimetral crea patrones de movimiento radiales

### 3. **Selección Natural Simulada**
Implementa principios evolutivos básicos:
- **Fitness variable**: Las criaturas con mejor gestión energética sobreviven más tiempo
- **Reproducción selectiva**: Solo las criaturas que alcanzan satisfacción (2 alimentos) se reproducen
- **Presión ambiental**: La escasez de recursos fuerza decisiones estratégicas
- **Supervivencia diferencial**: El modo supervivencia permite adaptación bajo estrés

### 4. **Arquitectura Basada en Mensajes**
Patrón de comunicación asincrónica:
- **Publisher-Subscriber**: Las criaturas publican estados, el host los consume
- **Event-Driven**: La lógica reacciona a eventos (comida consumida, energía crítica, satisfacción)
- **Temporal consistency**: Sistema de timestamps previene inconsistencias por mensajes tardíos

### 5. **Máquinas de Estado Finito (FSM)**
Cada criatura implementa estados bien definidos:
```
FORAGING → [comida >= objetivo] → SATISFIED → RETURNING_HOME → FINISHED
    ↓
[energía ≤ 35%] → SURVIVAL_MODE → [comida >= 1] → SATISFIED
    ↓
[energía ≤ 0] → EXHAUSTED → FINISHED
```

### 6. **Sincronización Distribuida**
Mecanismos para coordinar agentes sin control centralizado:
- **Barrier synchronization**: Señal `start_moving` sincroniza inicio de movimiento
- **Flag-based coordination**: `can_move` previene movimiento prematuro
- **Spawn sequence**: Creación secuencial con confirmación de inicio

### 7. **Optimización Espacial**
Algoritmos geométricos para distribución y navegación:
- **Perimeter distribution**: Cálculo de posiciones equidistantes en rectángulo
- **Euclidean distance**: Detección de comida y retorno al spawn
- **Homing behavior**: Navegación sin costo energético hacia punto de origen

------------------------------------------------------------------------------------------------------------------------------------------------
Agentes del sistema
------------------------------------------------------------------------------------------------------------------------------------------------

`HostAgent`
Es el agente encargado de:
- Servir la interfaz web mediante servidor HTTP (aiohttp) en puerto 10000
- Exponer el estado global del mundo mediante endpoint `/fishes`
- Mantener un diccionario actualizado de criaturas activas con sus estados
- Recibir mensajes de estados enviados por cada criatura (CyclicBehaviour)
- Registrar eliminaciones mediante la lista de `removals`, utilizada para efectos visuales
- Manejar la ventana de protección contra reintroducción (3 segundos)
- Iniciar la simulación y lanzar el GenerationAgent
- Gestionar control de velocidad mediante endpoint `/set_speed` (0.25x - 2.0x)
- Limpiar archivos CSV al inicio de cada ejecución

Es el agente más cercano a la interfaz e integra la parte visual con la parte lógica.

`GenerationAgent`
Coordina la simulación como un controlador central. Sus funciones principales son:
- Inicializar cada generación con distribución perimetral equidistante de criaturas
- Colocar comida aleatoriamente en el mapa (cantidad configurable)
- Enviar señal de sincronización `start_moving` después del spawn completo
- Supervisar depredación, muerte, agotamiento energético y satisfacción
- Procesar mensajes de criaturas (comida consumida, finalización)
- Recolectar información para métricas generacionales (CSV)
- Determinar finalización cuando `active_creature_jids` está vacío
- Generar reportes: `generation_summary.csv`, `generation_details.csv`, `predation_events.csv`
- Gestionar herencia genética para siguiente generación

**Comportamientos (SPADE Behaviours):**
- `RecvBehav` (CyclicBehaviour): Recibe eventos de criaturas (ate_food, finished, status)
- `MonitorBehav` (PeriodicBehaviour): Supervisa condiciones de término de generación

Este agente actúa como supervisor, recolector de estadísticas y motor evolutivo.

`CreatureAgent`
Cada CreatureAgent se comporta como una entidad autónoma con comportamientos complejos:

**Estados del ciclo de vida:**
- **Foraging**: Búsqueda activa de alimento con consumo de energía
- **Survival Mode**: Activado cuando energía ≤ 35%, reduce objetivo de 2 a 1 alimento
- **Satisfied**: Alcanzado el objetivo de comida, inicia retorno al spawn
- **Returning Home**: Navegación sin costo energético hacia punto de origen
- **Finished**: Terminación por satisfacción, agotamiento energético o por muerte causada por una criatura más grande

**Características del agente:**
- Movimiento dentro de la cuadrícula con consumo energético proporcional
- Detección y consumo de comida en radio de percepción (`sense`)
- Sistema de satisfacción con objetivos variables (2 → 1 en modo supervivencia)
- Reporte periódico de estado a HostAgent y GenerationAgent
- Variables heredables: velocidad (`speed`), tamaño (`size`), percepción (`sense`)

**Comportamientos (SPADE Behaviours):**
- `ReportBehav` (PeriodicBehaviour): Gestiona movimiento, energía y lógica de estados
- `RecvBehav` (CyclicBehaviour): Recibe señales de inicio y terminación

La criatura opera con información local (percepción limitada), sin conocimiento global del mapa.

------------------------------------------------------------------------------------------------------------------------------------------------
Arquitectura del proyecto
------------------------------------------------------------------------------------------------------------------------------------------------

El proyecto se organiza en los siguientes archivos principales:

`hostAgent.py`
Servidor HTTP y agente intermediario entre la simulación y la interfaz visual. Maneja la recepción de estados y el envío del estado completo a la UI.

`generationAgent.py`
Motor principal de la simulación. Controla las generaciones, depredación, métricas y creación de criaturas.

`creatureAgent.py`
Implementación del comportamiento individual de las criaturas: movimiento, energía, comida y comunicación.

`world.py`
Define WorldConfig con parámetros como dimensiones, energía inicial, cantidad de comida, duración de generación, velocidad de reporte, tasas de depredación, etc.

`utils.py`
Funciones auxiliares:
- `dist()`: Cálculo de distancia euclidiana
- `random_pos()`: Generación de posiciones aleatorias válidas
- `generate_pellets()`: Creación de pellets de comida
- `spawn_positions_on_perimeter()`: Distribución equidistante en perímetro rectangular
  - Calcula perímetro total: `2 * (width + height)`
  - Divide en segmentos iguales según cantidad de criaturas
  - Recorre bordes: top → right → bottom → left
  - Garantiza fairness espacial en condiciones iniciales

`logger_setup.py`
Configuración del logger unificado. Guarda los logs en `report/run.log` con rotación (hasta 3 archivos de respaldo).

`report/`
Contiene los resultados generados automáticamente:
- `generation_summary.csv` (métricas agregadas por generación)
- `generation_details.csv` (detalle por criatura)
- `predation_events.csv` (lista de eventos de depredación)
- `run.log` (log principal)

`static/`
Archivos de la interfaz web con visualización 3D:
- `index.html`: Interfaz principal con Three.js (r149), incluye:
  - Botones de control de velocidad (0.25x, 0.5x, 1.0x, 1.5x, 2.0x)
  - Display de número de generación
  - Canvas para renderizado 3D
- `app.js`: Lógica de visualización:
  - Polling a `/fishes` cada 250ms
  - Control de velocidad mediante POST a `/set_speed`
- `style.css`: Estilos para UI y botones de control

------------------------------------------------------------------------------------------------------------------------------------------------
Funcionamiento interno de la interfaz web
------------------------------------------------------------------------------------------------------------------------------------------------

La interfaz funciona mediante polling al endpoint `/fishes` cada 250ms.

**Ciclo de actualización (app.js):**
1. Solicita el estado global al servidor HostAgent
2. Recibe datos JSON con:
   - `generation`: Número de generación actual
   - `creatures`: Array de criaturas activas con posición, energía, comida, atributos
   - `foods`: Array de posiciones de comida disponible
   - `removals`: Array de criaturas eliminadas recientemente
   - `space_size`: Dimensiones del mundo

3. **Renderizado 3D con Three.js:**
   - **Criaturas**: Geometría orgánica tipo blob con:
     - Colores dinámicos basados en velocidad (verde = lento → rojo = rápido)
     - Animaciones de respiración y flotación natural
     - Escala proporcional al tamaño (`size`)
     - Intensidad emisiva según nivel de energía
   - **Comida**: Esferas verdes luminosas con suave emisión
   - **Fondo espacial**: Múltiples capas de estrellas animadas con galaxias giratorias
   - **Grid**: Plano de referencia con líneas sutiles

4. **Sistema de selección de criaturas:**
   - Click en cualquier blob para seleccionarlo
   - Panel lateral muestra estadísticas en tiempo real:
     - ID de Criatura
     - Generación
     - Velocidad
     - Energía
     - Tamaño
     - Sentido (rango de percepción)
     - Comida comida (contador)
     - Asesinatos (contador de depredaciones)
   - Contorno visual destacado alrededor del blob seleccionado
   - Stats se actualizan inmediatamente al depredar o consumir comida

5. **Gráfico de distribución de velocidad:**
   - Histograma en tiempo real mostrando distribución de velocidades
   - 10 bins desde velocidad mínima a máxima
   - Color degradado verde→amarillo→rojo según velocidad
   - Actualización dinámica cada 500ms
   - Permite observar presión selectiva y evolución de la población

6. **Animaciones de muerte diferenciadas:**
   - **Depredación** (`reason=killed`): Explosión de sangre con partículas rojas dispersándose
   - **Muerte por hambre** (`reason=exhausted`): Explosión de sangre (muerte dramática)
   - **Satisfacción** (`reason=finished`): Desvanecimiento limpio sin sangre
   - **Timeout de generación**: Desvanecimiento pacífico
   - Manchas de sangre persistentes durante la generación
   - Limpieza automática de sangre al cambiar de generación

7. **Herramienta de maldición (Curse Tool):**
   - Icono de calavera draggable en la esquina
   - Arrastrar y soltar sobre un blob para eliminarlo instantáneamente
   - Envía solicitud POST a `/kill` con el JID de la criatura
   - Permite observar efectos de eliminación selectiva

8. **Controles de velocidad:**
   - Botones modifican el periodo de `ReportBehav` en todas las criaturas
   - 0.25x = 2.0s periodo (slow motion)
   - 0.5x = 1.0s periodo
   - 1.0x = 0.5s periodo (normal)
   - 1.5x = 0.33s periodo
   - 2.0x = 0.25s periodo (fast forward)
   - POST a `/set_speed` actualiza dinámicamente sin reiniciar simulación
   - Polling dinámico: intervalo de actualización se ajusta según timeScale (250ms/timeScale, mínimo 100ms)

9. **OrbitControls:** Permite rotación, zoom y paneo de la cámara 3D

El canvas se redibuja completamente en cada ciclo para reflejar cambios en tiempo real. El sistema de colores dinámico permite identificar visualmente criaturas rápidas (rojizas) vs lentas (verdosas), facilitando observación de patrones evolutivos.

------------------------------------------------------------------------------------------------------------------------------------------------
Mejoras visuales y sistema de feedback en tiempo real
------------------------------------------------------------------------------------------------------------------------------------------------

### **1. Colores dinámicos basados en velocidad**
Cada blob tiene un color que representa su atributo de velocidad:
- **Verde (HSL 120°)**: Criaturas lentas (velocidad mínima)
- **Amarillo (HSL 60°)**: Criaturas de velocidad media
- **Rojo (HSL 0°)**: Criaturas rápidas (velocidad máxima)

**Implementación:**
```javascript
const minSpeed = 0.5, maxSpeed = 2.0;
const speedNorm = (speed - minSpeed) / (maxSpeed - minSpeed);
const hue = (1 - speedNorm) * 120; // Verde a Rojo
```

Esto permite identificar a simple vista la distribución de velocidades en la población y observar cómo la presión selectiva favorece ciertos rangos.

### **2. Panel de estadísticas por criatura**
Al hacer click en cualquier blob, se despliega un panel lateral con 8 métricas en tiempo real:

| Campo | Descripción | Formato |
|-------|-------------|---------|
| **ID Criatura** | JID único del agente | `creature0_3` |
| **Generación** | Número de generación actual | `Gen 2` |
| **Velocidad** | Atributo heredable de velocidad | `1.23` |
| **Energía** | Nivel actual de energía | `5.67` |
| **Tamaño** | Factor de tamaño (afecta depredación) | `1.45` |
| **Sentido** | Radio de percepción | `0.85` |
| **Comida comida** | Contador de alimentos consumidos | `2` |
| **Asesinatos** | Contador de depredaciones exitosas | `1` |

**Actualización en tiempo real:**
- Cada mensaje `status` del backend actualiza el panel si el blob está seleccionado
- Actualización inmediata al depredar (contador de kills sube instantáneamente)
- Sincronización perfecta: backend → `kill_confirmed` message → `creatureAgent.state.kills` → status report → frontend display

### **3. Gráfico de distribución de velocidad**
Histograma dinámico tipo bar chart que muestra la distribución poblacional:

**Características:**
- **10 bins** desde velocidad mínima (0.5) a máxima (2.0)
- Colores de barras siguen mismo esquema verde→amarillo→rojo
- Altura de barra = cantidad de criaturas en ese rango
- Actualización cada 500ms
- Eje Y adaptativo (escala automática según población máxima)

**Utilidad científica:**
- Observar deriva genética: distribución inicial uniforme → distribución sesgada por selección
- Identificar presión selectiva: si recursos escasos, criaturas rápidas dominan (barras rojas más altas)
- Detectar cuellos de botella: súbita reducción de diversidad genética
- Validar herencia: distribución de siguiente generación refleja padres supervivientes

### **4. Sistema de animaciones de muerte**
Tres tipos de animación según causa de muerte:

#### **Depredación** (`reason=killed`, `killed_by` presente)
```javascript
playBloodDeath(mesh, jid, isPredation=true)
```
- Explosión de **20 partículas de sangre** rojas (#ff0000)
- Dispersión radial con velocidades aleatorias (0.05-0.15 unidades/frame)
- Partículas descienden (gravedad simulada)
- Manchas de sangre persistentes en el suelo (decals rojos)
- Duración: 1.2 segundos
- Efecto visual dramático para destacar evento de depredación

#### **Muerte por hambre** (`reason=exhausted`)
```javascript
playBloodDeath(mesh, jid, isPredation=false)
```
- Misma animación de sangre que depredación
- Indica muerte violenta por agotamiento extremo
- Permite distinguir visualmente criaturas que murieron sin ser atacadas

#### **Satisfacción/Timeout** (`reason=finished`)
```javascript
playFadeOut(mesh, jid)
```
- Desvanecimiento suave y limpio (fade opacity 1.0 → 0.0)
- Reducción de tamaño al 50%
- Sin partículas de sangre
- Duración: 400ms
- Representa terminación pacífica (objetivo cumplido o timeout)

**Gestión de manchas de sangre:**
- Array `bloodStains` almacena todas las manchas generadas en la generación
- Función `cleanupBloodStains()` se ejecuta al cambiar de generación
- Limpieza completa: remove from scene + dispose geometry/material
- Previene acumulación de objetos 3D y memory leaks

### **5. Herramienta de eliminación manual (Curse Tool)**
Icono de calavera draggable que permite intervención manual:

**Funcionamiento:**
1. Usuario arrastra calavera desde esquina superior derecha
2. Suelta sobre un blob en el canvas
3. Raycasting de Three.js detecta criatura bajo cursor
4. POST request a `/kill` endpoint: `{jid: "creature1_5"}`
5. Backend elimina agente y notifica como `creature_removed`
6. Frontend reproduce animación de sangre

**Utilidad:**
- Experimentos controlados: eliminar selectivamente criaturas lentas/rápidas
- Observar impacto de eliminación artificial en distribución
- Debugging: forzar eventos de muerte para probar animaciones

### **6. Sincronización de movimiento mejorada**
Para evitar desincronización entre backend y frontend:

**Antes (problema):**
- `movementScale = Math.pow(timeScale, 0.5)` suavizaba excesivamente
- `baseMoveSpeed = 2.6` demasiado lento
- Polling fijo 250ms no se adaptaba a timeScale
- Resultado: criaturas lentas, comida desaparecía sin contacto visible

**Después (solución):**
- `movementScale = timeScale` (lineal, sin suavizado)
- `baseMoveSpeed = 8.0` (movimiento más fluido)
- `visualFactor = speed` (directo, sin exponencial)
- Polling dinámico: `interval = 250ms / timeScale` (min 100ms)
- Resultado: sincronización perfecta, movimientos fluidos

**Fórmula de polling adaptativo:**
```javascript
const baseInterval = 250;
const dynamicInterval = Math.max(100, baseInterval / timeScale);
```

A 2x velocidad → 125ms polling (más actualizaciones)
A 0.25x velocidad → 250ms polling (menos frecuencia necesaria)

------------------------------------------------------------------------------------------------------------------------------------------------
Modelo de comunicación
------------------------------------------------------------------------------------------------------------------------------------------------

Los agentes SPADE se comunican mediante mensajes XMPP con arquitectura asincrónica.

**Tipos de mensajes:**

1. **status** (Creature → Host, Creature → Generation)
   - Enviado periódicamente por `ReportBehav`
   - Contenido: `jid`, `x`, `y`, `energy`, `size`, `sense`, `foods_eaten`
   - Usado para actualización de UI y monitoreo de estados

2. **ate_food** (Creature → Generation)
   - Enviado cuando criatura consume comida
   - Contenido: `food_pos` (coordenadas)
   - Genera registro en `predation_events.csv` si aplica

3. **eat_confirm** (Generation → Creature)
   - Confirmación de consumo de comida o depredación exitosa
   - Contenido: `jid`, `energy_gain`, `prey` (opcional)
   - Incrementa `foods_eaten` y restaura energía en la criatura

4. **kill_confirmed** (Generation → Creature)
   - Notificación de depredación exitosa
   - Contenido: `kills` (nuevo valor del contador)
   - Actualiza `state.kills` en el depredador
   - Permite sincronización inmediata con frontend (panel de stats)

5. **creature_removed** (Creature/Generation → Host)
   - Notificación de eliminación para actualizar UI
   - Contenido: `jid`, `reason`, `killed_by` (opcional)
   - Razones posibles:
     - `killed`: Depredación → animación de sangre
     - `exhausted`: Muerte por hambre → animación de sangre
     - `finished`: Satisfacción/timeout → desvanecimiento limpio
   - Host agrega a array `removals` para procesamiento en frontend

6. **finished** (Creature → Generation)
   - Enviado al terminar ciclo de vida natural
   - Contenido: `foods_eaten`, `energy`, `size`, `sense`, `kills`
   - Usado para cálculo de métricas generacionales

7. **start_moving** (Generation → Creature)
   - Enviado después de spawn completo (barrier synchronization)
   - Activa flag `can_move` en criaturas
   - Garantiza inicio sincronizado de movimiento

8. **generation_end** (Generation → Creature)
   - Señal de terminación forzada (timeout de 15 segundos sin comida)
   - Fuerza envío de `creature_removed` con `reason=finished`
   - Criatura envía estado final y detiene agente

**Patrón de comunicación:**
- **Asincrónico**: No hay espera activa de respuestas
- **Event-driven**: Reacciones basadas en eventos recibidos
- **Timestamped**: Protección contra mensajes tardíos (3s grace period)
- **CyclicBehaviour**: Recepción continua de mensajes
- **PeriodicBehaviour**: Envío periódico de estados

------------------------------------------------------------------------------------------------------------------------------------------------
Características avanzadas implementadas
------------------------------------------------------------------------------------------------------------------------------------------------

### 1. **Sistema de Satisfacción con Objetivos Variables**
- Objetivo inicial: 2 alimentos para reproducirse
- Modo supervivencia (energía ≤ 35%): Objetivo reducido a 1 alimento
- Permite estrategias adaptativas bajo presión energética
- Implementado mediante `CreatureState` dataclass con flags: `satisfied`, `survival_mode`, `food_goal`

### 2. **Retorno al Hogar Sin Costo Energético**
- Criaturas satisfechas navegan hacia spawn point (`spawn_x`, `spawn_y`) sin drenar energía
- Evita penalización por comportamiento exitoso
- Flag `returning_home` controla este estado especial
- Distancia < 0.5 unidades activa terminación con `satisfied=True`

### 3. **Spawn Sincronizado y Distribución Equidistante**
- **Barrier synchronization**: Señal `start_moving` después de spawn completo
- **Perimeter distribution**: Criaturas distribuidas uniformemente en bordes del mundo
- Algoritmo recorre perímetro rectangular: top → right → bottom → left
- Garantiza fairness espacial (todas las criaturas equidistantes de recursos centrales)

### 4. **Control Dinámico de Velocidad**
- 5 velocidades disponibles: 0.25x, 0.5x, 1.0x, 1.5x, 2.0x
- Modificación en tiempo real sin reiniciar simulación
- Endpoint `/set_speed` actualiza periodo de `ReportBehav` de todas las criaturas
- Útil para observación detallada (slow motion) o pruebas rápidas (fast forward)
- Polling dinámico frontend: intervalo de actualización se adapta a timeScale (250ms/timeScale, mínimo 100ms)

### 5. **Timeout de Generación Inteligente**
- Condición principal de fin: `active_creature_jids == 0` (todas las criaturas terminaron naturalmente)
- Timeout de seguridad: Si no hay comida y han pasado **15 segundos** sin que nadie coma
- Evita generaciones colgadas por bugs de comportamiento (criaturas que nunca regresan)
- Permite observar animaciones de muerte por hambre antes de forzar cierre
- Criaturas restantes reciben `generation_end` → desvanecimiento limpio sin sangre
- Configurable mediante `WorldConfig.last_eat_grace` (default: 15.0 segundos)

### 6. **Limpieza Automática de Reportes**
- CSV limpiados al inicio de cada ejecución (`hostAgent.py`)
- Previene acumulación de datos entre simulaciones
- Archivos afectados:
  - `generation_summary.csv`
  - `generation_details.csv`
  - `predation_events.csv`

------------------------------------------------------------------------------------------------------------------------------------------------
Protección contra reintroducción
------------------------------------------------------------------------------------------------------------------------------------------------

Uno de los problemas conocidos en entornos asincrónicos es la llegada de mensajes tardíos después de la eliminación de un agente.
Para evitar que una criatura muerta reaparezca en el canvas:
- Cuando HostAgent registra una eliminación, guarda un timestamp.
- Durante tres segundos posteriores, cualquier mensaje de estado de ese mismo JID es ignorado.
- Esto evita carreras de mensajes y mantiene la interfaz consistente.

------------------------------------------------------------------------------------------------------------------------------------------------
Cómo ejecutar
------------------------------------------------------------------------------------------------------------------------------------------------

1.	Activar el entorno virtual (si corresponde)
powershell
& C:/SPADE/cst/Scripts/Activate.ps1
2.	Ejecutar el agente host, que inicia automáticamente GenerationAgent y la UI
powershell
py hostAgent.py
3.	Abrir la interfaz web en el navegador
http://localhost:10000/static/index.html

------------------------------------------------------------------------------------------------------------------------------------------------
Sobre los reportes generados
------------------------------------------------------------------------------------------------------------------------------------------------

run.log
Registro rotativo con eventos importantes. Permite revisar:
- Depredación
- Eliminación de criaturas
- Errores
- Mensajes tardíos
- Estados enviados por las criaturas

generation_summary.csv
Métricas agregadas por generación:
- `generation`: Número de generación
- `num_creatures`: Cantidad inicial de criaturas
- `num_foods`: Cantidad de alimento disponible
- `survivors`: Criaturas que completaron el ciclo
- `satisfied_creatures`: Criaturas que alcanzaron objetivo y retornaron (reproducción exitosa)
- `exhausted_creatures`: Criaturas que agotaron energía
- `avg_foods_eaten`: Promedio de alimentos consumidos
- `duration_seconds`: Duración total de la generación

generation_details.csv
Reporte individual por criatura:
- `generation`, `creature_jid`: Identificadores
- `initial_energy`, `final_energy`: Estado energético
- `foods_eaten`: Alimentos consumidos durante ciclo de vida
- `lifetime_seconds`: Duración de vida
- `speed`, `size`, `sense`: Atributos heredables
- `final_x`, `final_y`: Posición de terminación
- `satisfied`: Boolean indicando si alcanzó objetivo y retornó al spawn

predation_events.csv
Registro cronológico de eventos de depredación y consumo:
- `generation`: Número de generación
- `timestamp`: Momento del evento
- `predator_jid`: JID del agente que consumió
- `prey_jid`: JID o identificador de comida consumida
- `x`, `y`: Coordenadas del evento

------------------------------------------------------------------------------------------------------------------------------------------------
Diagnóstico y depuración
------------------------------------------------------------------------------------------------------------------------------------------------

`Para buscar información específica en los logs:`
powershell
Select-String -Path .\report\run.log* -Pattern "creature9_7"

`Para ver las últimas líneas del archivo (archivo activo):`
powershell
Get-Content .\report\run.log -Tail 200

`Para revisar también los archivos rotados:`
powershell
Get-ChildItem .\report\run.log* | Get-Content -Tail 200

------------------------------------------------------------------------------------------------------------------------------------------------
Parámetros configurables
------------------------------------------------------------------------------------------------------------------------------------------------

Los parámetros principales del mundo pueden modificarse en `WorldConfig` (`world.py`):

**Dimensiones y energía:**
- `space_size`: Dimensiones del mundo (default: 30x30)
- `initial_energy`: Energía inicial de criaturas (default: 1.0)
- `move_cost`: Costo energético por movimiento (default: 0.1)
- `energy_per_food`: Energía ganada por alimento (default: 3.0)

**Población y recursos:**
- `num_pellets`: Cantidad de comida por generación (default: 20)
- `num_creatures`: Criaturas iniciales (default: 10)

**Comportamiento:**
- `food_goal`: Objetivo de satisfacción normal (default: 2)
- `survival_threshold`: Umbral para modo supervivencia (default: 0.35 = 35%)
- `survival_food_goal`: Objetivo reducido en supervivencia (default: 1)

**Temporización:**
- `generation_duration`: Duración máxima de generación en segundos
- `report_period`: Intervalo de envío de estados (default: 0.5s)
- `monitor_period`: Intervalo de supervisión (default: 0.5s)
- `last_eat_grace`: Tiempo de espera sin comida antes de terminar generación

**UI y velocidad:**
- `poll_interval`: Frecuencia de actualización de UI (default: 250ms)
- Velocidad de simulación modificable en runtime (0.25x - 2.0x)

**Atributos heredables:**
- `speed`: Velocidad de movimiento (afecta distancia por tick)
- `size`: Tamaño de criatura (futuro: colisiones, visibilidad)
- `sense`: Radio de percepción para detectar comida


------------------------------------------------------------------------------------------------------------------------------------------------
**DECLARACIÓN DE USO DE IA Y EJERCICIOS DE CLASE**
------------------------------------------------------------------------------------------------------------------------------------------------

**EJERCICIO SEMANA 10 - PECESITOS**

Este proyecto se basa en conceptos y estructuras presentadas en los ejercicios de la Semana 10 (simulación de peces con SPADE) y otros ejemplos introductorios de agentes. A continuación se detallan las correspondencias directas entre el código del proyecto y los ejercicios de clase.

Inspiración del ejercicio “fish.py” (pecesito):
El comportamiento de movimiento y atributos básicos de las criaturas deriva del modelo visto en clase: un agente con posición, tamaño y velocidad que se actualiza cada ciclo. En el proyecto, esto se refleja en:
	•	CreatureState (creatureAgent.py): definición de size, speed, x, y, sense, foods_eaten, energy.
	•	ReportBehav.run() (creatureAgent.py): lógica de desplazamiento por tick, cálculos de cambio de posición, consumo energético y envío de estado.
	•	utils.random_size(), utils.random_speed(), utils.default_energy_for_speed(): funciones basadas en la relación tamaño–velocidad presentada en el ejercicio del pez.

Inspiración del ejercicio “dummy.py”:
El patrón básico de un agente SPADE con async def setup() proviene del ejemplo DummyAgent. Se reutiliza en:
	•	GenerationAgent.setup() (generationAgent.py): inicialización del supervisor y registro de behaviours.
	•	CreatureAgent.setup() (creatureAgent.py): configuración inicial de estado y behaviours del agente criatura.
	•	Estructura de arranque con spade.run(main()) en hostAgent.py.

Inspiración del ejercicio “cyclic.py” (CyclicBehaviour y PeriodicBehaviour):
El uso de behaviours internos y ciclos de ejecución periódicos proviene del ejemplo del contador. Se adapta de forma más compleja en:
	•	GenerationAgent.RecvBehav(CyclicBehaviour): recepción continua de mensajes de criaturas para coordinar eventos y depredación.
	•	GenerationAgent.MonitorBehav(PeriodicBehaviour): verificación periódica del tiempo de generación.
	•	CreatureAgent.ReportBehav(PeriodicBehaviour): envío periódico del estado y actualización energética.
	•	CreatureAgent.RecvBehav(CyclicBehaviour): manejo de mensajes entrantes (comida, finalización, etc.).

Inspiración del Host de la Semana 10 (visualización de peces):
El diseño del Host que recibe estados y expone /fishes como endpoint JSON se basa directamente en dicho ejercicio. En el proyecto toma forma en:
	•	HostAgent.RecvBehav: almacenamiento de estados, administración de criaturas activas y registro de eliminaciones.
	•	HostAgent._start_web(): servidor aiohttp que expone /fishes, limpiando criaturas eliminadas y sincronizando con la UI.
	•	Mecanismo de limpieza temporal (removals) inspirado en la necesidad abordada en los ejemplos: evitar que mensajes tardíos reintroduzcan agentes eliminados.

**EJERCICIO SEMANA 11 - Aviones y Torre de Control**

El proyecto también toma conceptos fundamentales del ejercicio de clase basado en la simulación de aviones y una torre de control en SPADE. Ese ejercicio enseñaba cómo múltiples agentes independientes coordinan sus acciones mediante mensajes estructurados (request, ack, status) y cómo un agente central supervisa el estado global. En el proyecto, estas ideas se ven reflejadas en los siguientes componentes:

Patrón Torre–Entidad (inspirado en torreAgent.py):
En el ejercicio, la Torre recibía mensajes de los aviones, mantenía su estado y enviaba respuestas. En el proyecto, este patrón se refleja directamente en:
	•	GenerationAgent.RecvBehav (generationAgent.py): recepción continua de mensajes de criaturas, actualización de registros y validación de eventos.
	•	HostAgent.RecvBehav (hostAgent.py): comportamiento análogo a la Torre; mantiene un mapa actualizado de criaturas y notifica eliminaciones.
	•	HostAgent._start_web(): equivalente a la Torre como punto central que expone el estado global.

Patrón Entidad que reporta su estado (inspirado en avionAgent.py):
Los aviones enviaban periódicamente mensajes con posición y estado. Este patrón fue adoptado en:
	•	CreatureAgent.ReportBehav.run() (creatureAgent.py): envío periódico del estado completo de la criatura (x, y, size, speed, energy, foods_eaten).
	•	CreatureAgent.RecvBehav: recepción de instrucciones externas (finalización, confirmación de comida, remoción).
Tal como el avión informaba su ubicación y condición, las criaturas reportan su estado al supervisor.

Patrón request–response (inspirado en senderAgent.py y receiverAgent.py):
El ejercicio mostraba cómo un agente envía un mensaje y espera una respuesta coherente del receptor. En el proyecto, este patrón se mantiene en:
	•	GenerationAgent.handle_food_request() implícito dentro de RecvBehav: cuando una criatura informa que llegó a una comida, el GenerationAgent responde confirmando o rechazando la adquisición.
	•	CreatureAgent.RecvBehav: espera respuestas del GenerationAgent que modifican la energía o informan eventos.

Estructura de arranque centralizada (inspirado en all.py):
El ejercicio mostraba cómo iniciar múltiples agentes y un host coordinador desde un único archivo. Esto se refleja en:
	•	hostAgent.main(): arranca HostAgent, inicia GenerationAgent y prepara el entorno web.
	•	Uso del patrón spade.run(main()), heredado directamente del ejemplo de aviones.

Mensajes estructurados con contenido JSON (inspirado en el intercambio Torre–Avión):
En el ejercicio, los aviones enviaban diccionarios con atributos tales como altitud, posición y estado. En el proyecto, esto se replica mediante:
	•	Mensajes JSON enviados desde CreatureAgent.ReportBehav al GenerationAgent.
	•	Mensajes JSON procesados en GenerationAgent.RecvBehav y en HostAgent.RecvBehav.


**DECLARACION DE USO DE IA (INTELIGENCIA ARTIFICIAL)**

Durante la implementación del sistema se emplearon herramientas de asistencia basadas en IA como apoyo complementario al proceso de desarrollo. Estas herramientas se usaron principalmente para dinamizar el “flow” de trabajo y facilitar decisiones de diseño mientras se construía la simulación.

Principales usos de la IA en el proyecto:
	•	Idear y refinar estructuras iniciales de módulos y behaviours, manteniendo un estilo homogéneo entre agentes.
	•	Generar borradores de funciones repetitivas o plantillas base para clases (CreatureAgent, GenerationAgent, HostAgent) para acelerar el ritmo de codificación.
	•	Convertir ideas sueltas en código más claro, ayudando a mantener coherencia entre movimiento, reporte de estado y sincronización.
	•	Asistir en la documentación técnica y organización del README, permitiendo explicar mejor decisiones internas del proyecto.
	•	Apoyar el estilo de desarrollo ágil, donde se alterna entre ideación rápida, prueba, ajuste y mejora continua.

El uso de IA permitió mantener un ritmo de desarrollo fluido, estructurado y más consistente, especialmente al trabajar con múltiples agentes y comportamientos concurrentes.

------------------------------------------------------------------------------------------------------------------------------------------------
**AUTORES**
------------------------------------------------------------------------------------------------------------------------------------------------

| Nombre | Código de estudiante |
|---|---|
| Nathaly Eliane Anaya Vadillo | U202210644 |
| Leonardo Leoncio Bravo Ricapa | U20211c688 |
| Ariana Graciela Quelopana Puppo | U202122430 |
| Liam Mikael Quino Neff | U20221E167 |


------------------------------------------------------------------------------------------------------------------------------------------------
**LICENCIA**
------------------------------------------------------------------------------------------------------------------------------------------------

Este proyecto se publica bajo la licencia MIT. Consulta el archivo `LICENSE` para el texto completo.
