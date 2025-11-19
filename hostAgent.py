import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from generationAgent import GenerationAgent
from world import WorldConfig
import asyncio
import aiohttp.web
import os
import json

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
                }

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
            return aiohttp.web.json_response({"fishes": fishes, "foods": foods, "space_size": self.gen.space_size if hasattr(self, "gen") else (30, 30)})

        app.router.add_get('/fishes', fishes_controller)
        # serve static files
        if os.path.isdir(static_folder):
            app.router.add_static('/static/', path=static_folder, name='static')

        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        print(f"Web UI available at http://0.0.0.0:{port}/static/index.html")
        # keep runner reference to stop later
        self._web_runner = runner

    async def setup(self):
        print("Host starting: creating GenerationAgent")
        cfg = WorldConfig()
        gen = GenerationAgent("generation@localhost", cfg.generation_password, num_initial=cfg.num_initial, food_count=cfg.food_count, space_size=cfg.space_size, max_generations=cfg.max_generations)
        # ensure GenerationAgent uses the same full config (detection_radius, energy cost, etc.)
        gen.config = cfg
        # keep reference for clean shutdown
        self.gen = gen
        # mapping jid -> status for frontend
        self.fishes = {}
        await gen.start(auto_register=True)
        print("GenerationAgent started")
        # add behaviour to receive statuses from creatures (we expect creatures to also send to host)
        self.add_behaviour(self.RecvBehav())
        # start web server in background
        asyncio.create_task(self._start_web(port=10000))


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