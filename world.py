from dataclasses import dataclass
from typing import Tuple


@dataclass
class WorldConfig:
    num_initial: int = 10
    # valores por defecto equilibrados: comida moderada y tamaño del mundo moderado para permitir selección
    food_count: int = 20
    space_size: Tuple[int, int] = (30, 30)
    max_generations: int = 10
    # radio de detección moderado para que las criaturas deban acercarse razonablemente
    detection_radius: float = 1.5
    # coste de energía mayor para forzar compensaciones (agotamiento más rápido)
    energy_cost_factor: float = 0.06
    # ventana de gracia para el fin de generación (segundos)
    last_eat_grace: float = 2.5
    # periodo de reporte (segundos) para las criaturas con jitter
    creature_period: float = 0.7
    # multiplicador de energía mientras se busca activamente un objetivo
    seek_energy_multiplier: float = 1.3
    creature_password: str = "123456abcd."
    generation_password: str = "123456abcd."
    # Atributos iniciales opcionales para la generación 1. Si None, se elige una velocidad aleatoria única para gen1.
    initial_speed: float = 1.0
    initial_energy: float = 1.0
    # Rangos de tamaño y sentido para las criaturas (la generación 1 puede fijarse mediante initial_size/initial_sense)
    size_min: float = 0.6
    size_max: float = 1.8
    sense_min: float = 0.0
    sense_max: float = 2.0
    initial_size: float = None
    initial_sense: float = None

    # Escalas de energía y detección para convertir magnitudes de la fórmula a energía por tick
    energy_scale: float = 0.02
    sense_scale: float = 0.02
    # Energía ganada al consumir un pellet de comida (escala aplicada al volumen del presa)
    food_energy_scale: float = 0.8
    # Factor de energía ganada al comerse a otra criatura (escala por masa del presa)
    prey_food_scale: float = 0.9

    # Predation rules
    # Reglas de depredación
    # El depredador debe ser al menos este múltiplo del tamaño del presa para poder comérselo (p.ej., 1.2 = 20% más grande)
    attack_size_ratio: float = 1.2
    # Umbral de distancia para realizar la depredación (en unidades del mundo)
    attack_radius: float = 1.0
    # Multiplicador para convertir 'sense' en radio extra de detección para depredación
    sense_radius_mult: float = 0.5

    # base de energía usada para calcular la energía inicial: energy_base * size^3 / speed
    energy_base: float = 1.0
    min_speed: float = 0.1
