"""Selección de los 4 movimientos por Pokémon, dentro de su learnset."""
from __future__ import annotations
import pygame

import config
from src.core.move import all_moves
from src.core.pokemon import all_species
from src.ui.assets_loader import (
    get_font, load_pokemon_sprites, intro_loop_dir,
)
from src.ui.widgets.sprite_animator import SpriteAnimator
from src.ui.widgets.video_loop import VideoLoop
from .base_scene import Scene
from .session import BattleSession


# Paleta compartida también desde aquí (evita import circular con team_select).
TYPE_COLORS = {
    "Acero": (180, 180, 200), "Agua": (100, 144, 240),  "Bicho": (168, 184, 32),
    "Dragón": (104, 64, 240), "Eléctrico": (248, 208, 48), "Fantasma": (112, 88, 152),
    "Fuego": (240, 128, 48), "Hada": (240, 168, 200),    "Hielo": (152, 216, 216),
    "Lucha": (192, 48, 40),   "Normal": (168, 168, 120), "Planta": (120, 200, 80),
    "Psíquico": (248, 88, 136), "Roca": (184, 160, 56), "Siniestro": (112, 88, 72),
    "Tierra": (224, 192, 104), "Veneno": (160, 64, 160), "Volador": (168, 144, 240),
}

# ─── Layout ───────────────────────────────────────────────────────────────────
PANEL_X = 24
PANEL_Y = 110
PANEL_W = 320
PANEL_H = config.WINDOW_H - PANEL_Y - 110

LIST_X = PANEL_X + PANEL_W + 24
LIST_Y = PANEL_Y
LIST_W = config.WINDOW_W - LIST_X - 24
CELL_H = 64
CELL_GAP = 6


