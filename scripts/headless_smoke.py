"""Smoke test sin GUI: simula RandomAgent vs HeuristicAgent N veces e imprime stats.

Sirve para:
- Probar que core/agents/data funcionan sin depender de Pygame.
- Generar resultados preliminares (Entrega Parcial).
"""
from __future__ import annotations
import sys
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config
from src.core import BattleState, Action
from src.core.pokemon import Pokemon, all_species, random_moveset
from src.agents import RandomAgent, HeuristicAgent


def make_team(rng: random.Random, size: int) -> list[Pokemon]:
    species_names = list(all_species().keys())
    chosen = rng.sample(species_names, size)
    team = []
    for nm in chosen:
        sp = all_species()[nm]
        ms = random_moveset(sp, rng=rng)
        team.append(Pokemon.build(sp, ms))
    return team


def play_once(agent_a, agent_b, size: int, rng: random.Random,
              max_turns: int = 200) -> tuple[int, int]:
    state = BattleState(make_team(rng, size), make_team(rng, size),
                        names=("A", "B"), rng=rng)
    turns = 0
    while not state.is_over() and turns < max_turns:
        # Si alguien tiene pending_switch, toma esa decisión
        if state.pending_switch[0]:
            a = agent_a.choose_forced_switch(state, 0)
            state.force_switch(0, a.switch_to)
            continue
        if state.pending_switch[1]:
            b = agent_b.choose_forced_switch(state, 1)
            state.force_switch(1, b.switch_to)
            continue
        a = agent_a.choose_action(state, 0)
        b = agent_b.choose_action(state, 1)
        state.step(a, b)
        turns += 1
    winner = state.winner()
    return (winner if winner is not None else -1, turns)


def run() -> None:
    n_games = 50
    rng = random.Random(42)
    a, b = RandomAgent(), HeuristicAgent()
    wins = [0, 0, 0]   # [a, b, draw/timeout]
    durations = []
    for _ in range(n_games):
        w, t = play_once(a, b, size=4, rng=rng)
        if w == 0:    wins[0] += 1
        elif w == 1:  wins[1] += 1
        else:          wins[2] += 1
        durations.append(t)
    print("\n=== Smoke test: 50 partidas, 4v4 ===")
    print(f"Random   ganó: {wins[0]:3d}  ({wins[0]/n_games:.1%})")
    print(f"Heur(HP) ganó: {wins[1]:3d}  ({wins[1]/n_games:.1%})")
    print(f"Empates:        {wins[2]:3d}")
    print(f"Duración media: {sum(durations)/len(durations):.1f} turnos")


if __name__ == "__main__":
    run()
