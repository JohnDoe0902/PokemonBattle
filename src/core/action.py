"""Acciones de combate: atacar o cambiar Pokémon."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    kind: str            # "attack" | "switch"
    move_index: int = -1     # idx (0..3) en pokemon.moves; usado si kind == "attack"
    switch_to: int = -1      # idx en team; usado si kind == "switch"

    @staticmethod
    def attack(idx: int) -> "Action":
        return Action(kind="attack", move_index=idx)

    @staticmethod
    def switch(idx: int) -> "Action":
        return Action(kind="switch", switch_to=idx)

    def __repr__(self) -> str:  # pragma: no cover
        if self.kind == "attack":
            return f"Atk({self.move_index})"
        return f"Switch->{self.switch_to}"
