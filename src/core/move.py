"""Modelo de movimiento + carga desde JSON."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Optional

import config


@dataclass
class Move:
    id: str
    name: str
    type: str
    category: str            # "physical" | "special"
    power: int               # 0 si es un movimiento de estado
    accuracy: int            # 0–100; movimientos always_hits ignoran este valor
    pp: int
    flags: dict = field(default_factory=dict)  # bandera libre: drain, recoil, multi_hit, etc.

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Move {self.name} {self.type} {self.category} {self.power}/{self.accuracy}>"


# ─── Carga ────────────────────────────────────────────────────────────────────
_MOVES_BY_ID: Optional[dict[str, Move]] = None


def _load() -> dict[str, Move]:
    global _MOVES_BY_ID
    if _MOVES_BY_ID is not None:
        return _MOVES_BY_ID
    with open(config.DATA_DIR / "moves.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
    out: dict[str, Move] = {}
    for m in raw["moves"]:
        flags = {k: v for k, v in m.items() if k not in ("id", "name", "type", "category", "power", "accuracy", "pp")}
        out[m["id"]] = Move(
            id=m["id"], name=m["name"], type=m["type"], category=m["category"],
            power=m["power"], accuracy=m["accuracy"], pp=m["pp"], flags=flags,
        )
    _MOVES_BY_ID = out
    return out


def get_move(move_id: str) -> Move:
    return _load()[move_id]


def all_moves() -> dict[str, Move]:
    return _load()
