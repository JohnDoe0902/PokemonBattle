"""Menú de opciones (FIGHT/POKEMON/etc) navegable con teclado y mouse."""
from __future__ import annotations
import pygame
import config
from src.ui.assets_loader import get_font


class Menu:
    def __init__(self, rect: pygame.Rect, items: list[str], cols: int = 2, font_size: int = 22):
        self.rect = rect
        self.items = items
        self.cols = cols
        self.font = get_font(font_size)
        self.cursor = 0
        self.disabled: set[int] = set()
        self.subtitles: dict[int, str] = {}  # texto auxiliar por item (ej: PP / tipo)

    def set_items(self, items: list[str], subtitles: dict[int, str] | None = None,
                  disabled: set[int] | None = None) -> None:
        self.items = items
        self.cursor = 0
        self.subtitles = subtitles or {}
        self.disabled = disabled or set()

    @property
    def selected(self) -> int:
        return self.cursor

    def handle_event(self, ev) -> str | None:
        """Devuelve "select" si el jugador confirmó, "cancel" si canceló, o None."""
        n = len(self.items)
        if n == 0:
            return None
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.cursor = (self.cursor + 1) % n
            elif ev.key in (pygame.K_LEFT, pygame.K_a):
                self.cursor = (self.cursor - 1) % n
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.cursor = (self.cursor + self.cols) % n
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.cursor = (self.cursor - self.cols) % n
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                if self.cursor not in self.disabled:
                    return "select"
            elif ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_x):
                return "cancel"
        elif ev.type == pygame.MOUSEMOTION:
            idx = self._index_at(ev.pos)
            if idx is not None and idx not in self.disabled:
                self.cursor = idx
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            idx = self._index_at(ev.pos)
            if idx is not None and idx not in self.disabled:
                self.cursor = idx
                return "select"
        return None

    def _cell_rect(self, i: int) -> pygame.Rect:
        rows = (len(self.items) + self.cols - 1) // self.cols
        cw = self.rect.w // self.cols
        ch = self.rect.h // max(1, rows)
        col = i % self.cols
        row = i // self.cols
        return pygame.Rect(self.rect.x + col * cw + 6, self.rect.y + row * ch + 6,
                           cw - 12, ch - 12)

    def _index_at(self, pos) -> int | None:
        for i in range(len(self.items)):
            if self._cell_rect(i).collidepoint(pos):
                return i
        return None

    def draw(self, surf: pygame.Surface) -> None:
        for i, label in enumerate(self.items):
            cell = self._cell_rect(i)
            sel = (i == self.cursor)
            disabled = i in self.disabled
            bg = config.COLOR_BUTTON_SEL if sel else config.COLOR_BUTTON
            pygame.draw.rect(surf, bg, cell, border_radius=8)
            pygame.draw.rect(surf, config.COLOR_BOX_BORDER, cell, width=2, border_radius=8)
            color = config.COLOR_TEXT if not disabled else (180, 180, 180)
            r = self.font.render(label, True, color)
            tx = cell.x + 12
            ty = cell.y + (cell.h - r.get_height()) // 2
            sub = self.subtitles.get(i)
            if sub:
                sub_r = get_font(14).render(sub, True, (90, 90, 90))
                surf.blit(r, (tx, ty - sub_r.get_height() // 2))
                surf.blit(sub_r, (tx, ty + r.get_height() - 4))
            else:
                surf.blit(r, (tx, ty))
