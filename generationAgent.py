import asyncio
import csv
import json
import os
import random
import time
import utils
from world import WorldConfig
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message

from creatureAgent import CreatureAgent


class GenerationAgent(Agent):
    """Agente que controla el mundo y las generaciones.

    - Mantiene posiciones de comida
    - Recibe reportes de criaturas y confirma comidas
    - Controla fin de generación y crea la siguiente
    """

    def __init__(self, jid, password, num_initial=10, food_count=30, space_size=(100, 100), max_generations=10):
        super().__init__(jid, password)
        self.num_initial = num_initial
        self.food_count = food_count
        self.space_size = space_size
        self.max_generations = max_generations

        # configuración del mundo (valores por defecto)
        self.config = WorldConfig()

        # Estado runtime
        self.generation = 0
        self.foods = []  # list of (x,y)
        self.creatures_info = {}  # jid -> {foods_eaten, alive}
        self.active_creature_jids = set()
        self.last_eat_time = time.time()
        # referencias a agentes spawnados para apagado ordenado
        self.spawned_agents = []
        # flag para evitar llamadas reentrantes a _end_generation
        self._ending = False

        # comenten esta linea si usan wsl
        self.summary_file = os.path.join(os.path.dirname(__file__), "generation_summary.csv")
        # CSV file for per-creature details (appended each generation)
        self.details_file = os.path.join(os.path.dirname(__file__), "generation_details.csv")

        # descomentar esto si estan usando wsl
        #script_dir = os.path.dirname(os.path.abspath(__file__))
        #self.summary_file = os.path.join(script_dir, "generation_summary.csv")

    # food placement and distance calculations delegated to utils

    async def spawn_generation(self, spawn_list=None):
        """Crea y arranca las criaturas para la generación actual.

        spawn_list: None para generación inicial; si es lista de dicts, cada dict debe
        contener 'speed' y 'energy' para el nuevo individuo.
        """
        self.generation += 1
        self.foods = utils.place_food(self.food_count, self.space_size)
        self.creatures_info = {}
        self.active_creature_jids = set()

        to_spawn = []
        if spawn_list is None:
            # crear individuos: para la generación 1 todos deben tener los mismos atributos
            if self.generation == 1:
                # usar valores provistos en config si existen, sino elegir un speed aleatorio único
                base_speed = getattr(self.config, "initial_speed", None)
                if base_speed is None:
                    base_speed = utils.random_speed()
                base_energy = getattr(self.config, "initial_energy", None)
                if base_energy is None:
                    base_energy = utils.default_energy_for_speed(base_speed)
                for i in range(self.num_initial):
                    to_spawn.append((base_speed, base_energy))
            else:
                # generaciones posteriores: individuos con velocidad/energía aleatoria (energía inversa a velocidad)
                for i in range(self.num_initial):
                    speed = utils.random_speed()
                    energy = utils.default_energy_for_speed(speed)
                    to_spawn.append((speed, energy))
        else:
            for spec in spawn_list:
                speed = spec.get("speed")
                energy = spec.get("energy")
                to_spawn.append((speed, energy))

        print(f"Generation {self.generation}: spawning {len(to_spawn)} creatures, food={len(self.foods)}")

        # arrancar agentes criatura
        i = 0
        for speed, energy in to_spawn:
            jid_base = f"creature{self.generation}_{i}"
            jid = f"{jid_base}@localhost"
            passwd = "123456abcd."
            agent = CreatureAgent(jid, passwd)
            # pasar parámetros iniciales
            agent.init_speed = speed
            agent.init_energy = energy
            agent.generation_jid = str(self.jid).split("/")[0]
            # pasar tamaño de espacio y posición inicial aleatoria
            w, h = self.space_size
            agent.space_size = self.space_size
            agent.init_x = random.uniform(0, w)
            agent.init_y = random.uniform(0, h)
            # pass world config so creature can use same parameters
            agent.config = self.config
            await agent.start(auto_register=True)
            print(f"  started {jid} speed={speed:.2f} energy={energy:.2f}")
            # registrar
            self.creatures_info[jid_base] = {"jid_full": jid, "foods_eaten": 0, "alive": True, "speed": speed, "energy": energy}
            self.active_creature_jids.add(jid)
            self.spawned_agents.append(agent)
            i += 1

    class RecvBehav(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg is None:
                return
            try:
                data = json.loads(msg.body)
            except Exception:
                print("GenerationAgent: mensaje no JSON recibido")
                return

            mtype = data.get("type")
            sender = data.get("jid") or str(msg.sender).split("/")[0]

            if mtype == "status":
                # Comprueba si hay comida cerca
                pos = (data.get("x", 0), data.get("y", 0))
                # buscar primera comida en rango
                ate = False
                remove_idx = None
                for idx, fpos in enumerate(self.agent.foods):
                    if utils.distance(pos, fpos) <= getattr(self.agent.config, "detection_radius", 1.0):
                        ate = True
                        remove_idx = idx
                        break
                if ate and remove_idx is not None:
                    fpos = self.agent.foods.pop(remove_idx)
                    self.agent.last_eat_time = time.time()
                    # actualizar contador local
                    base = sender.split("@")[0]
                    info = self.agent.creatures_info.get(base)
                    if info is not None:
                        info["foods_eaten"] += 1
                    # confirmar al creature
                    reply = Message(to=str(msg.sender).split("/")[0])
                    reply.set_metadata("performative", "inform")
                    reply.body = json.dumps({"type": "eat_confirm", "jid": sender})
                    await self.send(reply)
                    print(f"  {sender} ate food at {fpos}")
                # actualizar energía/estado en registro local para poder preservar atributos
                base = sender.split("@")[0]
                info = self.agent.creatures_info.get(base)
                if info is not None:
                    info["energy"] = data.get("energy", info.get("energy"))
                    # speed también puede actualizarse si el creature cambia (por seguridad)
                    if "speed" in data:
                        info["speed"] = data.get("speed")
                # En cualquier caso, enviar al creature el target (la comida más cercana restante)
                # para que busque de forma dirigida
                target_msg = Message(to=str(msg.sender).split("/")[0])
                target_msg.set_metadata("performative", "inform")
                if len(self.agent.foods) > 0:
                    # buscar comida más cercana al creature
                    nearest = None
                    nearest_d = None
                    for f in self.agent.foods:
                        d = utils.distance(pos, f)
                        if nearest is None or d < nearest_d:
                            nearest = f
                            nearest_d = d
                    target_msg.body = json.dumps({"type": "target", "x": nearest[0], "y": nearest[1]})
                else:
                    target_msg.body = json.dumps({"type": "no_target"})
                await self.send(target_msg)
            elif mtype == "finished":
                # Marca criatura como finalizada
                base = sender.split("@")[0]
                info = self.agent.creatures_info.get(base)
                if info is not None:
                    info["alive"] = False
                    info["foods_eaten"] = data.get("foods_eaten", info.get("foods_eaten", 0))
                    info["energy"] = data.get("energy", info.get("energy"))
                # eliminar de activos
                jid_full = str(msg.sender).split("/")[0]
                if jid_full in self.agent.active_creature_jids:
                    self.agent.active_creature_jids.remove(jid_full)
                print(f"  {sender} finished (foods={data.get('foods_eaten')})")

    class MonitorBehav(PeriodicBehaviour):
        async def run(self):
            # Si no quedan creatures activos -> finalizar generación
            if len(self.agent.active_creature_jids) == 0:
                await self.agent._end_generation()
                return

            # Si no queda comida y no se ha comido nada en los últimos `last_eat_grace` -> terminar generación
            if len(self.agent.foods) == 0 and (time.time() - self.agent.last_eat_time) > getattr(self.agent.config, "last_eat_grace", 3.0):
                # instruir a las criaturas activas a terminar
                for jid in list(self.agent.active_creature_jids):
                    msg = Message(to=jid)
                    msg.set_metadata("performative", "inform")
                    msg.body = json.dumps({"type": "generation_end"})
                    await self.send(msg)
                # esperar un momento y luego forzar el end
                await asyncio.sleep(1)
                await self.agent._end_generation()

    async def _end_generation(self):
        if self._ending:
            return
        self._ending = True
        print(f"Generation {self.generation} ending. Evaluating population...")

        # pedir a las criaturas activas que finalicen y esperar sus informes
        for jid in list(self.active_creature_jids):
            msg = Message(to=jid)
            msg.set_metadata("performative", "inform")
            msg.body = json.dumps({"type": "generation_end"})
            await self.send(msg)

        # esperar un breve periodo para recolectar mensajes 'finished'
        await asyncio.sleep(1.5)

        # Forzar parada de los agentes que siguen activos
        if hasattr(self, "spawned_agents") and self.spawned_agents:
            for ag in list(self.spawned_agents):
                try:
                    if str(ag.jid).split("/")[0] in self.active_creature_jids:
                        await ag.stop()
                except Exception:
                    pass
            self.spawned_agents = []

        # asegurar que active_creature_jids está vacio
        self.active_creature_jids = set()

        # calcular estadísticas y nueva lista de specs para siguiente generación
        next_specs = []
        survivors = 0
        deaths = 0
        reproducers = 0
        speeds = []
        foods_list = []

        for base, info in list(self.creatures_info.items()):
            foods = info.get("foods_eaten", 0)
            speed_parent = info.get("speed", utils.random_speed())
            # Preserve reported energy, but if it's non-positive, reset to default for that speed
            reported_energy = info.get("energy", None)
            default_energy = utils.default_energy_for_speed(speed_parent)
            if reported_energy is None:
                energy_parent = default_energy
            else:
                try:
                    # handle possible non-numeric
                    energy_parent = float(reported_energy)
                except Exception:
                    energy_parent = default_energy
            if energy_parent <= 0:
                energy_parent = default_energy
            speeds.append(speed_parent)
            foods_list.append(foods)
            if foods == 0:
                deaths += 1
                continue
            elif foods == 1:
                # parent survives, keep same speed and remaining energy
                next_specs.append({"speed": speed_parent, "energy": energy_parent})
                survivors += 1
            else:
                # parent survives AND produces one child
                next_specs.append({"speed": speed_parent, "energy": energy_parent})
                # child with random speed and energy (inverse relation)
                child_speed = utils.random_speed()
                child_energy = utils.default_energy_for_speed(child_speed)
                next_specs.append({"speed": child_speed, "energy": child_energy})
                survivors += 1
                reproducers += 1

        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        avg_foods = sum(foods_list) / len(foods_list) if foods_list else 0

        print(f"  survivors/offspring for next gen: {len(next_specs)}")

        # escribir resumen CSV
        header = ["generation", "initial", "deaths", "survivors", "reproducers", "next_population", "avg_speed", "avg_foods"]
        row = [self.generation, len(speeds), deaths, survivors, reproducers, len(next_specs), f"{avg_speed:.3f}", f"{avg_foods:.3f}"]
        write_header = not os.path.exists(self.summary_file)
        try:
            with open(self.summary_file, "a", newline="", encoding="utf-8") as csvf:
                writer = csv.writer(csvf)
                if write_header:
                    writer.writerow(header)
                writer.writerow(row)
            print(f"Summary written to {self.summary_file}")
        except Exception as e:
            print(f"Failed writing summary CSV to {self.summary_file}: {e}")
            import traceback
            traceback.print_exc()

        # escribir detalles por criatura
        detail_header = ["generation", "jid_base", "jid_full", "speed", "energy", "foods_eaten", "alive", "is_reproducer"]
        write_details_header = not os.path.exists(self.details_file)
        try:
            with open(self.details_file, "a", newline="", encoding="utf-8") as df:
                dw = csv.writer(df)
                if write_details_header:
                    dw.writerow(detail_header)
                for base, info in list(self.creatures_info.items()):
                    jid_full = info.get("jid_full")
                    speed = info.get("speed")
                    energy = info.get("energy")
                    foods = info.get("foods_eaten", 0)
                    # alive flag refers to survival to next generation (foods>0),
                    # not whether the agent process was still running at the snapshot.
                    alive_flag = True if foods > 0 else False
                    is_reproducer = True if foods >= 2 else False
                    # format numbers sensibly
                    speed_s = f"{speed:.3f}" if isinstance(speed, (int, float)) else str(speed)
                    energy_s = f"{energy:.3f}" if isinstance(energy, (int, float)) else str(energy)
                    dw.writerow([self.generation, base, jid_full, speed_s, energy_s, foods, alive_flag, is_reproducer])
        except Exception as e:
            print(f"Failed writing details CSV: {e}")

        # si no quedan individuos -> terminar simulación
        if len(next_specs) == 0 or self.generation >= self.max_generations:
            print("Simulation finished (no descendants or max generations reached).")
            await self.stop()
            return

        # spawn siguiente generación
        await asyncio.sleep(0.5)
        self._ending = False
        await self.spawn_generation(spawn_list=next_specs)

    async def setup(self):
        print(f"GenerationAgent {str(self.jid)} started")
        # añadir behaviours primero para no perder mensajes entrantes
        self.add_behaviour(self.RecvBehav())
        self.add_behaviour(self.MonitorBehav(period=1))
        # iniciar primera generación
        await self.spawn_generation()


if __name__ == "__main__":
    print("Este archivo define `GenerationAgent`. Ejecutarlo desde `hostAgent`.")

