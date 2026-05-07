"""Nivel 1: agente aleatorio (baseline).

Política: elige uniformemente entre las acciones legales. No discrimina entre
atacar y cambiar — esa simplicidad es la idea: es nuestro baseline para
medir mejora frente a heurísticos y Minimax/GA en el entregable final.
"""
from __future__ import annotations
import random
from typing import Optional

from src.core import BattleState, Action
from .base_agent import Agent


class RandomAgent(Agent):
    name = "Random"

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()

    def choose_action(self, state: BattleState, side: int) -> Action:
        legal = state.legal_actions(side)
        if not legal:
            raise RuntimeError("RandomAgent: no hay acciones legales")
        return self.rng.choice(legal)
