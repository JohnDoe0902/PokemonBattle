"""Cálculo de daño.

Fórmula base del PDF:
    Damage = (Attack / Defense_op) * BasePower − Speed_op * K

Sobre eso aplicamos STAB (1.5 si el tipo del movimiento coincide con el del
atacante), efectividad de tipo (chart oficial), y un factor random 0.85–1.0
estilo Showdown. Si el resultado es ≤0 pero el ataque sí golpeó, devolvemos
MIN_DAMAGE.

calculate_damage devuelve un dict con todo lo necesario para mostrar mensajes
en pantalla (efectividad, stab, hit/miss, etc.).
"""
from __future__ import annotations
import random
from typing import Optional

import config
from .pokemon import Pokemon
from .move import Move
from .types import type_effectiveness


def _is_physical(move: Move) -> bool:
    if move.flags.get("use_def") == "physical":
        # ej: Psicocarga ataca usando la Def física aunque sea Especial
        return False
    return move.category == "physical"


def _accuracy_check(move: Move, rng: random.Random) -> bool:
    if move.flags.get("always_hits"):
        return True
    if move.accuracy <= 0:
        return True
    return rng.randint(1, 100) <= move.accuracy


def calculate_damage(attacker: Pokemon, defender: Pokemon, move: Move,
                     rng: Optional[random.Random] = None) -> dict:
    rng = rng or random.Random()

    info = {
        "hit": False, "damage": 0,
        "stab": 1.0, "effectiveness": 1.0, "crit": False,
        "missed": False, "no_effect": False,
        "move_type": move.type, "move_name": move.name,
    }

    # Movimientos sin poder (ej: Rayo Confuso) → sin daño en el modelo simple
    if move.power <= 0:
        info["hit"] = _accuracy_check(move, rng)
        info["missed"] = not info["hit"]
        return info

    if not _accuracy_check(move, rng):
        info["missed"] = True
        return info

    # Stats relevantes
    if move.category == "physical":
        atk = attacker.attack
    else:
        atk = attacker.sp_attack
    if _is_physical(move):
        d_def = defender.defense
    else:
        d_def = defender.sp_defense

    # Fórmula base del PDF
    base_power = move.power
    base = (atk / max(1, d_def)) * base_power - defender.speed * config.DAMAGE_K

    # STAB
    stab = config.STAB_MULTIPLIER if move.type in attacker.types else 1.0

    # Efectividad de tipo
    eff = type_effectiveness(move.type, defender.types)
    if eff == 0:
        info["no_effect"] = True
        info["effectiveness"] = 0.0
        return info

    # Crítico simple (~1/16, x1.5)
    crit = rng.randint(1, 16) == 1
    crit_mult = 1.5 if crit else 1.0

    # Random 0.85–1.0
    lo, hi = config.DAMAGE_RANDOM_RANGE
    rand = rng.uniform(lo, hi)

    raw = base * stab * eff * crit_mult * rand
    damage = max(config.MIN_DAMAGE, int(raw))

    info.update({
        "hit": True, "damage": damage,
        "stab": stab, "effectiveness": eff, "crit": crit,
    })
    return info
