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
    """Return default energy given speed using inverse relation energy = k / speed."""
    if speed == 0:
        return k
    return k / speed


def random_speed(min_s=0.5, max_s=2.0):
    return random.uniform(min_s, max_s)