class MoveSelectScene(Scene):
    def __init__(self, session: BattleSession, side: str):
        self.session = session
        self.side = side
        self.team = session.player_team if side == "player" else session.opp_team
        previous = (session.player_movesets if side == "player" else session.opp_movesets)
        self.movesets: list[list[str]] = [list(ms) for ms in previous]
        self.intro = VideoLoop(intro_loop_dir(), target_size=(config.WINDOW_W, config.WINDOW_H))
        self.idx = 0
        self.cursor = 0
        self.chosen: list[str] = list(self.movesets[0]) if self.movesets else []
        self.anim: SpriteAnimator | None = None
        self._reload_anim(reset=False)

    @property
    def species_now(self):
        return all_species()[self.team[self.idx]]

    def _learnset(self) -> list[str]:
        return list(self.species_now.learnset)

    def _reload_anim(self, reset: bool = True) -> None:
        sp = self.species_now
        data = load_pokemon_sprites(sp)
        # Mejor escala según tamaño del sprite
        self.anim = SpriteAnimator(
            data["front_frames"], data["front_durations"], scale=2.0)
        self.cursor = 0
        if reset:
            if self.idx < len(self.movesets):
                self.chosen = list(self.movesets[self.idx])
            else:
                self.chosen = []

    # ─── Eventos ──────────────────────────────────────────────────────────────
    def handle_event(self, ev) -> None:
        learnset = self._learnset()
        n = len(learnset)
        cols = 2
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self._go_back()
                return
            if ev.key in (pygame.K_DOWN, pygame.K_s):    self.cursor = (self.cursor + cols) % n
            elif ev.key in (pygame.K_UP, pygame.K_w):    self.cursor = (self.cursor - cols) % n
            elif ev.key in (pygame.K_RIGHT, pygame.K_d): self.cursor = (self.cursor + 1) % n
            elif ev.key in (pygame.K_LEFT, pygame.K_a):  self.cursor = (self.cursor - 1) % n
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                self._toggle(learnset[self.cursor])
            elif ev.key == pygame.K_TAB:
                if len(self.chosen) == config.MOVES_PER_POKEMON:
                    self._next_pokemon()
        elif ev.type == pygame.MOUSEMOTION:
            idx = self._index_at(ev.pos)
            if idx is not None:
                self.cursor = idx
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self._confirm_rect().collidepoint(ev.pos):
                if len(self.chosen) == config.MOVES_PER_POKEMON:
                    self._next_pokemon()
                return
            idx = self._index_at(ev.pos)
            if idx is not None:
                self.cursor = idx
                self._toggle(learnset[idx])

    def _toggle(self, mid: str) -> None:
        if mid in self.chosen:
            self.chosen.remove(mid)
        elif len(self.chosen) < config.MOVES_PER_POKEMON:
            self.chosen.append(mid)

    def _next_pokemon(self) -> None:
        if self.idx < len(self.movesets):
            self.movesets[self.idx] = list(self.chosen)
        else:
            self.movesets.append(list(self.chosen))
        if self.idx + 1 < len(self.team):
            self.idx += 1
            self._reload_anim()
        else:
            if self.side == "player":
                self.session.player_movesets = self.movesets
            else:
                self.session.opp_movesets = self.movesets
            from .flow import next_after_config
            self.next = next_after_config(self.session)
            self.done = True

    def _go_back(self) -> None:
        if self.idx > 0:
            self.idx -= 1
            self._reload_anim(reset=True)
            return
        side_random_team = (self.session.player_random_team if self.side == "player"
                            else self.session.opp_random_team)
        if side_random_team:
            from .config_scene import ConfigScene
            self.next = ConfigScene(self.session)
        else:
            from .team_select_scene import TeamSelectScene
            self.next = TeamSelectScene(self.session, self.side)
        self.done = True

    # ─── Layout helpers ───────────────────────────────────────────────────────
    def _cell_rect(self, i: int) -> pygame.Rect:
        col, row = i % 2, i // 2
        cw = (LIST_W - CELL_GAP) // 2
        return pygame.Rect(LIST_X + col * (cw + CELL_GAP),
                           LIST_Y + row * (CELL_H + CELL_GAP),
                           cw, CELL_H)

    def _index_at(self, pos):
        for i in range(len(self._learnset())):
            if self._cell_rect(i).collidepoint(pos):
                return i
        return None

    def _confirm_rect(self) -> pygame.Rect:
        return pygame.Rect(config.WINDOW_W - 220, config.WINDOW_H - 70, 200, 50)

    def update(self, dt_ms: int) -> None:
        if self.anim:
            self.anim.update(dt_ms)
        self.intro.update(dt_ms)

    # ─── Dibujo ───────────────────────────────────────────────────────────────
    def draw(self, surf) -> None:
        if self.intro.available:
            self.intro.draw(surf)
            veil = pygame.Surface((config.WINDOW_W, config.WINDOW_H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 165))
            surf.blit(veil, (0, 0))
        else:
            surf.fill((30, 30, 50))
        self._draw_header(surf)
        self._draw_panel(surf)
        self._draw_move_list(surf)
        self._draw_confirm(surf)

    def _draw_header(self, surf) -> None:
        bar = pygame.Rect(0, 36, config.WINDOW_W, 56)
        s = pygame.Surface((bar.w, bar.h), pygame.SRCALPHA)
        s.fill((20, 30, 60, 200))
        surf.blit(s, bar.topleft)
        pygame.draw.line(surf, (255, 200, 90), (0, bar.bottom), (config.WINDOW_W, bar.bottom), 3)

        title_text = (
            f"Movimientos de {self.species_now.name}  ·  {self.idx + 1}/{len(self.team)}"
        )
        title = get_font(20, bold=True).render(title_text, True, (255, 240, 220))
        surf.blit(title, (config.WINDOW_W // 2 - title.get_width() // 2,
                          bar.centery - title.get_height() // 2))

        side_label = "TU EQUIPO" if self.side == "player" else "EQUIPO RIVAL"
        side_r = get_font(12).render(side_label, True, (255, 220, 100))
        surf.blit(side_r, (28, bar.centery - side_r.get_height() // 2))

    def _draw_panel(self, surf) -> None:
        panel = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)
        pygame.draw.rect(surf, (250, 248, 232), panel, border_radius=18)
        pygame.draw.rect(surf, (60, 50, 30), panel, width=4, border_radius=18)

        sp = self.species_now

        # Sprite animado (más arriba para no chocar con el nombre)
        if self.anim:
            cy = panel.y + 95
            self.anim.draw(surf, (panel.centerx, cy))

        # Banner del nombre (legible incluso si el sprite cuelga la cola por aquí)
        name_r = get_font(18, bold=True).render(sp.name, True, (255, 240, 220))
        banner_w = max(name_r.get_width() + 24, 160)
        banner = pygame.Rect(panel.centerx - banner_w // 2, panel.y + 184, banner_w, 30)
        pygame.draw.rect(surf, (40, 40, 60), banner, border_radius=8)
        pygame.draw.rect(surf, (255, 200, 90), banner, width=2, border_radius=8)
        surf.blit(name_r, (banner.centerx - name_r.get_width() // 2,
                           banner.centery - name_r.get_height() // 2))

        # Tipos
        tags_y = panel.y + 222
        tag_w = 80
        tags_total = len(sp.types) * tag_w + (len(sp.types) - 1) * 8
        tx = panel.centerx - tags_total // 2
        for t in sp.types:
            color = TYPE_COLORS.get(t, (180, 180, 180))
            tag = pygame.Rect(tx, tags_y, tag_w, 22)
            pygame.draw.rect(surf, color, tag, border_radius=11)
            pygame.draw.rect(surf, (40, 40, 60), tag, width=1, border_radius=11)
            tr = get_font(10).render(t, True, (255, 255, 255))
            surf.blit(tr, (tag.centerx - tr.get_width() // 2,
                           tag.centery - tr.get_height() // 2))
            tx += tag_w + 8

        # Mini barras de stats
        stats_y = tags_y + 36
        stat_max = 200
        stats = [
            ("HP", sp.base_hp, (96, 200, 96)),
            ("ATK", sp.base_attack, (224, 96, 96)),
            ("DEF", sp.base_defense, (96, 144, 224)),
            ("ATE", sp.base_sp_attack, (224, 144, 96)),
            ("DFE", sp.base_sp_defense, (96, 200, 200)),
            ("VEL", sp.base_speed, (240, 200, 80)),
        ]
        for i, (lbl, v, color) in enumerate(stats):
            y = stats_y + i * 20
            l = get_font(10).render(lbl, True, (60, 60, 80))
            surf.blit(l, (panel.x + 20, y))
            track = pygame.Rect(panel.x + 70, y + 3, panel.w - 110, 9)
            pygame.draw.rect(surf, (210, 200, 180), track, border_radius=4)
            fill = pygame.Rect(track.x, track.y, int(track.w * min(1.0, v / stat_max)), track.h)
            pygame.draw.rect(surf, color, fill, border_radius=4)
            pygame.draw.rect(surf, (60, 50, 30), track, width=1, border_radius=4)
            val = get_font(10, bold=True).render(str(v), True, (40, 40, 60))
            surf.blit(val, (track.right + 6, y))

    def _draw_move_list(self, surf) -> None:
        moves_db = all_moves()
        learnset = self._learnset()
        for i, mid in enumerate(learnset):
            mv = moves_db[mid]
            cell = self._cell_rect(i)
            sel = (i == self.cursor)
            chosen = mid in self.chosen
            bg_c = (255, 220, 130) if sel else ((180, 240, 200) if chosen else (240, 240, 250))
            pygame.draw.rect(surf, bg_c, cell, border_radius=8)
            pygame.draw.rect(surf, (40, 40, 60), cell, width=2, border_radius=8)

            # Tag de tipo a la izquierda
            type_color = TYPE_COLORS.get(mv.type, (200, 200, 200))
            tag = pygame.Rect(cell.x + 8, cell.y + 8, 70, 18)
            pygame.draw.rect(surf, type_color, tag, border_radius=9)
            pygame.draw.rect(surf, (40, 40, 60), tag, width=1, border_radius=9)
            tg = get_font(9).render(mv.type, True, (255, 255, 255))
            surf.blit(tg, (tag.centerx - tg.get_width() // 2,
                           tag.centery - tg.get_height() // 2))

            # Categoría tag (abreviado para no recortarse)
            cat_tag = pygame.Rect(cell.x + 84, cell.y + 8, 38, 18)
            cat_col = (210, 80, 80) if mv.category == "physical" else (80, 130, 210)
            pygame.draw.rect(surf, cat_col, cat_tag, border_radius=9)
            pygame.draw.rect(surf, (40, 40, 60), cat_tag, width=1, border_radius=9)
            cat = "Fis" if mv.category == "physical" else "Esp"
            cr = get_font(10, bold=True).render(cat, True, (255, 255, 255))
            surf.blit(cr, (cat_tag.centerx - cr.get_width() // 2,
                           cat_tag.centery - cr.get_height() // 2))

            # Nombre
            nm = get_font(13, bold=True).render(mv.name, True, (40, 40, 60))
            surf.blit(nm, (cell.x + 8, cell.y + 30))

            # Stats compactas
            stats_text = f"P {mv.power}   Pr {mv.accuracy}   PP {mv.pp}"
            ss = get_font(10).render(stats_text, True, (60, 60, 80))
            surf.blit(ss, (cell.x + 8, cell.y + 47))

            if chosen:
                idx_b = self.chosen.index(mid) + 1
                badge = pygame.Rect(cell.right - 22, cell.y + 6, 18, 18)
                pygame.draw.rect(surf, (220, 60, 40), badge, border_radius=4)
                bn = get_font(10, bold=True).render(str(idx_b), True, (255, 255, 255))
                surf.blit(bn, (badge.centerx - bn.get_width() // 2,
                               badge.centery - bn.get_height() // 2))

    def _draw_confirm(self, surf) -> None:
        ready = (len(self.chosen) == config.MOVES_PER_POKEMON)
        c_rect = self._confirm_rect()
        col = (60, 160, 96) if ready else (130, 130, 140)
        pygame.draw.rect(surf, col, c_rect, border_radius=12)
        pygame.draw.rect(surf, (255, 255, 255), c_rect, width=2, border_radius=12)
        last = (self.idx + 1 == len(self.team))
        label = "¡A combatir!" if last else "Siguiente"
        c = get_font(14, bold=True).render(label, True, (255, 255, 255))
        surf.blit(c, (c_rect.centerx - c.get_width() // 2,
                      c_rect.centery - c.get_height() // 2))

        cnt = get_font(11, bold=True).render(
            f"Movs: {len(self.chosen)}/{config.MOVES_PER_POKEMON}", True, (255, 220, 100))
        surf.blit(cnt, (28, config.WINDOW_H - 50))

        hint = get_font(10).render(
            "Click/Enter añade  ·  Tab confirma  ·  Esc vuelve",
            True, (220, 220, 230))
        surf.blit(hint, (28, config.WINDOW_H - 24))
