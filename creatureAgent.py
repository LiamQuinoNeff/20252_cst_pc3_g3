import asyncio
import json
import random
import math
from dataclasses import dataclass
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour
from spade.message import Message
import utils
from logger_setup import get_logger

logger = get_logger('creature')


@dataclass
class CreatureState:
	jid: str
	speed: float
	energy: float
	foods_eaten: int = 0
	size: float = 1.0
	sense: float = 0.0
	x: float = 0.0
	y: float = 0.0


class CreatureAgent(Agent):
	"""Agente que representa una criatura en la simulación.

	Comportamientos principales:
	- Reportar estado periódicamente al `GenerationAgent`.
	- Responder a mensajes de confirmación (comer) y al fin de generación.
	- Moverse en el espacio y consumir energía según tamaño/velocidad/sense.
	"""

	class ReportBehav(PeriodicBehaviour):
		async def run(self):
			# Moverse (hacia target si existe, o aleatoriamente) según `speed`
			state = self.agent.state
			# movimiento aleatorio: dirección uniforme
			# Si tiene un objetivo, moverse hacia él; si no, moverse aleatoriamente
			target = getattr(self.agent, "target", None)
			if target is not None:
				# vector hacia target
				dx = target[0] - state.x
				dy = target[1] - state.y
				dist = math.hypot(dx, dy)
				if dist > 0:
					step = min(state.speed, dist)
					state.x += (dx / dist) * step
					state.y += (dy / dist) * step
					seeking = True
				else:
					seeking = False
			else:
				seeking = False
				# movimiento aleatorio: dirección uniforme
				theta = random.random() * 2 * math.pi
				dx = math.cos(theta) * state.speed
				dy = math.sin(theta) * state.speed
				state.x += dx
				state.y += dy
			# Limitar posición dentro del espacio si está disponible
			space = getattr(self.agent, "space_size", None)
			if space is not None:
				w, h = space
				# clamp
				state.x = max(0.0, min(w, state.x))
				state.y = max(0.0, min(h, state.y))
			# reducir energía según la fórmula: energy_scale*(size^3*speed^2) + sense_scale*sense
			config = getattr(self.agent, "config", None)
			if config is not None:
				energy_scale = getattr(config, "energy_scale", 0.02)
				sense_scale = getattr(config, "sense_scale", 0.02)
			else:
				energy_scale = 0.02
				sense_scale = 0.02
			drain = energy_scale * (state.size ** 3 * (state.speed ** 2)) + sense_scale * state.sense
			# if seeking, slightly increase drain using seek multiplier
			if seeking:
				mult = getattr(config, "seek_energy_multiplier", 1.3) if config is not None else 1.3
				drain *= mult
			state.energy -= drain

			# Construir y enviar mensaje JSON con el estado actual
			payload = {
				"type": "status",
				"jid": state.jid,
				"x": state.x,
				"y": state.y,
				"energy": state.energy,
				"size": state.size,
				"sense": state.sense,
				"foods_eaten": state.foods_eaten,
			}
			msg = Message(to=self.agent.generation_jid)
			msg.set_metadata("performative", "inform")
			msg.body = json.dumps(payload)
			await self.send(msg)

			# También reportar al Host UI si está configurado
			host_jid = getattr(self.agent, "host_jid", None)
			if host_jid:
				host_msg = Message(to=host_jid)
				host_msg.set_metadata("performative", "inform")
				host_msg.body = json.dumps(payload)
				try:
					await self.send(host_msg)
				except Exception:
					pass

			# Si la energía se agotó, notificar finalización y detener el agente
			if state.energy <= 0:
				end_msg = Message(to=self.agent.generation_jid)
				end_msg.set_metadata("performative", "inform")
				end_msg.body = json.dumps({"type": "finished", "jid": state.jid, "foods_eaten": state.foods_eaten, "energy": state.energy, "size": state.size, "sense": state.sense})
				await self.send(end_msg)
				try:
					logger.info(f"Creature {state.jid} finished energy={state.energy:.3f} foods={state.foods_eaten} size={state.size:.3f} sense={state.sense:.3f}")
				except Exception:
					pass
				# also inform host UI if present
				host_jid = getattr(self.agent, "host_jid", None)
				if host_jid:
					host_end = Message(to=host_jid)
					host_end.set_metadata("performative", "inform")
					host_end.body = end_msg.body
					try:
						await self.send(host_end)
					except Exception:
						pass
				await asyncio.sleep(0.1)
				await self.agent.stop()


	class RecvBehav(CyclicBehaviour):
		async def run(self):
			msg = await self.receive(timeout=1)
			if msg is None:
				return
			try:
				data = json.loads(msg.body)
			except Exception:
				return

			# Manejar confirmación de comida recibida
			if data.get("type") == "eat_confirm" and data.get("jid") == self.agent.state.jid:
				# incrementar contador de comidas y aumentar la energía según `energy_gain`
				self.agent.state.foods_eaten += 1
				energy_gain = None
				if "energy_gain" in data:
					try:
						energy_gain = float(data.get("energy_gain"))
					except Exception:
						energy_gain = None
				if energy_gain is None:
					cfg = getattr(self.agent, "config", None)
					fes = getattr(cfg, "food_energy_scale", 0.8) if cfg is not None else 0.8
					energy_gain = fes * (self.agent.state.size ** 3)
				self.agent.state.energy += energy_gain
				# enviar ack opcional
			elif data.get("type") == "generation_end":
				# La generación terminó: enviar estado final (`finished`) y detener
				end_msg = Message(to=self.agent.generation_jid)
				end_msg.set_metadata("performative", "inform")
				end_msg.body = json.dumps({"type": "finished", "jid": self.agent.state.jid, "foods_eaten": self.agent.state.foods_eaten, "energy": self.agent.state.energy, "size": self.agent.state.size, "sense": self.agent.state.sense})
				await self.send(end_msg)
				# also inform host UI if present
				host_jid = getattr(self.agent, "host_jid", None)
				if host_jid:
					host_end = Message(to=host_jid)
					host_end.set_metadata("performative", "inform")
					host_end.body = end_msg.body
					try:
						await self.send(host_end)
					except Exception:
						pass
				await asyncio.sleep(0.05)
				await self.agent.stop()
			elif data.get("type") == "target":
				# Se indica la posición de la comida más cercana (target)
				tx = data.get("x")
				ty = data.get("y")
				if tx is not None and ty is not None:
					self.agent.target = (tx, ty)
				else:
					self.agent.target = None
			elif data.get("type") == "no_target":
				self.agent.target = None


	async def setup(self):
		# Crear estado interno a partir de atributos del agente
		# Se espera que la generación pase `speed` y `energy` en self.extra
		speed = getattr(self, "init_speed", None)
		energy = getattr(self, "init_energy", None)
		if speed is None or energy is None:
			# valores por defecto
			speed = utils.random_speed()
			energy = utils.default_energy_for_speed(speed)

		jid = str(self.jid).split("/")[0]
		self.state = CreatureState(jid=jid, speed=speed, energy=energy)
		# size and sense initialization (may be set by GenerationAgent)
		self.state.size = getattr(self, "init_size", None) or utils.random_size()
		self.state.sense = getattr(self, "init_sense", None) or utils.random_sense()
		# generation_jid debe ser seteado por el Host/GenerationAgent
		self.generation_jid = getattr(self, "generation_jid", "generation@localhost")
		# posición inicial si fue provista
		self.state.x = getattr(self, "init_x", self.state.x)
		self.state.y = getattr(self, "init_y", self.state.y)

		print(f"Creature {jid} started — speed={self.state.speed:.2f} energy={self.state.energy:.2f} size={self.state.size:.2f} sense={self.state.sense:.2f}")
		try:
			logger.info(f"Creature {jid} started speed={self.state.speed:.2f} energy={self.state.energy:.2f} size={self.state.size:.2f} sense={self.state.sense:.2f}")
		except Exception:
			pass

		# Reportar periódicamente (usar periodo del world config si existe, añadir jitter)
		period = 1.0
		config = getattr(self, "config", None)
		if config is not None:
			period = getattr(config, "creature_period", period)
		# pequeño jitter para evitar sincronización excesiva
		period = random.uniform(period * 0.9, period * 1.1)
		self.add_behaviour(self.ReportBehav(period=period))
		self.add_behaviour(self.RecvBehav())


if __name__ == "__main__":
	print("Este archivo define `CreatureAgent`. Ejecutarlo a través de `hostAgent` o `generationAgent`.")

