"""Wrapper de RNG con semilla configurable (para reproducibilidad de experimentos)."""
import random
import config


def make_rng(seed: int | None = None) -> random.Random:
    if seed is None:
        seed = config.RNG_SEED
    return random.Random(seed)
