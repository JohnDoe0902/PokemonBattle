"""Barra HP con drenaje suave estilo Pokémon."""
from __future__ import annotations
import pygame
import config


class HPBar:
    def __init__(self, w: int = 160, h: int = 8):
        self.w = w
        self.h = h
        self.target_ratio = 1.0   # 0..1
        self.shown_ratio = 1.0

    def set_target(self, ratio: float) -> None:
        self.target_ratio = max(0.0, min(1.0, ratio))

    def update(self, dt_ms: int) -> None:
        # px que se vacían en este frame
        delta = (config.HP_BAR_DRAIN_PER_S * dt_ms / 1000) / self.w
        if self.shown_ratio > self.target_ratio:
            self.shown_ratio = max(self.target_ratio, self.shown_ratio - delta)
        elif self.shown_ratio < self.target_ratio:
            self.shown_ratio = min(self.target_ratio, self.shown_ratio + delta)

    @property
    def is_settled(self) -> bool:
        return abs(self.shown_ratio - self.target_ratio) < 1e-3

    def color(self) -> tuple[int, int, int]:
        r = self.shown_ratio
        if r > 0.5:  return config.COLOR_HP_HIGH
        if r > 0.2:  return config.COLOR_HP_MID
        return config.COLOR_HP_LOW

    def draw(self, surf: pygame.Surface, topleft: tuple[int, int]) -> None:
        x, y = topleft
        pygame.draw.rect(surf, (40, 40, 40), (x - 1, y - 1, self.w + 2, self.h + 2), border_radius=3)
        pygame.draw.rect(surf, (220, 220, 220), (x, y, self.w, self.h), border_radius=2)
        fill_w = int(self.w * self.shown_ratio)
        if fill_w > 0:
            pygame.draw.rect(surf, self.color(), (x, y, fill_w, self.h), border_radius=2)
