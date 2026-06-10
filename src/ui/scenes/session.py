"""Configuración acumulada por las escenas previas al combate."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BattleSession:
    size: int = 4                      # 3 o 4
    player_random_team: bool = False
    opp_random_team: bool = False
    player_random_moves: bool = False
    opp_random_moves: bool = False
    opp_agent: str = "Heuristic"       # "Random" | "Heuristic" | "Minimax"  #AGREGADO (Nivel 3)

    # Resultado del flujo de selección
    player_team: list[str] = field(default_factory=list)         # nombres de especies
    opp_team: list[str] = field(default_factory=list)
    player_movesets: list[list[str]] = field(default_factory=list)  # 4 ids por Pokémon
    opp_movesets: list[list[str]] = field(default_factory=list)
