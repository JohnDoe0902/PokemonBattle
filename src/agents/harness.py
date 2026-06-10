"""Harness compartido de simulación headless: equipos aleatorios, configuraciones
reproducibles (CRN) y bucle de partida entre dos agentes.

Única fuente de verdad para los scripts (`headless_smoke.py`, `evaluate.py`,
`train_level3.py`): antes cada uno tenía su propia copia de estas funciones y
podían divergir silenciosamente.

Puro (sin Pygame ni I/O): apto para experimentos masivos por consola.
"""
from __future__ import annotations
import random
from typing import Optional

from src.core import BattleState
from src.core.pokemon import Pokemon, all_species, random_moveset

# Lista estable de especies (orden de inserción del JSON) → muestreo reproducible.
SPECIES = list(all_species().keys())


def make_team(rng: random.Random, size: int) -> list[Pokemon]:
    """Equipo aleatorio muestreado directamente de `rng` (especies + movesets)."""
    team = []
    for nm in rng.sample(SPECIES, size):
        sp = all_species()[nm]
        team.append(Pokemon.build(sp, random_moveset(sp, rng=rng)))
    return team


def gen_config(rng: random.Random, size: int):
    """Configuración reproducible de una partida: equipos, movesets y semilla de batalla.

    Separar la configuración de los agentes es lo que permite CRN: distintos
    agentes/genomas juegan exactamente las mismas partidas.
    """
    names0 = rng.sample(SPECIES, size)
    names1 = rng.sample(SPECIES, size)
    ms0 = [random_moveset(all_species()[n], rng=rng) for n in names0]
    ms1 = [random_moveset(all_species()[n], rng=rng) for n in names1]
    return (names0, ms0, names1, ms1, rng.randrange(1_000_000))


def build_team(names, movesets) -> list[Pokemon]:
    return [Pokemon.build(all_species()[n], ms) for n, ms in zip(names, movesets)]


def run_battle(state: BattleState, agent0, agent1,
               max_turns: int = 300) -> tuple[Optional[int], int]:
    """Bucle estándar de partida: resuelve cambios forzados y avanza turnos.

    Devuelve (winner, turnos); winner es None si se alcanzó `max_turns`.
    """
    agents = (agent0, agent1)
    turns = 0
    while not state.is_over() and turns < max_turns:
        if state.pending_switch[0]:
            state.force_switch(0, agents[0].choose_forced_switch(state, 0).switch_to)
            continue
        if state.pending_switch[1]:
            state.force_switch(1, agents[1].choose_forced_switch(state, 1).switch_to)
            continue
        state.step(agents[0].choose_action(state, 0), agents[1].choose_action(state, 1))
        turns += 1
    return state.winner(), turns


def hp_margin(state: BattleState, side: int) -> float:
    """Diferencia de HP total normalizada (side − rival), ∈ [-1, 1]."""
    own = sum(p.hp for p in state.teams[side])
    opp = sum(p.hp for p in state.teams[1 - side])
    own_max = sum(p.hp_max for p in state.teams[side]) or 1
    opp_max = sum(p.hp_max for p in state.teams[1 - side]) or 1
    return own / own_max - opp / opp_max


def play(cfg, agent0, agent1, max_turns: int = 300):
    """Juega una configuración de `gen_config`.

    Devuelve (winner, turnos, margen de HP desde la perspectiva del lado 1).
    """
    names0, ms0, names1, ms1, bseed = cfg
    state = BattleState(build_team(names0, ms0), build_team(names1, ms1),
                        rng=random.Random(bseed))
    winner, turns = run_battle(state, agent0, agent1, max_turns)
    return winner, turns, hp_margin(state, 1)
