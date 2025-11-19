from dataclasses import dataclass
from typing import Tuple


@dataclass
class WorldConfig:
    num_initial: int = 10
    # balanced defaults: moderate food, moderate world size to produce selection
    food_count: int = 30
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
