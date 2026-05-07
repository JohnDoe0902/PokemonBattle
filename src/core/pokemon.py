"""Modelo de Pokémon: stats, movs equipados, estado de combate."""
from __future__ import annotations
import json
import random
from dataclasses import dataclass, field
from typing import Optional

import config
from .move import Move, get_move


@dataclass
class PokemonSpecies:
    """Datos inmutables de la especie (HP/ATK base, tipos, sprite)."""
    name: str
    types: tuple[str, ...]
    base_hp: int
    base_attack: int
    base_defense: int
    base_sp_attack: int
    base_sp_defense: int
    base_speed: int
    sprite_dir: str
    sprite_base: str
    learnset: tuple[str, ...]


@dataclass
class Pokemon:
    """Instancia de combate: tiene HP actual, 4 movs y PPs propios."""
    species: PokemonSpecies
    moves: list[Move]
    hp_max: int
    hp: int
    pp: list[int]  # PPs restantes paralelos a self.moves

    @classmethod
    def build(cls, species: PokemonSpecies, move_ids: list[str]) -> "Pokemon":
        moves = [get_move(mid) for mid in move_ids]
        # HP = floor((2*base + 110) * level/100) + level + 10  (aprox. con IV/EV cero)
        hp_max = int((2 * species.base_hp + 110) * config.LEVEL / 100) + 10
        return cls(
            species=species, moves=moves,
            hp_max=hp_max, hp=hp_max,
            pp=[m.pp for m in moves],
        )

    # Atajos a stats efectivos (con nivel) ─ mismo mapeo aprox. que las series
    def _stat(self, base: int) -> int:
        return int((2 * base) * config.LEVEL / 100) + 5

    @property
    def attack(self) -> int:        return self._stat(self.species.base_attack)
    @property
    def defense(self) -> int:       return self._stat(self.species.base_defense)
    @property
    def sp_attack(self) -> int:     return self._stat(self.species.base_sp_attack)
    @property
    def sp_defense(self) -> int:    return self._stat(self.species.base_sp_defense)
    @property
    def speed(self) -> int:         return self._stat(self.species.base_speed)

    @property
    def name(self) -> str:           return self.species.name
    @property
    def types(self) -> tuple[str, ...]: return self.species.types
    @property
    def is_fainted(self) -> bool:    return self.hp <= 0
    @property
    def hp_ratio(self) -> float:     return self.hp / self.hp_max if self.hp_max else 0.0

    def take_damage(self, amount: int) -> int:
        amount = max(0, int(amount))
        applied = min(self.hp, amount)
        self.hp -= applied
        return applied

    def heal(self, amount: int) -> int:
        amount = max(0, int(amount))
        before = self.hp
        self.hp = min(self.hp_max, self.hp + amount)
        return self.hp - before

    def has_pp(self, idx: int) -> bool:
        return self.pp[idx] > 0

    def consume_pp(self, idx: int) -> None:
        self.pp[idx] = max(0, self.pp[idx] - 1)

    def clone(self) -> "Pokemon":
        # species es inmutable → compartir referencia
        return Pokemon(
            species=self.species,
            moves=list(self.moves),
            hp_max=self.hp_max,
            hp=self.hp,
            pp=list(self.pp),
        )


# ─── Carga del dex y learnsets ────────────────────────────────────────────────
_SPECIES: Optional[dict[str, PokemonSpecies]] = None


def _load_species() -> dict[str, PokemonSpecies]:
    global _SPECIES
    if _SPECIES is not None:
        return _SPECIES
    with open(config.DATA_DIR / "pokemon.json", "r", encoding="utf-8") as f:
        pkmn_raw = json.load(f)
    with open(config.DATA_DIR / "learnsets.json", "r", encoding="utf-8") as f:
        learnsets_raw = json.load(f)["learnsets"]
    out: dict[str, PokemonSpecies] = {}
    for p in pkmn_raw["pokemon"]:
        out[p["name"]] = PokemonSpecies(
            name=p["name"], types=tuple(p["types"]),
            base_hp=p["hp"], base_attack=p["attack"], base_defense=p["defense"],
            base_sp_attack=p["sp_attack"], base_sp_defense=p["sp_defense"],
            base_speed=p["speed"],
            sprite_dir=p["sprite_dir"], sprite_base=p["sprite_base"],
            learnset=tuple(learnsets_raw.get(p["name"], [])),
        )
    _SPECIES = out
    return out


def get_species(name: str) -> PokemonSpecies:
    return _load_species()[name]


def all_species() -> dict[str, PokemonSpecies]:
    return _load_species()


def random_moveset(species: PokemonSpecies, k: int = config.MOVES_PER_POKEMON,
                   rng: Optional[random.Random] = None) -> list[str]:
    rng = rng or random
    pool = list(species.learnset)
    if len(pool) <= k:
        return pool
    return rng.sample(pool, k)
