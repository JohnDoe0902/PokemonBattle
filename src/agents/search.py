"""Búsqueda del agente Nivel 3.

Contiene:
- `simulate_turn`: transición DETERMINISTA de un turno (daño esperado, sin RNG),
  con el mismo orden que `BattleState.step` (cambios primero → ataques por
  prioridad/velocidad). Hace el árbol del minimax determinista y reproducible.
- `ordered_actions`: genera, ordena (para mejorar la poda α-β) y poda los cambios
  (top-K por matchup).
- `search`: minimax secuencial paranoico con poda α-β. Maneja también los cambios
  FORZADOS como el bucle real del juego (resolución en solitario, sin ataque rival).
- `best_action`: capa raíz que devuelve la mejor acción.

Archivo NUEVO: forma parte del agente Nivel 3; no modifica código preexistente.
"""
#AGREGADO Inicio
from __future__ import annotations
import math
import random

import config
from src.core import BattleState, Action
from .evaluation import expected_damage, evaluate, terminal_value, _best_offensive_eff


# RNG ficticio: `simulate_turn` es determinista y NUNCA extrae de él. Se pasa a
# clone() para que la clonación no consuma el RNG real de la batalla (preserva el
# CRN del entrenamiento del GA; ver agente 3.md §6).
_DET_RNG = random.Random(0)


def _order_key(state: BattleState, side: int, action: Action):
    """Orden de ataque: prioridad, luego velocidad. Empates → sort estable (lado 0 antes)."""
    active = state.active_pokemon(side)
    move = active.moves[action.move_index]
    priority = int(move.flags.get("priority", 0))
    return (priority, active.speed)


def _apply_switch(state: BattleState, side: int, to_index: int) -> None:
    state.active[side] = to_index
    state.pending_switch[side] = False


def _apply_attack(state: BattleState, side: int, move_idx: int) -> None:
    attacker = state.active_pokemon(side)
    defender = state.active_pokemon(1 - side)
    move = attacker.moves[move_idx]
    # Mismo recurso sin PPs que el motor real: el ataque hace daño mínimo.
    out_of_pp = not attacker.has_pp(move_idx)
    attacker.consume_pp(move_idx)
    dmg = expected_damage(attacker, defender, move)
    if out_of_pp:
        dmg = min(dmg, float(config.MIN_DAMAGE))
    if dmg > 0:
        defender.take_damage(int(dmg))


def simulate_turn(state: BattleState, action0: Action, action1: Action) -> BattleState:
    """Devuelve un NUEVO estado tras resolver el turno de forma determinista.

    No muta `state`: clona y trabaja sobre la copia. Mismo orden que el motor real:
    1) cambios primero (ambos lados), 2) ataques por (prioridad, velocidad).
    Si tras un ataque el defensor cae, se marca su `pending_switch`.
    """
    child = state.clone(rng=_DET_RNG)   # no consume el RNG de `state`
    actions = [action0, action1]

    # 1. Cambios primero (estilo Showdown)
    for s in (0, 1):
        a = actions[s]
        if a is not None and a.kind == "switch":
            _apply_switch(child, s, a.switch_to)

    # 2. Ataques en orden por (prioridad, velocidad); desempate estable → lado 0 antes
    atk_sides = [s for s in (0, 1)
                 if actions[s] is not None and actions[s].kind == "attack"
                 and not child.teams[s][child.active[s]].is_fainted]
    atk_sides.sort(key=lambda s: _order_key(child, s, actions[s]), reverse=True)

    for s in atk_sides:
        if child.is_over():
            break
        if child.active_pokemon(s).is_fainted:
            continue
        other = 1 - s
        _apply_attack(child, s, actions[s].move_index)
        if child.active_pokemon(other).is_fainted:
            child.pending_switch[other] = True

    child.turn += 1
    return child


# ─── Generación, ordenado y poda de acciones ───────────────────────────────────
INF = float("inf")


def _switch_matchup_score(state: BattleState, side: int, bench_index: int) -> float:
    """Calidad del matchup del Pokémon de banca `bench_index` frente al activo rival.

    Escala log simétrica: mayor = mejor para `side` (yo pego fuerte, me pegan flojo).
    """
    opp = state.active_pokemon(1 - side)
    incoming = state.teams[side][bench_index]
    off = min(4.0, max(0.25, _best_offensive_eff(incoming, opp)))
    deff = min(4.0, max(0.25, _best_offensive_eff(opp, incoming)))
    return math.log2(off) - math.log2(deff)


