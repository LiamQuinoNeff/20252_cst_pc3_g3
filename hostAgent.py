import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from generationAgent import GenerationAgent
from world import WorldConfig
import asyncio
import aiohttp.web
import os
import json
import webbrowser
import time

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
            # Debug log every received event for tracing
            try:
                print(f"Host received: {data}")
            except Exception:
                pass

            if data.get("type") == "status":
                jid = data.get("jid")
                if jid is None:
                    return
                # store minimal info for web interface
                self.agent.fishes[jid] = {
                    "jid": jid,
                    "x": data.get("x", 0),
                    "y": data.get("y", 0),
                    "energy": data.get("energy", 0),
                    "foods_eaten": data.get("foods_eaten", 0),
                    "speed": data.get("speed", 0),
                    "size": data.get("size", None),
                    "sense": data.get("sense", None),
                }
            elif data.get("type") == "generation_start":
                # clear previous fishes at the start of a new generation
                try:
                    # keep a short history of removals
                    if not hasattr(self.agent, 'removals'):
                        self.agent.removals = []
                    self.agent.fishes = {}
                    print(f"Host: generation {data.get('generation')} started — cleared fishes")
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
                        print(f"Host: removed {jid} reason={reason} killed_by={killed_by}")
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
            return aiohttp.web.json_response({"fishes": fishes, "foods": foods, "space_size": self.gen.space_size if hasattr(self, "gen") else (30, 30), "removals": removals})

        app.router.add_get('/fishes', fishes_controller)
        # serve static files
        if os.path.isdir(static_folder):
            app.router.add_static('/static/', path=static_folder, name='static')

        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        url = f"http://localhost:{port}/static/index.html"
        print(f"Web UI available at {url} (bound to 0.0.0.0)")
        try:
            # try to open the UI in the default browser
            webbrowser.open(url)
        except Exception:
            pass
        # keep runner reference to stop later
        self._web_runner = runner

    async def setup(self):
        print("Host starting: creating GenerationAgent")
        cfg = WorldConfig()
        # mapping jid -> status for frontend
        self.fishes = {}
        # add behaviour to receive statuses from creatures (we expect creatures to also send to host)
        self.add_behaviour(self.RecvBehav())
        # start web server in background early so UI can connect and host can receive removal notifications
        asyncio.create_task(self._start_web(port=10000))

        # create GenerationAgent after host behaviours are registered to avoid missed messages
        gen = GenerationAgent("generation@localhost", cfg.generation_password, num_initial=cfg.num_initial, food_count=cfg.food_count, space_size=cfg.space_size, max_generations=cfg.max_generations)
        # ensure GenerationAgent uses the same full config (detection_radius, energy cost, etc.)
        gen.config = cfg
        # let generation know how to contact host for frontend updates
        gen.host_jid = str(self.jid).split("/")[0]
        # keep reference for clean shutdown
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