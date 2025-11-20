# Simulación SPADE: Selección Natural (Proyecto)

Breve descripción
------------------
Este proyecto es una mini-simulación de selección natural implementada con agentes SPADE. Hay tres tipos principales de agentes:

- `HostAgent` — espejo para la interfaz web; recibe estados (`status`) y notificaciones (`finished`, `creature_removed`) y sirve la UI en `http://localhost:10000/static/index.html`.
- `GenerationAgent` — controlador de la generación: coloca comida, crea `CreatureAgent`, detecta predación, escribe CSVs de resultados y finaliza generaciones.
- `CreatureAgent` — representa una criatura: se mueve, consume energía, come pellets y reporta su estado.

Archivos importantes
-------------------
- `hostAgent.py` — agente host y servidor web (ruta `/fishes`).
- `generationAgent.py` — lógica de generación, depredación y reportes CSV.
- `creatureAgent.py` — comportamiento de la criatura (movimiento, reporte, terminar).
- `world.py` — configuración del mundo (`WorldConfig`).
- `utils.py` — utilidades (distancia, generación de comida, etc.).
- `logger_setup.py` — configuración del logger que escribe `report/run.log`.
- `report/` — carpeta donde se generan: `generation_summary.csv`, `generation_details.csv`, `predation_events.csv`, `run.log`.
- `static/` — archivos de la interfaz web (canvas polling `/fishes`).

Cómo ejecutar
--------------
1. Activar el entorno virtual (si corresponde):

```powershell
& C:/SPADE/cst/Scripts/Activate.ps1
```

2. Ejecutar el host (inicia GenerationAgent y la UI):

```powershell
py hostAgent.py
```

3. Abrir la UI automática o navegar a:

```
http://localhost:10000/static/index.html
```

Salida y reportes
-----------------
- `report/run.log`: registro rotativo con eventos principales (INFO). Útil para depuración de mensajes perdidos/ordenados.
- `report/generation_summary.csv`: resumen por generación.
- `report/generation_details.csv`: línea por criatura con sus atributos y resultados.
- `report/predation_events.csv`: eventos de depredación (predador, presa, posición, energía ganada).

Notas importantes
-----------------
- La interfaz web consulta `/fishes` (host) cada 250 ms y dibuja las criaturas. Cuando `HostAgent` recibe un `finished` o `creature_removed` añade una entrada en `removals` para que la UI haga un flash de eliminación.
- Se añadió una protección en `hostAgent.py` que evita re-agregar al mapa de criaturas (`self.fishes`) a un JID que fue removido en los últimos 3 segundos. Esto mitiga carreras donde un `status` tardío reintroduce una criatura ya eliminada.
- Comentarios y docstrings principales fueron traducidos al español para estandarizar la documentación en el código.

Configuraciones y ajustes rápidos
---------------------------------
- Ajustar parámetros del mundo en `WorldConfig` (`world.py`).
- Cambiar la ventana de ignorados (3s) puede realizarse en `hostAgent.py` o refactorizar para añadirlo a `WorldConfig`.

Diagnóstico y depuración
------------------------
- Para buscar eventos concretos en el log:

```powershell
Select-String -Path .\report\run.log -Pattern "creature9_7"
# o ver las últimas 200 líneas
Get-Content .\report\run.log -Tail 200
```

Contribuciones
--------------
Si quieres que traduzca también los docstrings en `tests/` y `docs/`, o que haga la configuración de `WorldConfig` más accesible (ej. añadir `removed_ignore_seconds`), dímelo y lo implemento.

Licencia
--------
Contenido para uso académico y didáctico (adaptar según necesidad).