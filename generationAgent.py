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
from logger_setup import get_logger

logger = get_logger('generation')


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
        # mapa jid_full -> agent para control directo (uso en depredación)
        self.spawned_map = {}
        # flag para evitar llamadas reentrantes a _end_generation
        self._ending = False
            # archivos CSV para reportes
            # crear directorio de reportes y rutas de archivos CSV
        self.report_dir = os.path.join(os.path.dirname(__file__), "report")
        os.makedirs(self.report_dir, exist_ok=True)
        self.summary_file = os.path.join(self.report_dir, "generation_summary.csv")
        # CSV file for per-creature details (appended each generation)
        self.details_file = os.path.join(self.report_dir, "generation_details.csv")
        # CSV file for predation events
        self.predation_file = os.path.join(self.report_dir, "predation_events.csv")

    # colocación de comida y cálculos de distancia delegados a `utils`

    async def spawn_generation(self, spawn_list=None):
        """Crea y arranca las criaturas para la generación actual.

        spawn_list: None para generación inicial; si es lista de dicts, cada dict debe
        contener 'speed' y 'energy' para el nuevo individuo.
        """
        self.generation += 1
        self.foods = utils.place_food(self.food_count, self.space_size)
        # notify host UI that a new generation starts so it can clear previous creatures
        try:
            host_j = getattr(self, "host_jid", None)
            if host_j:
                nm = Message(to=host_j)
                nm.set_metadata("performative", "inform")
                nm.body = json.dumps({"type": "generation_start", "generation": self.generation})
                await self.send(nm)
        except Exception:
            pass
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
                base_size = getattr(self.config, "initial_size", None)
                if base_size is None:
                    base_size = utils.random_size()
                base_sense = getattr(self.config, "initial_sense", None)
                if base_sense is None:
                    base_sense = utils.random_sense()
                for i in range(self.num_initial):
                    to_spawn.append((base_speed, base_energy, base_size, base_sense))
            else:
                # generaciones posteriores: individuos con velocidad/energía aleatoria (energía inversa a velocidad)
                for i in range(self.num_initial):
                    speed = utils.random_speed()
                    energy = utils.default_energy_for_speed(speed)
                    size = utils.random_size()
                    sense = utils.random_sense()
                    to_spawn.append((speed, energy, size, sense))
        else:
            for spec in spawn_list:
                speed = spec.get("speed")
                energy = spec.get("energy")
                # preserve size and sense when provided; otherwise randomize
                size = spec.get("size", utils.random_size())
                sense = spec.get("sense", utils.random_sense())
                to_spawn.append((speed, energy, size, sense))

        print(f"Generation {self.generation}: spawning {len(to_spawn)} creatures, food={len(self.foods)}")
        try:
            logger.info(f"Generation {self.generation}: spawning {len(to_spawn)} creatures, food={len(self.foods)}")
        except Exception:
            pass

        # arrancar agentes criatura
        i = 0
        for tup in to_spawn:
            # soporta tupla tanto (speed, energy) como (speed, energy, size, sense)
            if len(tup) >= 4:
                speed, energy, size, sense = tup[0], tup[1], tup[2], tup[3]
            else:
                speed, energy = tup[0], tup[1]
                size = utils.random_size()
                sense = utils.random_sense()
            jid_base = f"creature{self.generation}_{i}"
            jid = f"{jid_base}@localhost"
            passwd = "123456abcd."
            agent = CreatureAgent(jid, passwd)
            # pasar parámetros iniciales
            agent.init_speed = speed
            agent.init_energy = energy
            agent.init_size = size
            agent.init_sense = sense
            # pass host_jid so creatures can also report to Host UI
            agent.host_jid = getattr(self, "host_jid", None)
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
            try:
                logger.info(f"started {jid} speed={speed:.2f} energy={energy:.2f} size={size:.3f} sense={sense:.3f}")
            except Exception:
                pass
            # map for direct control
            self.spawned_map[jid] = agent
            # registrar (incluye tamaño y sense)
            self.creatures_info[jid_base] = {"jid_full": jid, "foods_eaten": 0, "alive": True, "speed": speed, "energy": energy, "size": size, "sense": sense, "x": agent.init_x, "y": agent.init_y}
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
                    try:
                        logger.info(f"{sender} ate food at {fpos}")
                    except Exception:
                        pass
                # actualizar energía/estado en registro local para poder preservar atributos
                base = sender.split("@")[0]
                info = self.agent.creatures_info.get(base)
                if info is not None:
                    info["energy"] = data.get("energy", info.get("energy"))
                    # actualizar posición/tamaño/sense si vienen en el status
                    info["x"] = data.get("x", info.get("x"))
                    info["y"] = data.get("y", info.get("y"))
                    if "size" in data:
                        info["size"] = data.get("size")
                    if "sense" in data:
                        info["sense"] = data.get("sense")
                    # speed también puede actualizarse si el creature cambia (por seguridad)
                    if "speed" in data:
                        info["speed"] = data.get("speed")

                    # Predation: the reporting creature may attack nearby smaller creatures
                    try:
                        predator_size = float(info.get("size", 0))
                        predator_sense = float(info.get("sense", 0))
                    except Exception:
                        predator_size = info.get("size", 0)
                        predator_sense = info.get("sense", 0)
                    cfg = getattr(self.agent, "config", None)
                    attack_size_ratio = getattr(cfg, "attack_size_ratio", 1.2) if cfg is not None else 1.2
                    attack_radius = getattr(cfg, "attack_radius", 1.0) if cfg is not None else 1.0
                    prey_food_scale = getattr(cfg, "prey_food_scale", 1.0) if cfg is not None else 1.0
                    sense_radius_mult = getattr(cfg, "sense_radius_mult", 0.5) if cfg is not None else 0.5

                    # scale attack radius by predator sense (more sense -> larger effective radius)
                    effective_attack_radius = attack_radius * (1.0 + predator_sense * sense_radius_mult)

                    # iterate over known creatures and attempt to eat eligible prey
                    for other_base, other_info in list(self.agent.creatures_info.items()):
                        if other_base == base:
                            continue
                        if not other_info.get("alive", False):
                            continue
                        # need position and size for the prey
                        ox = other_info.get("x", None)
                        oy = other_info.get("y", None)
                        o_size = other_info.get("size", None)
                        if ox is None or oy is None or o_size is None:
                            continue
                        # distance between predator (pos) and prey
                        d = utils.distance(pos, (ox, oy))
                        if d <= effective_attack_radius and predator_size >= (attack_size_ratio * float(o_size)):
                                    # el depredador mata exitosamente a la presa
                            prey_jid = other_info.get("jid_full")
                            # mark prey as dead in registry
                            other_info["alive"] = False
                            # clear prey's food count so it won't reproduce
                            other_info["foods_eaten"] = 0
                            other_info["energy"] = 0
                            # remove from active set if present
                            if prey_jid in self.agent.active_creature_jids:
                                try:
                                    self.agent.active_creature_jids.remove(prey_jid)
                                except Exception:
                                    pass
                            # increase predator's foods_eaten and energy according to prey size
                            gained = prey_food_scale * (float(o_size) ** 3)
                            info["foods_eaten"] = info.get("foods_eaten", 0) + 1
                            info["energy"] = float(info.get("energy", 0)) + gained
                            print(f"  {sender} predated on {other_base} at d={d:.2f}, energy+={gained:.2f}")
                            try:
                                logger.info(f"{sender} predated on {other_base} at d={d:.2f}, energy+={gained:.2f}")
                            except Exception:
                                pass
                            # enviar `eat_confirm` al depredador para que el agente local también actualice su estado
                            try:
                                predator_jid_full = str(msg.sender).split("/")[0]
                            except Exception:
                                predator_jid_full = sender
                            pred_ack = Message(to=predator_jid_full)
                            pred_ack.set_metadata("performative", "inform")
                            pred_ack.body = json.dumps({"type": "eat_confirm", "jid": sender, "energy_gain": gained, "prey": other_base})
                            await self.send(pred_ack)
                            # registrar evento de depredación en CSV
                            try:
                                write_header = not os.path.exists(self.agent.predation_file)
                                with open(self.agent.predation_file, "a", newline="", encoding="utf-8") as pf:
                                    pw = csv.writer(pf)
                                    if write_header:
                                        pw.writerow(["generation", "time", "predator_base", "predator_jid", "prey_base", "prey_jid", "energy_gained", "pred_x", "pred_y", "prey_x", "prey_y", "distance"])
                                    pw.writerow([self.agent.generation, time.time(), base, predator_jid_full, other_base, prey_jid, f"{gained:.3f}", f"{pos[0]:.3f}", f"{pos[1]:.3f}", f"{ox:.3f}", f"{oy:.3f}", f"{d:.3f}"])
                            except Exception as e:
                                logger.error(f"Failed writing predation event: {e}")
                            # instruir a la presa para que termine (muerta). Preferir detener el agente
                            if prey_jid:
                                prey_agent = self.agent.spawned_map.get(prey_jid)
                                if prey_agent is not None:
                                    try:
                                        # stop the prey agent directly to avoid sending messages to stopped agents
                                        await prey_agent.stop()
                                    except Exception:
                                        pass
                                    # eliminar el mapeo y la entrada del conjunto activo si están presentes
                                    self.agent.spawned_map.pop(prey_jid, None)
                                    if prey_jid in self.agent.active_creature_jids:
                                        try:
                                            self.agent.active_creature_jids.remove(prey_jid)
                                        except Exception:
                                            pass
                                    # notificar al Host UI que la presa fue eliminada (killed)
                                    try:
                                        host_j = getattr(self.agent, "host_jid", None)
                                        if host_j:
                                            rem = Message(to=host_j)
                                            rem.set_metadata("performative", "inform")
                                            rem.body = json.dumps({"type": "creature_removed", "jid": prey_jid, "reason": "killed", "killed_by": sender})
                                            await self.send(rem)
                                    except Exception:
                                        pass
                                else:
                                    # alternativa: enviar generation_end si no tenemos el objeto agente
                                    endm = Message(to=prey_jid)
                                    endm.set_metadata("performative", "inform")
                                    endm.body = json.dumps({"type": "generation_end", "killed_by": sender})
                                    await self.send(endm)
                                    # también notificar al Host UI en la ruta alternativa
                                    try:
                                        host_j = getattr(self.agent, "host_jid", None)
                                        if host_j:
                                            rem = Message(to=host_j)
                                            rem.set_metadata("performative", "inform")
                                            rem.body = json.dumps({"type": "creature_removed", "jid": prey_jid, "reason": "killed", "killed_by": sender})
                                            await self.send(rem)
                                    except Exception:
                                        pass
                            # do not allow multiple predators to eat the same prey (we marked it dead)
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
                    info["foods_eaten"] = data.get("foods_eaten", info.get("foods_eaten", 0))
                    info["energy"] = data.get("energy", info.get("energy"))
                # eliminar de activos y del mapa de spawn si existe
                jid_full = str(msg.sender).split("/")[0]
                if jid_full in self.agent.active_creature_jids:
                    try:
                        self.agent.active_creature_jids.remove(jid_full)
                    except Exception:
                        pass
                # remove from spawned_map if present
                try:
                    self.agent.spawned_map.pop(jid_full, None)
                except Exception:
                    pass

                # compute a reason for finishing: killed/exhausted/alive/will reproduce
                foods_num = data.get("foods_eaten", info.get("foods_eaten") if info is not None else 0)
                alive_flag = info.get("alive", True) if info is not None else True
                if not alive_flag:
                    reason = "killed"
                else:
                    try:
                        fnum = int(foods_num)
                    except Exception:
                        fnum = foods_num
                    if isinstance(fnum, int):
                        if fnum == 0:
                            reason = "exhausted"
                        elif fnum == 1:
                            reason = "alive"
                        else:
                            reason = "will reproduce"
                    else:
                        reason = "finished"

                print(f"  {sender} finished (foods={foods_num}; {reason})")

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
        try:
            logger.info(f"Generation {self.generation} ending. Evaluating population...")
        except Exception:
            pass

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

        # Notify host UI that remaining active creatures are being removed (generation end)
        try:
            host_j = getattr(self, "host_jid", None)
            if host_j:
                for jid_full in list(self.active_creature_jids):
                    try:
                        rem = Message(to=host_j)
                        rem.set_metadata("performative", "inform")
                        rem.body = json.dumps({"type": "creature_removed", "jid": jid_full, "reason": "generation_end"})
                        await self.send(rem)
                    except Exception:
                        pass
        except Exception:
            pass

        # asegurar que active_creature_jids está vacio
        self.active_creature_jids = set()

        # calcular estadísticas y nueva lista de specs para siguiente generación
        next_specs = []
        survivors = 0
        deaths = 0
        reproducers = 0
        speeds = []
        foods_list = []
        sizes = []
        senses = []
        survivors_bases = []
        reproducers_bases = []

        for base, info in list(self.creatures_info.items()):
            foods = info.get("foods_eaten", 0)
            speed_parent = info.get("speed", utils.random_speed())
            size_parent = info.get("size", utils.random_size())
            sense_parent = info.get("sense", utils.random_sense())
            # Reset parent energy for next generation to the default for their speed
            default_energy = utils.default_energy_for_speed(speed_parent)
            energy_parent = default_energy
            speeds.append(speed_parent)
            foods_list.append(foods)
            sizes.append(size_parent)
            senses.append(sense_parent)
            # if the creature was killed by predation or otherwise marked not alive, count as death
            if not info.get("alive", True):
                deaths += 1
                continue
            if foods == 0:
                deaths += 1
                continue
            elif foods == 1:
                # parent survives, keep same speed and remaining energy
                # keep speed, size and sense; reset energy to default
                next_specs.append({"speed": speed_parent, "energy": energy_parent, "size": size_parent, "sense": sense_parent})
                survivors_bases.append(base)
                survivors += 1
            else:
                # parent survives AND produces one child
                # parent keeps same speed/size/sense and resets energy
                next_specs.append({"speed": speed_parent, "energy": energy_parent, "size": size_parent, "sense": sense_parent})
                survivors_bases.append(base)
                # child with random speed and energy (inverse relation)
                child_speed = utils.random_speed()
                child_energy = utils.default_energy_for_speed(child_speed)
                child_size = utils.random_size()
                child_sense = utils.random_sense()
                next_specs.append({"speed": child_speed, "energy": child_energy, "size": child_size, "sense": child_sense})
                reproducers_bases.append(base)
                survivors += 1
                reproducers += 1

        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        avg_foods = sum(foods_list) / len(foods_list) if foods_list else 0
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        avg_sense = sum(senses) / len(senses) if senses else 0

        print(f"  survivors/offspring for next gen: {len(next_specs)}")
        # debug: list survivors/reproducers and next_specs content
        try:
            print(f"  survivors bases: {survivors_bases}")
            print(f"  reproducers bases: {reproducers_bases}")
            print(f"  next_specs count detail: parents={len(survivors_bases)}, reproducers={len(reproducers_bases)}, total_specs={len(next_specs)}")
        except Exception:
            pass

        # escribir resumen CSV
        header = ["generation", "initial", "deaths", "survivors", "reproducers", "next_population", "avg_speed", "avg_foods", "avg_size", "avg_sense"]
        row = [self.generation, len(speeds), deaths, survivors, reproducers, len(next_specs), f"{avg_speed:.3f}", f"{avg_foods:.3f}", f"{avg_size:.3f}", f"{avg_sense:.3f}"]
        write_header = not os.path.exists(self.summary_file)
        try:
            with open(self.summary_file, "a", newline="", encoding="utf-8") as csvf:
                writer = csv.writer(csvf)
                if write_header:
                    writer.writerow(header)
                writer.writerow(row)
        except Exception as e:
            print(f"Failed writing summary CSV: {e}")

        # escribir detalles por criatura
        detail_header = ["generation", "jid_base", "jid_full", "speed", "energy", "size", "sense", "foods_eaten", "alive", "is_reproducer"]
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
                    size = info.get("size")
                    sense = info.get("sense")
                    foods = info.get("foods_eaten", 0)
                    # alive flag refers to whether creature survived (not killed by predation)
                    alive_flag = True if info.get("alive", False) else False
                    # a reproducer is an alive creature that ate >=2
                    is_reproducer = True if (alive_flag and foods >= 2) else False
                    # format numbers sensibly
                    speed_s = f"{speed:.3f}" if isinstance(speed, (int, float)) else str(speed)
                    energy_s = f"{energy:.3f}" if isinstance(energy, (int, float)) else str(energy)
                    size_s = f"{size:.3f}" if isinstance(size, (int, float)) else str(size)
                    sense_s = f"{sense:.3f}" if isinstance(sense, (int, float)) else str(sense)
                    dw.writerow([self.generation, base, jid_full, speed_s, energy_s, size_s, sense_s, foods, alive_flag, is_reproducer])
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
