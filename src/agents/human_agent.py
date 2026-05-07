"""Agente humano: la UI le 'inyecta' la decisión.

La UI llama a `set_pending(action)` cuando el jugador clickea/teclea. La escena
de combate sólo avanza el turno cuando ambos lados tienen acción.
"""
from __future__ import annotations
from typing import Optional

from src.core import BattleState, Action
from .base_agent import Agent


class HumanAgent(Agent):
    name = "Human"
    is_human = True

    def __init__(self):
        self._pending: Optional[Action] = None

    def set_pending(self, action: Action) -> None:
        self._pending = action

    def take_pending(self) -> Optional[Action]:
        a = self._pending
        self._pending = None
        return a

    def has_pending(self) -> bool:
        return self._pending is not None

    def choose_action(self, state: BattleState, side: int) -> Action:
        # No debería invocarse: la escena consulta has_pending/take_pending.
        raise NotImplementedError(
            "HumanAgent.choose_action no debe llamarse: "
            "la UI proporciona la acción vía set_pending()."
        )
