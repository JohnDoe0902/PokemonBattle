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

from src.core import BattleState
from src.agents import RandomAgent, HeuristicAgent
from src.agents.harness import make_team, run_battle


def play_once(agent_a, agent_b, size: int, rng: random.Random,
              max_turns: int = 200) -> tuple[int, int]:
    state = BattleState(make_team(rng, size), make_team(rng, size),
                        names=("A", "B"), rng=rng)
    winner, turns = run_battle(state, agent_a, agent_b, max_turns)
    return (winner if winner is not None else -1, turns)


def run() -> None:
    n_games = 50
    #AGREGADO Inicio
    # Sembrar TODOS los RNG (batalla y agentes) desde una semilla maestra para que
    # el smoke test sea realmente reproducible. Antes los agentes se creaban sin
    # semilla (RNG por entropía del sistema), así que el resultado variaba en cada
    # corrida. Cada agente recibe su propio stream, independiente del de la batalla
    # (no se comparte el objeto rng) — la misma convención que usará el GA.
    MASTER_SEED = 42
    rng = random.Random(MASTER_SEED)                    # RNG exclusivo de la batalla
    a = RandomAgent(random.Random(MASTER_SEED + 1))     # RNG propio del agente A
    b = HeuristicAgent(random.Random(MASTER_SEED + 2))  # RNG propio del agente B
    #AGREGADO Fin
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
