"""Clase base mínima para escenas. La Game las pivota mediante self.next."""
from __future__ import annotations
from typing import Optional


class Scene:
    next: Optional["Scene"] = None
    done: bool = False

    def handle_event(self, ev) -> None:  # noqa: D401 (override en subclases)
        pass

    def update(self, dt_ms: int) -> None:
        pass

    def draw(self, surf) -> None:
        pass
