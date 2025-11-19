import spade
from spade.agent import Agent
from generationAgent import GenerationAgent
from world import WorldConfig
import asyncio


class HostAgent(Agent):
    async def setup(self):
        print("Host starting: creating GenerationAgent")
        cfg = WorldConfig()
        gen = GenerationAgent("generation@localhost", cfg.generation_password, num_initial=cfg.num_initial, food_count=cfg.food_count, space_size=cfg.space_size, max_generations=cfg.max_generations)
        # ensure GenerationAgent uses the same full config (detection_radius, energy cost, etc.)
        gen.config = cfg
        # keep reference for clean shutdown
        self.gen = gen
        await gen.start(auto_register=True)
        print("GenerationAgent started")
        # we don't block here; host will wait in main


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
