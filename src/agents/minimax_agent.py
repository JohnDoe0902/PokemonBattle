"""Nivel 3: agente Minimax con poda α-β y evaluación H = Σ wᵢ·Cᵢ.

Para cada decisión explora varios turnos hacia adelante (minimax secuencial
paranoico, ver search.py) y elige la acción que maximiza la evaluación de los
componentes C1–C5 (ver evaluation.py). Los pesos `wᵢ` los optimiza el algoritmo
genético; aquí se cargan desde fuera (o se usan unos por defecto razonables).

Archivo NUEVO: forma parte del agente Nivel 3; no modifica código preexistente.
"""
#AGREGADO Inicio
from __future__ import annotations
import json
import random
from pathlib import Path
from typing import Optional, Sequence

import config
from src.core import BattleState, Action
from .base_agent import Agent
from .search import search, best_action, _force_switch, INF


# Pesos por defecto (fallback si no hay JSON entrenado). Uniformes a propósito:
# es el baseline NO INFORMADO (sin suponer qué componente importa más), la
# referencia honesta contra la que se mide lo que aprende el GA. En producción el
# agente carga los pesos entrenados desde data/level3_weights.json.
# Orden: (hp, vivos, tipo, velocidad, ko)  ─ ver evaluation.COMPONENT_NAMES
DEFAULT_WEIGHTS = (0.20, 0.20, 0.20, 0.20, 0.20)
DEFAULT_DEPTH = 3
DEFAULT_TOP_K = 2


class MinimaxAgent(Agent):
    name = "Minimax"

    def __init__(self, weights: Optional[Sequence[float]] = None,
                 depth: int = DEFAULT_DEPTH, top_k: int = DEFAULT_TOP_K,
                 rng: Optional[random.Random] = None):
        self.weights = list(weights) if weights is not None else list(DEFAULT_WEIGHTS)
        self.depth = depth
        self.top_k = top_k
        # rng sólo para desempates entre acciones igual de buenas (no toca la batalla)
        self.rng = rng or random.Random()

    @classmethod
    def from_weights_file(cls, path: Optional[str] = None,
                          depth: int = DEFAULT_DEPTH, top_k: int = DEFAULT_TOP_K,
                          rng: Optional[random.Random] = None) -> "MinimaxAgent":
        """Crea el agente cargando los pesos entrenados desde un JSON.

        Por defecto lee data/level3_weights.json. Si el archivo no existe o está
        mal formado, cae a DEFAULT_WEIGHTS (uniforme) sin romper la GUI.
        """
        p = Path(path) if path else (config.DATA_DIR / "level3_weights.json")
        try:
            with open(p, encoding="utf-8") as f:
                weights = json.load(f)["weights"]
        except (FileNotFoundError, KeyError, ValueError, TypeError):
            weights = None
        return cls(weights=weights, depth=depth, top_k=top_k, rng=rng)

    def choose_action(self, state: BattleState, side: int) -> Action:
        return best_action(state, side, self.depth, self.weights, self.top_k, self.rng)

    def choose_forced_switch(self, state: BattleState, side: int) -> Action:
        switches = state.legal_actions(side)   # con pending sólo hay cambios
        if not switches:
            return Action.attack(0)
        if len(switches) == 1:
            return switches[0]
        # Evalúa cada reemplazo resolviéndolo en solitario y buscando desde ahí.
        scored = [(search(_force_switch(state, side, sw.switch_to), side,
                          self.depth, self.weights, -INF, INF, self.top_k), sw)
                  for sw in switches]
        best_v = max(v for v, _ in scored)
        best = [sw for v, sw in scored if v == best_v]
        return self.rng.choice(best)
#AGREGADO Fin
