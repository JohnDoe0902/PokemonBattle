"""Pantalla de configuración previa al combate.

Permite elegir:
- Tamaño del equipo (3 o 4, 1v1 simultáneos)
- Equipo del jugador: manual o aleatorio
- Equipo del rival: manual o aleatorio
- Movimientos del jugador: manual o aleatorio (de su learnset)
- Movimientos del rival: manual o aleatorio
- Tipo de agente rival: Random (Nivel 1) o Heuristic (Nivel 2)
"""
from __future__ import annotations
import pygame

import config
from src.ui.assets_loader import get_font, make_battle_background, intro_loop_dir
from src.ui.widgets.menu import Menu
from src.ui.widgets.video_loop import VideoLoop
from .base_scene import Scene
from .session import BattleSession


class ConfigScene(Scene):
    OPTIONS = [
        ("size",                 "Tamaño del equipo",       ["3 vs 3", "4 vs 4"]),
        ("player_random_team",   "Tu equipo",               ["Elegir manual", "Aleatorio"]),
        ("opp_random_team",      "Equipo rival",            ["Elegir manual", "Aleatorio"]),
        ("player_random_moves",  "Tus movimientos",         ["Elegir manual", "Aleatorio"]),
        ("opp_random_moves",     "Movs del rival",          ["Elegir manual", "Aleatorio"]),
        ("opp_agent",            "Inteligencia del rival",  ["Nivel 1 (Random)", "Nivel 2 (Heurística)", "Nivel 3 (Minimax)"]),  #AGREGADO (Nivel 3)
    ]

    def __init__(self, session: BattleSession | None = None):
        self.session = session or BattleSession()
        # Reflejar lo que ya esté en la sesión (caso al volver con Esc)
        self.values = [
            1 if self.session.size == 4 else 0,
            1 if self.session.player_random_team else 0,
            1 if self.session.opp_random_team else 0,
            1 if self.session.player_random_moves else 0,
            1 if self.session.opp_random_moves else 0,
            {"Random": 0, "Heuristic": 1, "Minimax": 2}.get(self.session.opp_agent, 1),  #AGREGADO (mapeo 3 opciones)
        ]
        self.cursor = 0
        self.bg_static = make_battle_background((config.WINDOW_W, config.WINDOW_H))
        self.intro = VideoLoop(intro_loop_dir(), target_size=(config.WINDOW_W, config.WINDOW_H))
        self.fade_in = config.SCENE_FADE_MS
        self.fade_t = 0
        self.button_rect = pygame.Rect(config.WINDOW_W // 2 - 110, config.WINDOW_H - 90, 220, 56)

    def handle_event(self, ev) -> None:
        n = len(self.OPTIONS)
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                from .menu_scene import MenuScene
                self.next = MenuScene(self.session)
                self.done = True
                return
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.cursor = (self.cursor + 1) % (n + 1)
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.cursor = (self.cursor - 1) % (n + 1)
            elif ev.key in (pygame.K_LEFT, pygame.K_a):
                if self.cursor < n:
                    opts = self.OPTIONS[self.cursor][2]
                    self.values[self.cursor] = (self.values[self.cursor] - 1) % len(opts)
            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                if self.cursor < n:
                    opts = self.OPTIONS[self.cursor][2]
                    self.values[self.cursor] = (self.values[self.cursor] + 1) % len(opts)
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                if self.cursor == n:
                    self._commit_and_next()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.button_rect.collidepoint(ev.pos):
                self._commit_and_next()
            else:
                # click en una fila → cicla esa opción
                for i in range(n):
                    rect = self._row_rect(i)
                    if rect.collidepoint(ev.pos):
                        self.cursor = i
                        opts = self.OPTIONS[i][2]
                        self.values[i] = (self.values[i] + 1) % len(opts)
                        break

    def _commit_and_next(self) -> None:
        s = self.session
        s.size = 3 if self.values[0] == 0 else 4
        s.player_random_team  = (self.values[1] == 1)
        s.opp_random_team     = (self.values[2] == 1)
        s.player_random_moves = (self.values[3] == 1)
        s.opp_random_moves    = (self.values[4] == 1)
        s.opp_agent           = {0: "Random", 1: "Heuristic", 2: "Minimax"}[self.values[5]]  #AGREGADO (mapeo 3 opciones)
        from .flow import next_after_config
        self.next = next_after_config(s)
        self.done = True

    def update(self, dt_ms: int) -> None:
        self.fade_t = min(self.fade_in, self.fade_t + dt_ms)
        self.intro.update(dt_ms)

    def _row_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(120, 120 + i * 60, config.WINDOW_W - 240, 50)

    def draw(self, surf) -> None:
        if self.intro.available:
            self.intro.draw(surf)
            veil = pygame.Surface((config.WINDOW_W, config.WINDOW_H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 165))
            surf.blit(veil, (0, 0))
        else:
            surf.blit(self.bg_static, (0, 0))
        # Banner — mismo estilo que TeamSelect/MoveSelect
        bar = pygame.Rect(0, 36, config.WINDOW_W, 56)
        s = pygame.Surface((bar.w, bar.h), pygame.SRCALPHA)
        s.fill((20, 30, 60, 200))
        surf.blit(s, bar.topleft)
        pygame.draw.line(surf, (255, 200, 90), (0, bar.bottom), (config.WINDOW_W, bar.bottom), 3)
        title_font = get_font(22, bold=True)
        t = title_font.render("Configuración del combate", True, (255, 240, 220))
        surf.blit(t, (config.WINDOW_W // 2 - t.get_width() // 2,
                      bar.centery - t.get_height() // 2))

        font = get_font(22)
        small = get_font(16)
        for i, (key, label, opts) in enumerate(self.OPTIONS):
            rect = self._row_rect(i)
            sel = (i == self.cursor)
            bg_color = config.COLOR_BUTTON_SEL if sel else config.COLOR_BUTTON
            pygame.draw.rect(surf, bg_color, rect, border_radius=10)
            pygame.draw.rect(surf, config.COLOR_BOX_BORDER, rect, width=2, border_radius=10)

            lbl = font.render(label, True, config.COLOR_TEXT)
            surf.blit(lbl, (rect.x + 18, rect.y + (rect.h - lbl.get_height()) // 2))

            value_str = opts[self.values[i]]
            v = font.render(value_str, True, config.COLOR_ACCENT)
            value_x = rect.right - v.get_width() - 40
            value_y = rect.y + (rect.h - v.get_height()) // 2
            surf.blit(v, (value_x, value_y))
            # Triángulos ◀ ▶ dibujados (independientes de la fuente)
            cy = rect.centery
            tri_color = config.COLOR_ACCENT if sel else (120, 120, 140)
            # izquierda
            lx = value_x - 18
            pygame.draw.polygon(surf, tri_color,
                [(lx + 8, cy - 8), (lx + 8, cy + 8), (lx - 4, cy)])
            # derecha
            rx = value_x + v.get_width() + 6
            pygame.draw.polygon(surf, tri_color,
                [(rx, cy - 8), (rx, cy + 8), (rx + 12, cy)])

        # Botón Comenzar
        sel_btn = (self.cursor == len(self.OPTIONS))
        col = config.COLOR_BUTTON_SEL if sel_btn else config.COLOR_ACCENT
        pygame.draw.rect(surf, col, self.button_rect, border_radius=14)
        pygame.draw.rect(surf, config.COLOR_BOX_BORDER, self.button_rect, width=3, border_radius=14)
        b = get_font(26, bold=True).render("¡Comenzar!", True, config.COLOR_TEXT_LIGHT if not sel_btn else config.COLOR_TEXT)
        surf.blit(b, (self.button_rect.centerx - b.get_width() // 2,
                      self.button_rect.centery - b.get_height() // 2))

        hint = small.render("Flechas para cambiar  ·  Enter para confirmar  ·  Esc para volver", True, (200, 200, 220))
        surf.blit(hint, ((config.WINDOW_W - hint.get_width()) // 2, config.WINDOW_H - 28))

        # Fade in
        if self.fade_t < self.fade_in:
            alpha = int(255 * (1 - self.fade_t / self.fade_in))
            overlay = pygame.Surface((config.WINDOW_W, config.WINDOW_H))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(alpha)
            surf.blit(overlay, (0, 0))
