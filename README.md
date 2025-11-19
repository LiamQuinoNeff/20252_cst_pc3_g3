# PC3 — Mini-simulación de selección natural (SPADE)

Pequeño proyecto con agentes SPADE que simula generaciones de criaturas que se mueven, comen y se reproducen según reglas simples.

**Descripción**
- Cada `GenerationAgent` crea una generación de `CreatureAgent` y distribuye comida en un área 2D.
- Las criaturas informan su posición/energía periódicamente; si alcanzan comida la comen y aumentan su contador.
- Reglas de supervivencia/reproducción (versión actual):
  - 0 comidas -> muere
  - 1 comida  -> sobrevive (padre permanece)
  - >=2 comidas -> padre sobrevive y además genera 1 hijo
- La simulación escribe un resumen por generación en `generation_summary.csv` (ubicado en la carpeta `pc3`).

- Además, se genera `generation_details.csv` con una fila por criatura en cada generación: `generation, jid_base, jid_full, speed, energy, foods_eaten, alive, is_reproducer`.
- La simulación escribe un resumen por generación en `generation_summary.csv` (ubicado en la carpeta `pc3`).

**Nota sobre atributos iniciales**
- Todas las criaturas de la generación 1 comparten los mismos valores de `speed` y `energy`. Puedes configurar valores por defecto en `world.py` usando `initial_speed` e `initial_energy`. Si se dejan en `None`, la generación 1 elegirá un `speed` aleatorio único y calculará la energía correspondiente.
- A partir de la segunda generación los individuos tienen `speed` y `energy` aleatorios (energía calculada en función inversa a la velocidad).

**Requisitos**
- Python 3.8+ (se probó con entornos que contienen SPADE). 
- SPADE instalado en el entorno virtual (ver `requirements.txt` del repo principal si existe).

**Uso**
1. Activar tu entorno virtual (si aplica).
2. Abrir una terminal en `C:\SPADE\pc3`.
3. Ejecutar:

```powershell
py hostAgent.py
```

La ejecución mostrará logs de cada criatura y generación. Al finalizar cada generación se añadirá/actualizará `generation_summary.csv`.

Leer comentarios en `generationAgent.py` para la creación de `generation_summary.csv` en WSL (líneas 46 a 51).

**Archivos importantes en `20252_cst_pc3_g3`**
- `hostAgent.py` — lanzador / punto de entrada.
- `generationAgent.py` — controla el ciclo de generaciones y la lógica de evaluación.
- `creatureAgent.py` — definición del agente criatura (movimiento, energía, mensajes).
- `utils.py` / `world.py` — utilidades y configuración del mundo.
- `generation_summary.csv` — resumen por generación (omitido por defecto en git via `.gitignore`).

**Licencia**
Este proyecto se entrega bajo licencia MIT — adáptalo según prefieras.
