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


def spawn_positions_on_perimeter(num_creatures, space_size):
    """Calcula posiciones equidistantes en el perímetro del mundo rectangular.
    
    Args:
        num_creatures: Número de criaturas a distribuir
        space_size: Tupla (width, height) del mundo
    
    Returns:
        Lista de tuplas (x, y) con posiciones en el borde
    """
    w, h = space_size
    perimeter = 2 * (w + h)
    
    # Calcular distancia entre criaturas
    spacing = perimeter / num_creatures
    
    positions = []
    for i in range(num_creatures):
        # Distancia desde el origen siguiendo el perímetro
        distance_along_perimeter = i * spacing
        
        # Determinar en qué lado del rectángulo estamos
        if distance_along_perimeter < w:
            # Lado superior: de (0,0) a (w,0)
            x = distance_along_perimeter
            y = 0
        elif distance_along_perimeter < w + h:
            # Lado derecho: de (w,0) a (w,h)
            x = w
            y = distance_along_perimeter - w
        elif distance_along_perimeter < 2 * w + h:
            # Lado inferior: de (w,h) a (0,h)
            x = w - (distance_along_perimeter - w - h)
            y = h
        else:
            # Lado izquierdo: de (0,h) a (0,0)
            x = 0
            y = h - (distance_along_perimeter - 2 * w - h)
        
        positions.append((x, y))
    
    return positions
