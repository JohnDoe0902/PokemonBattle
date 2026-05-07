"""Interfaz común a todos los agentes (humanos, IA o futuros Minimax/GA)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from src.core import BattleState, Action


class Agent(ABC):
    """Cualquier estrategia que toma un Action dado un BattleState y un side."""

    name: str = "agent"
    is_human: bool = False

    @abstractmethod
    def choose_action(self, state: BattleState, side: int) -> Action:
        ...

    # Algunas IAs querrán resolver cambios forzados con la misma lógica de
    # 'choose_action' acotada a switches; otras pueden sobreescribir.
    def choose_forced_switch(self, state: BattleState, side: int) -> Action:
        return self.choose_action(state, side)
