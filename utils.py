import random
import math


def place_food(count, space_size):
    """Devuelve una lista de tuplas (x,y) distribuidas uniformemente en `space_size` (w,h)."""
    w, h = space_size
    return [(random.uniform(0, w), random.uniform(0, h)) for _ in range(count)]


def distance(a, b):
    """Distancia euclidiana entre los puntos `a` y `b` (tuplas)."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def default_energy_for_speed(speed, k=3.0):
    """Wrapper retrocompatible para energía inicial basada en velocidad.

    Históricamente: energía = k / speed.
    Ahora delega en `speed_to_energy` usando `k` como presupuesto total
    aproximado de velocidad + energía.
    """
    return speed_to_energy(speed, total_budget=k)


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


def random_speed(min_s=0.3, max_s=2.5):
    return random.uniform(min_s, max_s)


def spawn_position_on_edge(space_size):
    """Generate a spawn position on the border of the rectangular world.

    The logical world is [0, w] x [0, h]. We pick a random point along the
    outer rectangle (edges x=0, x=w, y=0, y=h) so blobs aparecen en el borde
    de la plataforma CUADRADA.
    """
    w, h = space_size
    if w <= 0 or h <= 0:
        return (0.0, 0.0)

    # Elegir un punto uniforme a lo largo del perímetro del rectángulo
    perimeter = 2.0 * (w + h)
    t = random.uniform(0.0, perimeter)

    if t < w:
        # borde inferior: y = 0, x en [0, w]
        x = t
        y = 0.0
    elif t < w + h:
        # borde derecho: x = w, y en [0, h]
        x = w
        y = t - w
    elif t < 2.0 * w + h:
        # borde superior: y = h, x en [w, 0]
        x = (2.0 * w + h) - t
        y = h
    else:
        # borde izquierdo: x = 0, y en [h, 0]
        x = 0.0
        y = perimeter - t

    return (x, y)



def mutate_speed(parent_speed, mutation_rate=0.1, min_s=0.3, max_s=2.5):
    """Mutate parent speed with a small variation.

    Args:
        parent_speed: parent's speed value
        mutation_rate: fraction of change (0.1 = ±10%)
        min_s, max_s: bounds for speed

    Returns:
        mutated speed value (slightly faster or slower than the parent)
    """
    change = random.uniform(-mutation_rate, mutation_rate)
    new_speed = parent_speed * (1 + change)
    return max(min_s, min(max_s, new_speed))


def speed_to_energy(speed, total_budget=3.0):
    """Calculate initial energy so that speed + energy ≈ constant for all blobs.

    Queremos que la suma `speed + energy` sea aproximadamente la misma
    para todos los individuos. Usamos:

        energy = total_budget - speed

    De esta forma, los individuos rápidos tienen menos energía inicial y
    los lentos tienen más, pero todos comparten el mismo "presupuesto"
    total (velocidad + energía).

    Args:
        speed: velocidad de la criatura
        total_budget: valor objetivo para speed + energy

    Returns:
        energía inicial
    """
    if speed is None:
        return total_budget * 0.5

    try:
        s = float(speed)
    except (TypeError, ValueError):
        s = 1.0

    if s <= 0:
        s = 0.1

    energy = total_budget - s

    # salvaguarda mínima para evitar energías no positivas si se cambia el rango de velocidades
    if energy <= 0:
        energy = 0.1

    return energy
