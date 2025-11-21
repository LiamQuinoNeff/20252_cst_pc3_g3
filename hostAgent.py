import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from generationAgent import GenerationAgent
from world import WorldConfig
import asyncio
import aiohttp.web
import os
import json
import webbrowser
import time
from logger_setup import get_logger

logger = get_logger('host')

class HostAgent(Agent):
    class RecvBehav(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg is None:
                return
            try:
                data = json.loads(msg.body)
            except Exception:
                return
            # Registrar en nivel DEBUG cada evento recibido para trazabilidad
            try:
                logger.info(f"Host received: {data}")
            except Exception:
                pass

            if data.get("type") == "status":
                jid = data.get("jid")
                if jid is None:
                    return
                # Si este jid fue eliminado hace muy poco, ignorar el estado entrante
                try:
                    cutoff = time.time() - 3.0
                    if hasattr(self.agent, 'removals'):
                        for r in getattr(self.agent, 'removals'):
                            if r.get('jid') == jid and r.get('time', 0) >= cutoff:
                                # ignore stale status arriving after removal
                                logger.info(f"Host: ignoring status for recently removed {jid}")
                                return
                except Exception:
                    pass
                # almacenar información mínima para la interfaz web
                self.agent.fishes[jid] = {
                    "jid": jid,
                    "x": data.get("x", 0),
                    "y": data.get("y", 0),
                    "energy": data.get("energy", 0),
                    "foods_eaten": data.get("foods_eaten", 0),
                    "speed": data.get("speed", 0),
                    "size": data.get("size", None),
                    "sense": data.get("sense", None),
                    "kills": data.get("kills", 0),
                }
            elif data.get("type") == "generation_start":
                # limpiar las criaturas previas al iniciar una nueva generación
                try:
                    # keep a short history of removals
                    if not hasattr(self.agent, 'removals'):
                        self.agent.removals = []
                    self.agent.fishes = {}
                    logger.info(f"Host: generation {data.get('generation')} started — cleared fishes")
                except Exception:
                    pass
            elif data.get("type") in ("finished", "creature_removed"):
                # remove creature from UI mapping when it finishes or is removed
                jid = data.get("jid") or (str(msg.sender).split("/")[0] if msg and msg.sender else None)
                reason = data.get("reason") or ("finished" if data.get("type") == "finished" else "removed")
                killed_by = data.get("killed_by") or data.get("killed_by")
                if jid:
                    # fetch last known position before popping
                    pos = None
                    try:
                        if jid in self.agent.fishes:
                            pos = (self.agent.fishes[jid].get('x'), self.agent.fishes[jid].get('y'))
                    except Exception:
                        pos = None
                    try:
                        self.agent.fishes.pop(jid, None)
                    except Exception:
                        pass
                    # record removal event for frontend flashing
                    try:
                        if not hasattr(self.agent, 'removals'):
                            self.agent.removals = []
                        if pos is not None:
                            self.agent.removals.append({"jid": jid, "x": pos[0], "y": pos[1], "time": time.time(), "reason": reason, "killed_by": killed_by})
                        else:
                            # still append without coords so frontend can ignore if missing
                            self.agent.removals.append({"jid": jid, "time": time.time(), "reason": reason, "killed_by": killed_by})
                        logger.info(f"Host: removed {jid} reason={reason} killed_by={killed_by}")
                        # trim old removals (keep last 5 seconds)
                        cutoff = time.time() - 5.0
                        self.agent.removals = [r for r in self.agent.removals if r.get('time', 0) >= cutoff]
                    except Exception:
                        pass

    async def _start_web(self, port=10000):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        static_folder = os.path.join(base_dir, "static")

        app = aiohttp.web.Application()

        async def fishes_controller(request):
            # return list of fishes and current foods for web interface
            fishes = list(self.fishes.values())
            foods = []
            try:
                foods = list(self.gen.foods) if hasattr(self, "gen") and getattr(self.gen, "foods", None) is not None else []
            except Exception:
                foods = []
            # include recent removals for frontend flashing
            removals = []
            try:
                removals = list(self.removals) if hasattr(self, 'removals') else []
            except Exception:
                removals = []
            # current generation number for UI
            gen_num = 0
            try:
                if hasattr(self, "gen") and getattr(self.gen, "generation", None) is not None:
                    gen_num = int(self.gen.generation)
            except Exception:
                gen_num = 0

            return aiohttp.web.json_response({
                "fishes": fishes,
                "foods": foods,
                "space_size": self.gen.space_size if hasattr(self, "gen") else (30, 30),
                "removals": removals,
                "generation": gen_num,
            })

        async def kill_controller(request):
            """HTTP endpoint to request killing a specific creature by JID.

            The frontend sends {"jid": "creatureX_Y@localhost"} and we forward
            a SPADE message to the GenerationAgent so it can perform a proper kill
            (stopping the agent and notifying the Host UI for blood effects).
            """
            try:
                payload = await request.json()
            except Exception:
                return aiohttp.web.json_response({"ok": False, "error": "invalid_json"}, status=400)

            jid = payload.get("jid")
            if not jid:
                return aiohttp.web.json_response({"ok": False, "error": "missing_jid"}, status=400)

            # Determine GenerationAgent JID
            try:
                gen_jid = str(self.gen.jid).split("/")[0] if hasattr(self, "gen") and self.gen is not None else None
            except Exception:
                gen_jid = None

            if not gen_jid:
                return aiohttp.web.json_response({"ok": False, "error": "no_generation"}, status=500)

            # Send kill command to GenerationAgent
            try:
                msg = Message(to=gen_jid)
                msg.set_metadata("performative", "inform")
                msg.body = json.dumps({"type": "kill", "target_jid": jid})
                await self.send(msg)
            except Exception:
                return aiohttp.web.json_response({"ok": False, "error": "send_failed"}, status=500)

            return aiohttp.web.json_response({"ok": True})

        app.router.add_get('/fishes', fishes_controller)
        app.router.add_post('/kill', kill_controller)
        # servir archivos estáticos
        if os.path.isdir(static_folder):
            app.router.add_static('/static/', path=static_folder, name='static')

        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        url = f"http://localhost:{port}/static/index.html"
        print(f"Web UI available at {url} (bound to 0.0.0.0)")
        try:
            # intentar abrir la UI en el navegador por defecto
            webbrowser.open(url)
        except Exception:
            pass
        # conservar referencia del runner para detenerlo más tarde
        self._web_runner = runner

    async def setup(self):
        print("Host starting: creating GenerationAgent")
        cfg = WorldConfig()
        # mapeo jid -> estado para el frontend
        self.fishes = {}
        # añadir comportamiento para recibir estados de las criaturas (se espera que las criaturas también reporten al host)
        self.add_behaviour(self.RecvBehav())
        # iniciar el servidor web en segundo plano pronto para que la UI pueda conectarse y el host reciba notificaciones de eliminación
        asyncio.create_task(self._start_web(port=10000))

        # crear GenerationAgent después de registrar los behaviours del host para evitar perder mensajes
        gen = GenerationAgent("generation@localhost", cfg.generation_password, num_initial=cfg.num_initial, food_count=cfg.food_count, space_size=cfg.space_size, max_generations=cfg.max_generations)
        # asegurar que GenerationAgent use la misma configuración completa (detection_radius, energy cost, etc.)
        gen.config = cfg
        # indicar a generation cómo contactar al host para actualizaciones del frontend
        gen.host_jid = str(self.jid).split("/")[0]
        # mantener referencia para un apagado ordenado
        self.gen = gen
        await gen.start(auto_register=True)
        print("GenerationAgent started")


async def main():
    host = HostAgent('host@localhost', '123456abcd.')
    await host.start()
    print("Host agent started")
    try:
        await spade.wait_until_finished(host)
    except KeyboardInterrupt:
        print("Keyboard interrupt received — shutting down agents...")
        # attempt clean shutdown
        try:
            if hasattr(host, "gen") and host.gen is not None:
                await host.gen.stop()
        except Exception:
            pass
        try:
            await host.stop()
        except Exception:
            pass


if __name__ == "__main__":
    spade.run(main())