def ordered_actions(state: BattleState, side: int, top_k: int) -> list[Action]:
    """Acciones legales ordenadas para mejorar la poda α-β, con poda de cambios.

    - Ataques primero, ordenados por daño esperado descendente (los KO emergen primero).
    - Cambios: solo los `top_k` mejores por calidad de matchup del Pokémon entrante.

    Para la capa MIN (rival), ordenar sus ataques por daño esperado equivale a poner
    primero su jugada más peligrosa para mí → más cortes.
    """
    legal = state.legal_actions(side)
    attacks = [a for a in legal if a.kind == "attack"]
    switches = [a for a in legal if a.kind == "switch"]

    active = state.active_pokemon(side)
    defender = state.active_pokemon(1 - side)
    if not active.is_fainted:
        attacks.sort(
            key=lambda a: expected_damage(active, defender, active.moves[a.move_index]),
            reverse=True,
        )
    if switches and top_k is not None:
        switches.sort(key=lambda a: _switch_matchup_score(state, side, a.switch_to), reverse=True)
        switches = switches[:max(0, top_k)]
    return attacks + switches


# ─── Minimax secuencial paranoico con α-β ──────────────────────────────────────
def _force_switch(state: BattleState, side: int, to_index: int) -> BattleState:
    """Resolución de un cambio FORZADO (en solitario, sin ataque rival).

    Modela fielmente el bucle real del juego: cuando un Pokémon cae, ese lado envía
    su reemplazo sin que el rival ataque en esa resolución.
    """
    child = state.clone(rng=_DET_RNG)
    child.active[side] = to_index
    child.pending_switch[side] = False
    return child


def _joint(me: int, my_action: Action, opp_action: Action) -> tuple[Action, Action]:
    """Coloca las acciones por índice de lado para simulate_turn(action0, action1)."""
    return (my_action, opp_action) if me == 0 else (opp_action, my_action)


def _min_over_opp(state, me, my_action, depth, weights, alpha, beta, top_k):
    """Capa MIN (paranoica): el rival responde viendo mi jugada y minimiza mi valor."""
    opp = 1 - me
    worst = INF
    for b in ordered_actions(state, opp, top_k):
        a0, a1 = _joint(me, my_action, b)
        child = simulate_turn(state, a0, a1)
        v = search(child, me, depth - 1, weights, alpha, beta, top_k)
        if v < worst:
            worst = v
        if worst <= alpha:
            break               # corte α
        if worst < beta:
            beta = worst
    return worst


def _search_forced(state, me, depth, weights, alpha, beta, top_k):
    """Nodo de cambio forzado: resuelve el reemplazo del lado con pending_switch.

    No consume profundidad (es una sub-resolución de la posición actual, no un turno).
    """
    opp = 1 - me
    if state.pending_switch[me]:        # MAX: yo elijo mi reemplazo
        best = -INF
        for sw in state.legal_actions(me):      # con pending sólo hay cambios
            child = _force_switch(state, me, sw.switch_to)
            v = search(child, me, depth, weights, alpha, beta, top_k)
            if v > best:
                best = v
            if best >= beta:
                break
            if best > alpha:
                alpha = best
        return best
    # MIN: el rival elige su reemplazo (peor caso para mí)
    worst = INF
    for sw in state.legal_actions(opp):
        child = _force_switch(state, opp, sw.switch_to)
        v = search(child, me, depth, weights, alpha, beta, top_k)
        if v < worst:
            worst = v
        if worst <= alpha:
            break
        if worst < beta:
            beta = worst
    return worst


def search(state, me, depth, weights, alpha=-INF, beta=INF, top_k=2) -> float:
    """Minimax secuencial paranoico con poda α-β. Valor desde la perspectiva de `me`.

    Cada nivel de recursión = un turno completo (mi capa MAX + capa MIN del rival),
    salvo los cambios forzados, que se resuelven aparte sin gastar profundidad.
    """
    if state.is_over():
        return terminal_value(state, me, depth)
    if depth <= 0:
        return evaluate(state, me, weights)
    if state.pending_switch[me] or state.pending_switch[1 - me]:
        return _search_forced(state, me, depth, weights, alpha, beta, top_k)

    best = -INF
    for a in ordered_actions(state, me, top_k):
        v = _min_over_opp(state, me, a, depth, weights, alpha, beta, top_k)
        if v > best:
            best = v
        if best >= beta:
            break               # corte β
        if best > alpha:
            alpha = best
    return best


def best_action(state, me, depth, weights, top_k, rng) -> Action:
    """Raíz: devuelve la mejor acción. Ventana completa por acción → valores exactos.

    Empates entre acciones igual de buenas se rompen con `rng` (reproducible).
    """
    legal = ordered_actions(state, me, top_k)
    if not legal:
        all_legal = state.legal_actions(me)
        return all_legal[0] if all_legal else Action.attack(0)
    if len(legal) == 1:
        return legal[0]
    scored = [(_min_over_opp(state, me, a, depth, weights, -INF, INF, top_k), a)
              for a in legal]
    best_v = max(v for v, _ in scored)
    best = [a for v, a in scored if v == best_v]
    return rng.choice(best)
#AGREGADO Fin
