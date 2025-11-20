from dataclasses import dataclass
from typing import Tuple


@dataclass
class WorldConfig:
    num_initial: int = 10
    # balanced defaults: moderate food, moderate world size to produce selection
    food_count: int = 20
    space_size: Tuple[int, int] = (30, 30)
    max_generations: int = 10
    # moderate detection radius so creatures must get reasonably close
    detection_radius: float = 1.5
    # energy cost higher to force trade-offs (faster depletion)
    energy_cost_factor: float = 0.06
    # grace window for generation end (seconds)
    last_eat_grace: float = 2.5
    # reporting period (seconds) for creatures with jitter
    creature_period: float = 0.7
    # energy multiplier while actively seeking a target
    seek_energy_multiplier: float = 1.3
    creature_password: str = "123456abcd."
    generation_password: str = "123456abcd."
    # Optional initial attributes for generation 1. If None, a single random speed is chosen for gen1.
    initial_speed: float = 1.0
    initial_energy: float = 1.0
    # Size and sense ranges for creatures (generation 1 can be set via initial_size/initial_sense)
    size_min: float = 0.6
    size_max: float = 1.8
    sense_min: float = 0.0
    sense_max: float = 2.0
    initial_size: float = None
    initial_sense: float = None

    # Energy and sensing scales to convert formula magnitudes into energy per tick
    energy_scale: float = 0.02
    sense_scale: float = 0.02
    # Energy gained from consuming a food pellet (scale applied to prey volume)
    food_energy_scale: float = 0.8
    # Energy gained factor when eating another creature (prey mass scale)
    prey_food_scale: float = 0.9

    # Predation rules
    # Predator must be at least this multiple of prey.size to eat it (e.g., 1.2 = 20% larger)
    attack_size_ratio: float = 1.2
    # Distance threshold to perform predation (in world units)
    attack_radius: float = 1.0
    # Multiplier to convert 'sense' into extra detection radius for predation
    sense_radius_mult: float = 0.5

    # energy base used to compute initial energy: energy_base * size^3 / speed
    energy_base: float = 1.0
    min_speed: float = 0.1
