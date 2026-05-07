"""Decide cuál escena va después de Config en función de las elecciones."""
from __future__ import annotations
import random

from src.core.pokemon import all_species, random_moveset
from .session import BattleSession


def next_after_config(s: BattleSession):
    # 1) Resolver equipo aleatorio si corresponde
    rng = random.Random()
    species_names = list(all_species().keys())

    if s.player_random_team:
        s.player_team = rng.sample(species_names, s.size)
    if s.opp_random_team:
        s.opp_team = rng.sample(species_names, s.size)

    # 2) Si jugador tiene que elegir manualmente:
    if not s.player_team:
        from .team_select_scene import TeamSelectScene
        return TeamSelectScene(s, side="player")
    if not s.player_random_moves and not s.player_movesets:
        from .move_select_scene import MoveSelectScene
        return MoveSelectScene(s, side="player")
    # 3) Movs aleatorios del jugador si no se eligieron
    if s.player_random_moves and not s.player_movesets:
        s.player_movesets = [random_moveset(all_species()[n], rng=rng) for n in s.player_team]

    if not s.opp_team:
        from .team_select_scene import TeamSelectScene
        return TeamSelectScene(s, side="opponent")
    if not s.opp_random_moves and not s.opp_movesets:
        from .move_select_scene import MoveSelectScene
        return MoveSelectScene(s, side="opponent")
    if s.opp_random_moves and not s.opp_movesets:
        s.opp_movesets = [random_moveset(all_species()[n], rng=rng) for n in s.opp_team]

    from .battle_scene import BattleScene
    return BattleScene(s)
