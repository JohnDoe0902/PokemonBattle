"""Nivel 2: heurística básica = diferencia de HP entre jugadores.

Política: para cada acción legal, simula 1 turno (lookahead 1-ply) asumiendo
que el rival usa su movimiento de mayor daño esperado. Puntúa el estado
resultante con la heurística H1 (HP diff normalizado, 0..1) y elige el mejor.

Se usa el promedio del random factor (sin RNG dentro del lookahead) para
que el agente sea determinista dada la misma información — lo que hace los
experimentos reproducibles.

> El PDF pide que el Nivel 2 use 'diferencia de HP'. Ésa es la única
> componente del scoring. La componente de tipos / velocidades / vivos
> entra en el Nivel 3.
"""
from __future__ import annotations
import random
from typing import Optional

import config
from src.core import BattleState, Action, type_effectiveness
from src.core.damage import calculate_damage
from .base_agent import Agent


def _hp_diff_normalized(state: BattleState, side: int) -> float:
    """H1: (HP propio - HP rival) sumando todo el equipo, normalizado a [-1, 1]."""
    own = sum(p.hp for p in state.teams[side])
    opp = sum(p.hp for p in state.teams[1 - side])
    own_max = sum(p.hp_max for p in state.teams[side])
    opp_max = sum(p.hp_max for p in state.teams[1 - side])
    own_norm = own / own_max if own_max else 0.0
    opp_norm = opp / opp_max if opp_max else 0.0
    return own_norm - opp_norm  # ∈ [-1, 1]


class HeuristicAgent(Agent):
    """Agente basado en H1 = diferencia normalizada de HP totales."""
    name = "Heuristic-HP"

    def __init__(self, rng: Optional[random.Random] = None):
        # rng solo para desempates entre acciones empatadas
        self.rng = rng or random.Random()

    # ─── API pública ─────────────────────────────────────────────────────────
    def choose_action(self, state: BattleState, side: int) -> Action:
        legal = state.legal_actions(side)
        if not legal:
            raise RuntimeError("HeuristicAgent: sin acciones legales")
        if len(legal) == 1:
            return legal[0]

        scored = [(self._score(state, side, a), a) for a in legal]
        best_score = max(s for s, _ in scored)
        best = [a for s, a in scored if s == best_score]
        return self.rng.choice(best)

    # ─── Lookahead 1-ply determinista ────────────────────────────────────────
    def _score(self, state: BattleState, side: int, action: Action) -> float:
        sim = state.clone()
        opp_action = self._predict_opponent(sim, 1 - side)
        actions = [None, None]
        actions[side] = action
        actions[1 - side] = opp_action
        try:
            sim.step(actions[0], actions[1])
        except Exception:
            return _hp_diff_normalized(state, side)  # acción inválida: castigo neutro
        return _hp_diff_normalized(sim, side)

    def _predict_opponent(self, state: BattleState, opp_side: int) -> Action:
        """Modelo simple del rival: usa el ataque con mayor daño esperado."""
        legal = state.legal_actions(opp_side)
        if not legal:
            return Action.attack(0)  # fallback
        attack_actions = [a for a in legal if a.kind == "attack"]
        if not attack_actions:
            return legal[0]
        attacker = state.active_pokemon(opp_side)
        defender = state.active_pokemon(1 - opp_side)
        best, best_dmg = attack_actions[0], -1.0
        for a in attack_actions:
            move = attacker.moves[a.move_index]
            dmg = self._expected_damage(attacker, defender, move)
            if dmg > best_dmg:
                best, best_dmg = a, dmg
        return best

    @staticmethod
    def _expected_damage(attacker, defender, move) -> float:
        """Daño esperado sin RNG (mismo cálculo que damage.py pero promedios)."""
        if move.power <= 0:
            return 0.0
        atk = attacker.attack if move.category == "physical" else attacker.sp_attack
        df = defender.defense if move.category == "physical" else defender.sp_defense
        base = (atk / max(1, df)) * move.power - defender.speed * config.DAMAGE_K
        if base <= 0:
            return 0.0
        stab = config.STAB_MULTIPLIER if move.type in attacker.types else 1.0
        eff = type_effectiveness(move.type, defender.types)
        if eff == 0:
            return 0.0
        # Random factor: promedio del rango
        lo, hi = config.DAMAGE_RANDOM_RANGE
        rand = (lo + hi) / 2
        # Accuracy esperada
        acc = 1.0 if move.flags.get("always_hits") else max(1, move.accuracy) / 100.0
        return base * stab * eff * rand * acc
