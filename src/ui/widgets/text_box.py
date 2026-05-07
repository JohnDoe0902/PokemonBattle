"""Caja de diálogo con typewriter (texto letra a letra)."""
from __future__ import annotations
import pygame
import config
from src.ui.assets_loader import get_font


class TextBox:
    def __init__(self, rect: pygame.Rect, font_size: int = 22):
        self.rect = rect
        self.font = get_font(font_size)
        self._lines: list[str] = []
        self._target_text = ""
        self._shown_chars = 0
        self._chars_per_s = config.TEXT_SPEED_CPS
        self._done = True

    def set_text(self, text: str) -> None:
        self._target_text = text
        self._shown_chars = 0
        self._done = False
        self._lines = self._wrap(text)

    @property
    def is_done(self) -> bool:
        return self._done

    def skip(self) -> None:
        self._shown_chars = len(self._target_text)
        self._done = True

    def update(self, dt_ms: int) -> None:
        if self._done:
            return
        self._shown_chars += self._chars_per_s * dt_ms / 1000
        if self._shown_chars >= len(self._target_text):
            self._shown_chars = len(self._target_text)
            self._done = True

    def _wrap(self, text: str) -> list[str]:
        max_w = self.rect.w - 24
        words = text.split(" ")
        lines: list[str] = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.font.size(test)[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def draw(self, surf: pygame.Surface) -> None:
        # Caja
        pygame.draw.rect(surf, config.COLOR_BOX, self.rect, border_radius=10)
        pygame.draw.rect(surf, config.COLOR_BOX_BORDER, self.rect, width=3, border_radius=10)
        # Texto progresivo, centrado verticalmente sobre el bloque final
        shown = int(self._shown_chars)
        partial = self._target_text[:shown]
        # Para que el texto no “salte” mientras crece, centramos respecto al
        # número final de líneas, no al parcial actual.
        target_lines = self._lines or self._wrap(self._target_text)
        partial_lines = self._wrap(partial)
        line_h = self.font.get_linesize()
        total_h = line_h * max(1, len(target_lines))
        y = self.rect.centery - total_h // 2
        for ln in partial_lines:
            r = self.font.render(ln, True, config.COLOR_TEXT)
            surf.blit(r, (self.rect.x + 18, y))
            y += line_h
        # Triangulito 'continuar' cuando termina
        if self._done:
            t_x = self.rect.right - 22
            t_y = self.rect.bottom - 18
            pulse = (pygame.time.get_ticks() // 300) % 2
            offset = 0 if pulse == 0 else 2
            pygame.draw.polygon(surf, config.COLOR_BOX_BORDER, [
                (t_x, t_y + offset), (t_x + 12, t_y + offset), (t_x + 6, t_y + 8 + offset)
            ])
