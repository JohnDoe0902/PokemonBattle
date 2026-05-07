"""Selección de equipo (3 o 4 Pokémon) con grilla 6x6 e icono pixel."""
from __future__ import annotations
import pygame

import config
from src.core.pokemon import all_species
from src.ui.assets_loader import (
    get_font, load_pokemon_icon, intro_loop_dir,
)
from src.ui.widgets.video_loop import VideoLoop
from .base_scene import Scene
from .session import BattleSession
from .move_select_scene import TYPE_COLORS  # paleta compartida


# ─── Layout (constantes para que sea fácil tunear) ────────────────────────────
GRID_X = 32
GRID_Y = 110
GRID_COLS = 6
CELL = 80          # tamaño del cuadro
CELL_PAD = 4       # gap entre cuadros

CARD_X = GRID_X + GRID_COLS * (CELL + CELL_PAD) + 24
CARD_Y = GRID_Y
CARD_W = config.WINDOW_W - CARD_X - 32
CARD_H = config.WINDOW_H - CARD_Y - 110


class TeamSelectScene(Scene):
    def __init__(self, session: BattleSession, side: str):
        self.session = session
        self.side = side  # "player" | "opponent"
        self.species_names = list(all_species().keys())
        previous = session.player_team if side == "player" else session.opp_team
        self.selected: list[str] = list(previous)[: session.size]
        self.cursor = 0
        self.intro = VideoLoop(intro_loop_dir(), target_size=(config.WINDOW_W, config.WINDOW_H))
        self.confirm_rect = pygame.Rect(config.WINDOW_W - 220, config.WINDOW_H - 70, 200, 50)

    @property
    def title(self) -> str:
        side_label = "tu equipo" if self.side == "player" else "el equipo del rival"
        return f"Elige {side_label}  ·  {self.session.size} Pokémon"

    # ─── Eventos ──────────────────────────────────────────────────────────────
    def handle_event(self, ev) -> None:
        n = len(self.species_names)
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self._go_back()
                return
            if ev.key in (pygame.K_RIGHT, pygame.K_d):  self.cursor = (self.cursor + 1) % n
            elif ev.key in (pygame.K_LEFT, pygame.K_a): self.cursor = (self.cursor - 1) % n
            elif ev.key in (pygame.K_DOWN, pygame.K_s): self.cursor = (self.cursor + GRID_COLS) % n
            elif ev.key in (pygame.K_UP, pygame.K_w):   self.cursor = (self.cursor - GRID_COLS) % n
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                self._toggle(self.species_names[self.cursor])
            elif ev.key == pygame.K_TAB:
                if len(self.selected) == self.session.size:
                    self._confirm()
        elif ev.type == pygame.MOUSEMOTION:
            idx = self._index_at(ev.pos)
            if idx is not None:
                self.cursor = idx
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.confirm_rect.collidepoint(ev.pos) and len(self.selected) == self.session.size:
                self._confirm()
                return
            idx = self._index_at(ev.pos)
            if idx is not None:
                self.cursor = idx
                self._toggle(self.species_names[idx])

    def _toggle(self, name: str) -> None:
        if name in self.selected:
            self.selected.remove(name)
        elif len(self.selected) < self.session.size:
            self.selected.append(name)

    def _confirm(self) -> None:
        if self.side == "player":
            self.session.player_team = list(self.selected)
        else:
            self.session.opp_team = list(self.selected)
        from .flow import next_after_config
        self.next = next_after_config(self.session)
        self.done = True

    def _go_back(self) -> None:
        from .config_scene import ConfigScene
        self.next = ConfigScene(self.session)
        self.done = True

    # ─── Layout helpers ───────────────────────────────────────────────────────
    def _cell_rect(self, i: int) -> pygame.Rect:
        col = i % GRID_COLS
        row = i // GRID_COLS
        return pygame.Rect(GRID_X + col * (CELL + CELL_PAD),
                           GRID_Y + row * (CELL + CELL_PAD),
                           CELL, CELL)

    def _index_at(self, pos):
        for i in range(len(self.species_names)):
            if self._cell_rect(i).collidepoint(pos):
                return i
        return None

    def update(self, dt_ms: int) -> None:
        self.intro.update(dt_ms)

    # ─── Dibujo ───────────────────────────────────────────────────────────────
    def draw(self, surf) -> None:
        if self.intro.available:
            self.intro.draw(surf)
            veil = pygame.Surface((config.WINDOW_W, config.WINDOW_H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 160))
            surf.blit(veil, (0, 0))
        else:
            surf.fill((30, 30, 50))
        self._draw_header(surf)
        self._draw_grid(surf)
        self._draw_card(surf)
        self._draw_confirm(surf)

    # Header con título centrado y contador a la derecha
    def _draw_header(self, surf) -> None:
        bar = pygame.Rect(0, 36, config.WINDOW_W, 56)
        s = pygame.Surface((bar.w, bar.h), pygame.SRCALPHA)
        s.fill((20, 30, 60, 200))
        surf.blit(s, bar.topleft)
        pygame.draw.line(surf, (255, 200, 90), (0, bar.bottom), (config.WINDOW_W, bar.bottom), 3)

        title = get_font(22, bold=True).render(self.title, True, (255, 240, 220))
        surf.blit(title, (config.WINDOW_W // 2 - title.get_width() // 2,
                          bar.centery - title.get_height() // 2))

        counter = get_font(14).render(
            f"{len(self.selected)}/{self.session.size}", True, (255, 220, 100))
        surf.blit(counter, (config.WINDOW_W - counter.get_width() - 28,
                            bar.centery - counter.get_height() // 2))

    # Grilla 6x6 con iconos pixel
    def _draw_grid(self, surf) -> None:
        species_db = all_species()
        font_small = get_font(10)
        for i, name in enumerate(self.species_names):
            cell = self._cell_rect(i)
            chosen = name in self.selected
            sel = (i == self.cursor)
            # Fondo
            if sel:
                bg_c = (255, 220, 130)
            elif chosen:
                bg_c = (140, 220, 160)
            else:
                bg_c = (240, 240, 250)
            pygame.draw.rect(surf, bg_c, cell, border_radius=8)
            pygame.draw.rect(surf, (40, 40, 60), cell, width=2, border_radius=8)
            # Icono
            sp = species_db[name]
            icon = load_pokemon_icon(sp, size=cell.w - 24)
            surf.blit(icon, (cell.centerx - icon.get_width() // 2,
                             cell.y + 4))
            # Nombre corto debajo
            label = name if len(name) <= 9 else name[:8] + "."
            r = font_small.render(label, True, (40, 40, 60))
            surf.blit(r, (cell.centerx - r.get_width() // 2, cell.bottom - r.get_height() - 4))
            # Badge de orden si está elegido
            if chosen:
                idx = self.selected.index(name) + 1
                badge_rect = pygame.Rect(cell.right - 22, cell.y + 2, 18, 18)
                pygame.draw.rect(surf, (220, 60, 40), badge_rect, border_radius=4)
                pygame.draw.rect(surf, (255, 255, 255), badge_rect, width=1, border_radius=4)
                bn = get_font(10, bold=True).render(str(idx), True, (255, 255, 255))
                surf.blit(bn, (badge_rect.centerx - bn.get_width() // 2,
                               badge_rect.centery - bn.get_height() // 2))

    # Tarjeta de stats a la derecha
    def _draw_card(self, surf) -> None:
        card = pygame.Rect(CARD_X, CARD_Y, CARD_W, CARD_H)
        # Fondo con gradiente sutil
        pygame.draw.rect(surf, (250, 248, 232), card, border_radius=18)
        pygame.draw.rect(surf, (60, 50, 30), card, width=4, border_radius=18)

        target_name = self.species_names[self.cursor]
        sp = all_species()[target_name]

        # Icono (tamaño moderado para que entren los 6 stats sin recorte)
        icon_size = min(CARD_W - 80, 180)
        icon = load_pokemon_icon(sp, size=icon_size)
        ix = card.centerx - icon.get_width() // 2
        iy = card.y + 14
        surf.blit(icon, (ix, iy))

        # Nombre
        name_r = get_font(18, bold=True).render(sp.name, True, (40, 40, 60))
        surf.blit(name_r, (card.centerx - name_r.get_width() // 2, iy + icon_size + 4))

        # Tipos como tags
        tags_y = iy + icon_size + 4 + name_r.get_height() + 6
        tag_w = 84
        tags_total_w = len(sp.types) * tag_w + (len(sp.types) - 1) * 8
        tx = card.centerx - tags_total_w // 2
        for t in sp.types:
            color = TYPE_COLORS.get(t, (180, 180, 180))
            tag = pygame.Rect(tx, tags_y, tag_w, 24)
            pygame.draw.rect(surf, color, tag, border_radius=12)
            pygame.draw.rect(surf, (40, 40, 60), tag, width=1, border_radius=12)
            tr = get_font(11).render(t, True, (255, 255, 255))
            surf.blit(tr, (tag.centerx - tr.get_width() // 2,
                           tag.centery - tr.get_height() // 2))
            tx += tag_w + 8

        # Stats en barras horizontales
        stats_y = tags_y + 32
        stat_max = 200  # base máxima razonable para escalar la barra
        stats = [
            ("HP", sp.base_hp, (96, 200, 96)),
            ("ATK", sp.base_attack, (224, 96, 96)),
            ("DEF", sp.base_defense, (96, 144, 224)),
            ("AT.E", sp.base_sp_attack, (224, 144, 96)),
            ("DF.E", sp.base_sp_defense, (96, 200, 200)),
            ("VEL", sp.base_speed, (240, 200, 80)),
        ]
        bar_x = card.x + 26
        bar_w = card.w - 80
        font_lbl = get_font(11)
        font_val = get_font(11, bold=True)
        for i, (lbl, v, color) in enumerate(stats):
            y = stats_y + i * 20
            l = font_lbl.render(lbl, True, (60, 60, 80))
            surf.blit(l, (bar_x, y))
            track = pygame.Rect(bar_x + 50, y + 4, bar_w - 50, 10)
            pygame.draw.rect(surf, (210, 200, 180), track, border_radius=4)
            fill = pygame.Rect(track.x, track.y, int(track.w * min(1.0, v / stat_max)), track.h)
            pygame.draw.rect(surf, color, fill, border_radius=4)
            pygame.draw.rect(surf, (60, 50, 30), track, width=1, border_radius=4)
            val = font_val.render(str(v), True, (40, 40, 60))
            surf.blit(val, (track.right + 6, y))

    def _draw_confirm(self, surf) -> None:
        ready = (len(self.selected) == self.session.size)
        col = (60, 160, 96) if ready else (130, 130, 140)
        pygame.draw.rect(surf, col, self.confirm_rect, border_radius=12)
        pygame.draw.rect(surf, (255, 255, 255), self.confirm_rect, width=2, border_radius=12)
        c = get_font(16, bold=True).render("Confirmar", True, (255, 255, 255))
        surf.blit(c, (self.confirm_rect.centerx - c.get_width() // 2,
                      self.confirm_rect.centery - c.get_height() // 2))

        hint = get_font(11).render(
            "Click o Enter para añadir/quitar  ·  Tab confirma  ·  Esc vuelve",
            True, (220, 220, 230))
        surf.blit(hint, (32, config.WINDOW_H - 24))
