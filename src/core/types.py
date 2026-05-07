"""Sistema de tipos y efectividades."""
import json
from functools import lru_cache
from typing import Iterable

import config

with open(config.DATA_DIR / "type_chart.json", "r", encoding="utf-8") as _f:
    _CHART_RAW = json.load(_f)

TYPES: tuple[str, ...] = tuple(_CHART_RAW["types"])
_CHART: dict[str, dict[str, float]] = _CHART_RAW["chart"]


@lru_cache(maxsize=1024)
def type_effectiveness(attack_type: str, defender_types: tuple[str, ...]) -> float:
    """Multiplicador combinado para un ataque sobre un Pokémon con uno o dos tipos."""
    mult = 1.0
    row = _CHART[attack_type]
    for t in defender_types:
        mult *= row[t]
    return mult


def effectiveness_label(mult: float) -> str:
    if mult == 0:
        return "no afecta"
    if mult >= 2.0:
        return "súper eficaz"
    if mult <= 0.5:
        return "poco eficaz"
    return ""
