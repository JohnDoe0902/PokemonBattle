"""Estado y motor del combate por turnos.

Reglas implementadas:
- Cada turno los dos jugadores eligen una Action. Los cambios resuelven antes
  que los ataques. Entre dos ataques actúa primero el de mayor velocidad
  (con priority como desempate; empate ⇒ aleatorio).
- Si un Pokémon cae a 0 HP, su entrenador debe elegir un reemplazo antes del
  siguiente turno (a través de pending_switch).
- La batalla termina cuando un equipo no tiene Pokémon vivos.

Pensado para ser puro: ninguna llamada a Pygame ni I/O. La UI consume `log`.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional

import config
from .pokemon import Pokemon
from .action import Action
from .damage import calculate_damage
from .types import effectiveness_label


@dataclass
class BattleEvent:
    """Cualquier evento mostrable: 'X usó Y!', '¡Es súper eficaz!', etc."""
    kind: str
    text: str
    data: dict = field(default_factory=dict)


class BattleState:
    def __init__(self, team_a: list[Pokemon], team_b: list[Pokemon],
                 names: tuple[str, str] = ("Jugador", "Rival"),
                 rng: Optional[random.Random] = None):
        self.teams: list[list[Pokemon]] = [team_a, team_b]
        self.names = names
        self.active: list[int] = [0, 0]
        self.turn: int = 0
        self.rng = rng or random.Random()
        self.log: list[BattleEvent] = []
        # Si algún lado tiene su Pokémon caído, debe elegir reemplazo antes
        # del siguiente step. Ese lado va aquí.
        self.pending_switch: list[bool] = [False, False]

    # ─── Helpers ──────────────────────────────────────────────────────────────
    def active_pokemon(self, side: int) -> Pokemon:
        return self.teams[side][self.active[side]]

    def alive_indices(self, side: int) -> list[int]:
        return [i for i, p in enumerate(self.teams[side]) if not p.is_fainted]

    def is_over(self) -> bool:
        return any(all(p.is_fainted for p in t) for t in self.teams)

    def winner(self) -> Optional[int]:
        if not self.is_over():
            return None
        return 0 if any(not p.is_fainted for p in self.teams[0]) else 1

    def legal_actions(self, side: int) -> list[Action]:
        actions: list[Action] = []
        if self.pending_switch[side]:
            for i in self.alive_indices(side):
                if i != self.active[side]:
                    actions.append(Action.switch(i))
            return actions
        active = self.active_pokemon(side)
        if not active.is_fainted:
            for i, m in enumerate(active.moves):
                if active.has_pp(i):
                    actions.append(Action.attack(i))
            # Si por alguna razón no quedan PPs, permitir Forcejeo (omito por simplicidad)
            if not actions:
                # Permitir cualquier ataque sin PP como recurso (hace daño 1 mínimo)
                for i, _ in enumerate(active.moves):
                    actions.append(Action.attack(i))
        for i in self.alive_indices(side):
            if i != self.active[side]:
                actions.append(Action.switch(i))
        return actions

    # ─── Avanzar el combate ───────────────────────────────────────────────────
    def step(self, action_a: Action, action_b: Action) -> list[BattleEvent]:
        """Ejecuta un turno completo y devuelve los eventos generados."""
        events: list[BattleEvent] = []
        actions = [action_a, action_b]

        # Si alguien tenía pending_switch, esa acción debe ser un switch
        for side in (0, 1):
            if self.pending_switch[side]:
                if actions[side].kind != "switch":
                    raise ValueError(
                        f"El lado {side} debe enviar un cambio (su Pokémon está caído)."
                    )

        # 1. Resolver cambios (ambos antes de los ataques, estilo Showdown)
        for side in (0, 1):
            a = actions[side]
            if a.kind == "switch":
                self._do_switch(side, a.switch_to, events)

        # 2. Resolver ataques en orden por velocidad (con priority)
        atk_sides = [s for s in (0, 1) if actions[s].kind == "attack"
                     and not self.teams[s][self.active[s]].is_fainted]
        atk_sides.sort(key=lambda s: self._priority_key(s, actions[s]), reverse=True)
        for side in atk_sides:
            if self.is_over():
                break
            other = 1 - side
            if self.active_pokemon(side).is_fainted:
                continue
            self._do_attack(side, actions[side].move_index, events)
            if self.active_pokemon(other).is_fainted:
                self.pending_switch[other] = True

        # 3. Limpieza turn end
        self.turn += 1
        self.log.extend(events)
        return events

    def force_switch(self, side: int, to_index: int) -> list[BattleEvent]:
        """Llamada cuando un lado tenía pending_switch fuera de un step normal."""
        events: list[BattleEvent] = []
        self._do_switch(side, to_index, events)
        self.log.extend(events)
        return events

    # ─── Ejecución de acciones individuales ───────────────────────────────────
    def _do_switch(self, side: int, to_index: int, events: list[BattleEvent]) -> None:
        if to_index < 0 or to_index >= len(self.teams[side]):
            raise ValueError(f"Índice de cambio inválido: {to_index}")
        if self.teams[side][to_index].is_fainted:
            raise ValueError(f"No puedes cambiar a un Pokémon debilitado.")
        if to_index == self.active[side] and not self.pending_switch[side]:
            raise ValueError(f"Ese Pokémon ya está en combate.")
        old = self.active_pokemon(side)
        if not old.is_fainted:
            events.append(BattleEvent(
                "switch_out", f"{self.names[side]} retiró a {old.name}.",
                {"side": side, "from": old.name},
            ))
        self.active[side] = to_index
        new_p = self.active_pokemon(side)
        events.append(BattleEvent(
            "switch_in", f"{self.names[side]} envió a {new_p.name}!",
            {"side": side, "to": new_p.name},
        ))
        self.pending_switch[side] = False

    def _do_attack(self, side: int, move_idx: int, events: list[BattleEvent]) -> None:
        attacker = self.active_pokemon(side)
        defender = self.active_pokemon(1 - side)
        move = attacker.moves[move_idx]
        attacker.consume_pp(move_idx)
        events.append(BattleEvent(
            "use_move", f"¡{attacker.name} usó {move.name}!",
            {"side": side, "move": move.name},
        ))
        info = calculate_damage(attacker, defender, move, self.rng)
        if info["no_effect"]:
            events.append(BattleEvent("no_effect", "No afecta a " + defender.name + "...", {"side": 1 - side}))
            return
        if info["missed"]:
            events.append(BattleEvent("missed", f"¡{attacker.name} falló!", {"side": side}))
            return
        dealt = defender.take_damage(info["damage"])
        events.append(BattleEvent(
            "damage",
            f"{defender.name} recibió {dealt} de daño.",
            {"side": 1 - side, "amount": dealt, "hp_now": defender.hp, "hp_max": defender.hp_max},
        ))
        if info["crit"]:
            events.append(BattleEvent("crit", "¡Un golpe crítico!", {}))
        if info["effectiveness"] != 1.0:
            label = effectiveness_label(info["effectiveness"])
            if label:
                events.append(BattleEvent("eff", f"¡{label.capitalize()}!", {"mult": info["effectiveness"]}))
        if defender.is_fainted:
            events.append(BattleEvent(
                "faint", f"¡{defender.name} se debilitó!",
                {"side": 1 - side, "name": defender.name},
            ))

    def _priority_key(self, side: int, action: Action) -> tuple[int, int, float]:
        """Llave de orden: priority del mov, luego velocidad, luego desempate aleatorio."""
        active = self.active_pokemon(side)
        move = active.moves[action.move_index]
        priority = int(move.flags.get("priority", 0))
        speed = active.speed
        return (priority, speed, self.rng.random())

    # ─── Snapshot / clonación (para Minimax en niveles 3+) ────────────────────
    def clone(self) -> "BattleState":
        new = BattleState(
            [p.clone() for p in self.teams[0]],
            [p.clone() for p in self.teams[1]],
            names=self.names,
            rng=random.Random(self.rng.random()),
        )
        new.active = list(self.active)
        new.turn = self.turn
        new.pending_switch = list(self.pending_switch)
        # log/log no se copia: la simulación de lookahead no necesita texto
        return new
