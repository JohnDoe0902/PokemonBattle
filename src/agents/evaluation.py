"""Función de evaluación del agente Nivel 3 (minimax).

Componentes C1–C5 (cada uno un diferencial 'yo − rival' normalizado a [-1, 1])
y la combinación lineal H = Σ wᵢ·Cᵢ que el algoritmo genético optimiza.

Archivo NUEVO: forma parte del agente Nivel 3; no modifica código preexistente.
"""
#AGREGADO Inicio
from __future__ import annotations
import math
from typing import Sequence

import config
from src.core import BattleState, type_effectiveness


# Valor de un estado terminal. Debe dominar cualquier valor heurístico: con los
# pesos en el simplex (Σwᵢ = 1) se cumple Σ|wᵢ·Cᵢ| ≤ 1, así que una victoria real
# siempre vale más que el estado heurístico más favorable.
TERMINAL: float = 1000.0

# Orden de los componentes en el vector de pesos.
COMPONENT_NAMES = ("hp", "vivos", "tipo", "velocidad", "ko")


# ─── Daño esperado determinista (sin RNG) ──────────────────────────────────────
def expected_damage(attacker, defender, move) -> float:
    """Daño esperado de `move` (misma fórmula que damage.py pero con promedios).

    - Factor random fijado al promedio del rango (sin tirada).
    - Sin crítico (ruido de baja probabilidad).
    - Precisión aplicada como multiplicador (valor esperado, no tirada).

    Determinista dado (attacker, defender, move) → búsqueda reproducible.
    """
    if move.power <= 0:
        return 0.0
    atk = attacker.attack if move.category == "physical" else attacker.sp_attack
    # Defensa usada: física salvo que el flag use_def indique lo contrario.
    use_physical_def = (move.category == "physical") or (move.flags.get("use_def") == "physical")
    d_def = defender.defense if use_physical_def else defender.sp_defense
    base = (atk / max(1, d_def)) * move.power - defender.speed * config.DAMAGE_K
    if base <= 0:
        return 0.0
    stab = config.STAB_MULTIPLIER if move.type in attacker.types else 1.0
    eff = type_effectiveness(move.type, defender.types)
    if eff == 0:
        return 0.0
    lo, hi = config.DAMAGE_RANDOM_RANGE
    rand = (lo + hi) / 2.0
    if move.flags.get("always_hits") or move.accuracy <= 0:
        acc = 1.0
    else:
        acc = move.accuracy / 100.0
    return base * stab * eff * rand * acc


def max_expected_damage(attacker, defender) -> float:
    """Mayor daño esperado que `attacker` puede infligir a `defender`."""
    best = 0.0
    for m in attacker.moves:
        d = expected_damage(attacker, defender, m)
        if d > best:
            best = d
    return best


def _best_offensive_eff(attacker, defender) -> float:
    """Mejor multiplicador de efectividad entre los movs de daño del atacante.

    Si no tiene movimientos de daño, devuelve 0.0 (ofensivamente inútil), que más
    abajo se trata como el extremo inferior (-2 en log) de la ventaja de tipo.
    """
    best = 0.0
    found = False
    for m in attacker.moves:
        if m.power <= 0:
            continue
        eff = type_effectiveness(m.type, defender.types)
        if not found or eff > best:
            best, found = eff, True
    return best if found else 0.0


def _both_active_alive(state: BattleState, side: int) -> bool:
    """True si ambos Pokémon activos están en pie (matchup 'micro' bien definido)."""
    return (not state.active_pokemon(side).is_fainted
            and not state.active_pokemon(1 - side).is_fainted)


# ─── Componentes C1–C5 (cada uno ∈ [-1, 1], desde la perspectiva de `side`) ─────
def c1_hp_diff(state: BattleState, side: int) -> float:
    """C1 (macro): diferencia de HP total normalizada."""
    own = sum(p.hp for p in state.teams[side])
    opp = sum(p.hp for p in state.teams[1 - side])
    own_max = sum(p.hp_max for p in state.teams[side]) or 1
    opp_max = sum(p.hp_max for p in state.teams[1 - side]) or 1
    return own / own_max - opp / opp_max


def c2_alive_diff(state: BattleState, side: int) -> float:
    """C2 (macro): diferencia de Pokémon vivos normalizada."""
    own_alive = sum(1 for p in state.teams[side] if not p.is_fainted)
    opp_alive = sum(1 for p in state.teams[1 - side] if not p.is_fainted)
    own_n = len(state.teams[side]) or 1
    opp_n = len(state.teams[1 - side]) or 1
    return own_alive / own_n - opp_alive / opp_n


def c3_type_matchup(state: BattleState, side: int) -> float:
    """C3 (micro): ventaja de tipo del activo, en escala log simétrica.

    log₂(efectividad) con efectividad recortada a [0.25, 4] → cada lado en [-2, 2];
    la diferencia /4 queda en [-1, 1].
    """
    if not _both_active_alive(state, side):
        return 0.0
    me = state.active_pokemon(side)
    opp = state.active_pokemon(1 - side)
    off_me = min(4.0, max(0.25, _best_offensive_eff(me, opp)))
    off_opp = min(4.0, max(0.25, _best_offensive_eff(opp, me)))
    return (math.log2(off_me) - math.log2(off_opp)) / 4.0


def c4_speed_diff(state: BattleState, side: int) -> float:
    """C4 (micro): ventaja de velocidad del activo, acotada a [-1, 1]."""
    if not _both_active_alive(state, side):
        return 0.0
    me = state.active_pokemon(side)
    opp = state.active_pokemon(1 - side)
    denom = me.speed + opp.speed
    if denom == 0:
        return 0.0
    return (me.speed - opp.speed) / denom


def c5_ko_pressure(state: BattleState, side: int) -> float:
    """C5 (micro): presión de KO (puedo tumbar − pueden tumbarme) ∈ {-1, 0, 1}."""
    if not _both_active_alive(state, side):
        return 0.0
    me = state.active_pokemon(side)
    opp = state.active_pokemon(1 - side)
    i_ko = 1.0 if max_expected_damage(me, opp) >= opp.hp else 0.0
    they_ko = 1.0 if max_expected_damage(opp, me) >= me.hp else 0.0
    return i_ko - they_ko


def components(state: BattleState, side: int) -> tuple[float, float, float, float, float]:
    """Vector [C1, C2, C3, C4, C5] desde la perspectiva de `side`."""
    return (
        c1_hp_diff(state, side),
        c2_alive_diff(state, side),
        c3_type_matchup(state, side),
        c4_speed_diff(state, side),
        c5_ko_pressure(state, side),
    )


def evaluate(state: BattleState, side: int, weights: Sequence[float]) -> float:
    """H = Σ wᵢ·Cᵢ para un estado NO terminal (los terminales usan terminal_value)."""
    cs = components(state, side)
    return sum(w * c for w, c in zip(weights, cs))


def terminal_value(state: BattleState, side: int, depth: int) -> float:
    """Valor de un estado terminal: ±TERMINAL con bonus por resolver antes.

    - Ganar con más `depth` restante (antes) → valor más alto → premia rematar.
    - Perder con menos `depth` restante (más tarde) → valor menos negativo → demora la derrota.
    """
    winner = state.winner()
    if winner == side:
        return TERMINAL + depth
    return -(TERMINAL + depth)
#AGREGADO Fin
