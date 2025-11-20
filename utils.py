import random
import math


def place_food(count, space_size):
    """Devuelve una lista de tuplas (x,y) distribuidas uniformemente en `space_size` (w,h)."""
    w, h = space_size
    return [(random.uniform(0, w), random.uniform(0, h)) for _ in range(count)]


def distance(a, b):
    """Distancia euclidiana entre los puntos `a` y `b` (tuplas)."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def default_energy_for_speed(speed, k=1.0):
    """Wrapper retrocompatible: energía = k / speed (mantenido para llamadas antiguas)."""
    if speed == 0:
        return k
    return k / speed


def random_size(min_size=0.6, max_size=1.8):
    return random.uniform(min_size, max_size)


def random_sense(min_sense=0.0, max_sense=2.0):
    return random.uniform(min_sense, max_sense)


def default_energy(speed, size, energy_base=1.0, min_speed=0.1):
    """Calcula la energía inicial por defecto proporcional a size^3 e inversa a la velocidad.

    Fórmula: energy = energy_base * (size ** 3) / max(abs(speed), min_speed)
    Devuelve la energía calculada.
    """


def energy_drain_per_tick(size, speed, sense, energy_scale=0.02, sense_scale=0.02):
    """Calcula la pérdida de energía por tick usando la fórmula propuesta.

    drain = energy_scale * (size ** 3 * (speed ** 2)) + sense_scale * sense
    Devuelve el valor de `drain`.
    """


def random_speed(min_s=0.5, max_s=2.0):
    return random.uniform(min_s, max_s)
