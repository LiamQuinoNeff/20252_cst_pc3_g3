# PC3 — Simulación de selección natural (SPADE)

Pequeño proyecto con agentes SPADE que simula generaciones de criaturas que se mueven, comen y se reproducen según reglas simples.

**Descripción**
- Cada `GenerationAgent` crea una generación de `CreatureAgent` y distribuye comida en un área 2D.
- Las criaturas informan su posición/energía periódicamente; si alcanzan comida la comen y aumentan su contador.
- Reglas de supervivencia/reproducción (versión actual):
  - 0 comidas -> muere
  - 1 comida  -> sobrevive (padre permanece)
  - >=2 comidas -> padre sobrevive y además genera 1 hijo
- La simulación escribe un resumen por generación en `generation_summary.csv` (ubicado en la carpeta `pc3`).

**Requisitos**
- Python 3.8+. 
- SPADE instalado en un entorno virtual.

**Uso**
1. Activar tu entorno virtual (si aplica).
2. Abrir una terminal en `.\20252_cst_pc3_g3`.
3. Ejecutar:

```powershell
py hostAgent.py
```

La ejecución mostrará logs de cada criatura y generación. Al finalizar cada generación se añadirá/actualizará `generation_summary.csv`.

**Archivos importantes en `20252_cst_pc3_g3`**
- `hostAgent.py` — lanzador / punto de entrada.
- `generationAgent.py` — controla el ciclo de generaciones y la lógica de evaluación.
- `creatureAgent.py` — definición del agente criatura (movimiento, energía, mensajes).
- `utils.py` / `world.py` — utilidades y configuración del mundo.
- `generation_summary.csv` — resumen por generación (omitido por defecto en git via `.gitignore`).

**Licencia**
Este proyecto se entrega bajo licencia MIT.


