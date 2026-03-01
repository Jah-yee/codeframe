import math
from dataclasses import dataclass


@dataclass
class Particle:
    """A particle in 2D space with velocity."""
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0

    def step(self, dt: float = 0.016):
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx**2 + self.vy**2)


def simulate(particles: list[Particle], steps: int = 1000):
    """Run a simple n-body simulation."""
    for _ in range(steps):
        for p in particles:
            p.step()
    return [p.speed for p in particles]
