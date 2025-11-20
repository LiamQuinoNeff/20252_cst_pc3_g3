# Simulación SPADE: Selección Natural (Proyecto)

------------------------------------------------------------------------------------------------------------------------------------------------
Introducción
------------------------------------------------------------------------------------------------------------------------------------------------

Este proyecto implementa una simulación de selección natural utilizando agentes autónomos construidos con SPADE.
El sistema recrea un ecosistema básico donde múltiples criaturas operan de manera independiente, consumiendo energía, moviéndose dentro de un entorno discreto, buscando comida, interactuando entre sí y pudiendo morir por depredación o agotamiento energético.

La ejecución completa incluye
	1.	Creación de agentes y del entorno.
	2.	Ciclo de vida de cada generación.
	3.	Visualización en tiempo real mediante interfaz web.
	4.	Registro detallado de eventos, depredación y resultados.

La arquitectura se basa en comunicación asincrónica entre agentes utilizando XMPP y mensajes periódicos de estado, donde HostAgent actúa como punto de observación y sincronización para la UI.

------------------------------------------------------------------------------------------------------------------------------------------------
Agentes del sistema
------------------------------------------------------------------------------------------------------------------------------------------------

`HostAgent`
Es el agente encargado de:
- Servir la interfaz web.
- Exponer el estado global del mundo mediante la ruta /fishes.
- Mantener un diccionario actualizado de criaturas activas.
- Recibir mensajes de estados enviados por cada criatura.
- Registrar eliminaciones mediante la lista de removals, utilizada para efectos visuales.
- Manejar la ventana de protección contra reintroducción de criaturas eliminadas recientemente.
- Iniciar la simulación y lanzar el GenerationAgent.

Es el agente más cercano a la interfaz e integra la parte visual con la parte lógica.

`GenerationAgent`
Coordina la simulación como un controlador central. Sus funciones principales son:
- Inicializar cada generación y colocar comida en el mapa.
- Crear una cantidad configurable de criaturas (cada una ejecutándose como un agente independiente).
- Supervisar depredación, muerte, agotamiento energético y demás eventos.
- Recolectar información relevante para generar métricas de la generación.
- Determinar cuándo finaliza la generación y preparar los archivos CSV.
- Enviar mensajes al HostAgent para actualizar la interfaz.
- Gestionar el tiempo de vida de las criaturas y condiciones de término.

Este agente actúa como supervisor y recolector de estadística.

`CreatureAgent`
Cada CreatureAgent se comporta como una entidad autónoma. Su ciclo de vida incluye:
- Movimiento dentro de la cuadrícula basada en reglas simples o heurísticas.
- Consumo constante de energía.
- Detección y consumo de comida si se encuentra en posiciones cercanas.
- Reporte periódico de estado a HostAgent y GenerationAgent.
- Finalización del ciclo al morir, agotarse o ser depredado.

La criatura no tiene información global del mapa, solo sus percepciones y los datos proporcionados por GenerationAgent.

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
Funciones auxiliares como cálculos de distancia, generación de pellets, posiciones válidas y soporte general para cálculos del mapa.

`logger_setup.py`
Configuración del logger unificado. Guarda todo en report/run.log.

`report/`
Contiene los resultados generados automáticamente:
- generation_summary.csv
- generation_details.csv
- predation_events.csv
- run.log

`static/`
Archivos de la interfaz web.
- index.html: archivo principal de visualización.
- style.css: estilos para el canvas y la leyenda.
- app.js: código que hace polling de /fishes y dibuja objetos en el canvas.

------------------------------------------------------------------------------------------------------------------------------------------------
Funcionamiento interno de la interfaz web
------------------------------------------------------------------------------------------------------------------------------------------------

La interfaz funciona mediante una consulta repetitiva al endpoint /fishes.
Cada 250 ms, el archivo app.js realiza las siguientes acciones:
1.	Solicita el estado global al servidor HostAgent.
2.	Traduce las criaturas en elementos visuales:
	-	Color gris si no ha comido.
	-	Color azul si ha comido una vez.
	-	Color rojo si está lista para reproducirse.
3.	Dibuja comidas y elementos del mapa.
4.	Dibuja un flash en posiciones donde una criatura ha sido eliminada recientemente.
5.	Ajusta automáticamente escalas del mundo según los valores de WorldConfig.

El canvas se redibuja completamente en cada ciclo para mostrar cambios en tiempo real.

------------------------------------------------------------------------------------------------------------------------------------------------
Modelo de comunicación
------------------------------------------------------------------------------------------------------------------------------------------------

Los agentes SPADE se comunican por mensajes XMPP.
Cada CreatureAgent envía periódicamente mensajes de estado al HostAgent, tales como:
- status
- creature_removed
- finished

El HostAgent no solo los recibe sino que también los ordena temporalmente, evitando inconsistencias debidas a mensajes tardíos.

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
Contiene métricas agregadas de cada generación, incluyendo número total de criaturas, comidas, depredaciones, supervivientes y duración.

generation_details.csv
Reporte individual por criatura, con información de energía inicial, comida consumida, tiempo de vida, posición final y otros atributos.

predation_events.csv
Lista cronológica de eventos de depredación con predador, presa y coordenadas del evento.

------------------------------------------------------------------------------------------------------------------------------------------------
Diagnóstico y depuración
------------------------------------------------------------------------------------------------------------------------------------------------

`Para buscar información específica en el log:`
powershell
Select-String -Path .\report\run.log -Pattern "creature9_7"

`Para ver las últimas líneas del archivo:`
powershell
Get-Content .\report\run.log -Tail 200

------------------------------------------------------------------------------------------------------------------------------------------------
Parámetros configurables
------------------------------------------------------------------------------------------------------------------------------------------------

Los parámetros principales del mundo pueden modificarse en WorldConfig. Algunos de ellos:
- Dimensiones del mapa
- Energía inicial de las criaturas
- Energía ganada al comer
- Cantidad de pellets por generación
- Número de criaturas iniciales
- Duración máxima de la generación
- Intervalo de reporte de estado
- Frecuencia de refresco de la UI
- Control de depredación

Si se desea mayor flexibilidad, ciertos valores actualmente codificados, como el tiempo de protección de reintroducción, pueden trasladarse a WorldConfig.
