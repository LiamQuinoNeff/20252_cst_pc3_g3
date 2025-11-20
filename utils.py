import random
import math


def place_food(count, space_size):
    """Return a list of (x,y) tuples uniformly distributed in space_size (w,h)."""
    w, h = space_size
    return [(random.uniform(0, w), random.uniform(0, h)) for _ in range(count)]


def distance(a, b):
    """Euclidean distance between points a and b (tuples)."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def default_energy_for_speed(speed, k=1.0):
    """Backward-compatible wrapper: energy = k / speed (kept for older callers)."""
    if speed == 0:
        return k
    return k / speed


def random_size(min_size=0.6, max_size=1.8):
    return random.uniform(min_size, max_size)


def random_sense(min_sense=0.0, max_sense=2.0):
    return random.uniform(min_sense, max_sense)


def default_energy(speed, size, energy_base=1.0, min_speed=0.1):
    """Compute default initial energy as proportional to size^3 and inverse to speed.

    energy = energy_base * (size ** 3) / max(abs(speed), min_speed)
    return energy"""


def energy_drain_per_tick(size, speed, sense, energy_scale=0.02, sense_scale=0.02):
    """Compute energy drain per time step using proposed formula.

    drain = energy_scale * (size ** 3 * (speed ** 2)) + sense_scale * sense
    return drain"""


def random_speed(min_s=0.5, max_s=2.0):
    return random.uniform(min_s, max_s)
