"""Escena de título: 'POKEFISI — pulsa cualquier tecla'."""
from __future__ import annotations
import math
import pygame

import config
from src.ui.assets_loader import get_font, make_battle_background, intro_loop_dir
from src.ui.widgets.video_loop import VideoLoop
from src.ui import audio
from .base_scene import Scene
from .session import BattleSession


class MenuScene(Scene):
    def __init__(self, session: BattleSession | None = None):
        self.session = session or BattleSession()
        self.bg_static = make_battle_background((config.WINDOW_W, config.WINDOW_H))
        self.intro = VideoLoop(intro_loop_dir(), target_size=(config.WINDOW_W, config.WINDOW_H))
        self.t = 0
        self.subtitle_alpha = 0
        audio.play_music("menu")

    def handle_event(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            return  # No se sale del título con Escape (hay que cerrar la ventana)
        if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            from .config_scene import ConfigScene
            self.next = ConfigScene(self.session)
            self.done = True

    def update(self, dt_ms: int) -> None:
        self.t += dt_ms
        self.subtitle_alpha = int(127 + 127 * math.sin(self.t / 400))
        self.intro.update(dt_ms)

    def draw(self, surf) -> None:
        if self.intro.available:
            self.intro.draw(surf)
            # Velo muy leve solo para mejorar contraste del subtítulo en zonas claras.
            veil = pygame.Surface((config.WINDOW_W, config.WINDOW_H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 35))
            surf.blit(veil, (0, 0))
        else:
            surf.blit(self.bg_static, (0, 0))
        title_font = get_font(82, bold=True)
        title_x = (config.WINDOW_W - title_font.size("POKEFISI")[0]) // 2
        title_y = (config.WINDOW_H - title_font.get_height()) // 2 - 60
        # Contorno oscuro (4 direcciones) para que destaque sobre cualquier fondo
        outline = title_font.render("POKEFISI", True, (20, 20, 40))
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-3, -3), (3, 3), (-3, 3), (3, -3)]:
            surf.blit(outline, (title_x + dx, title_y + dy))
        # Sombra dorada
        shadow = title_font.render("POKEFISI", True, (240, 200, 64))
        surf.blit(shadow, (title_x + 4, title_y + 4))
        # Texto principal
        title = title_font.render("POKEFISI", True, (255, 240, 220))
        surf.blit(title, (title_x, title_y))

        sub_font = get_font(22)
        sub = sub_font.render("Pulsa cualquier tecla para empezar", True, (32, 32, 32))
        sub.set_alpha(self.subtitle_alpha)
        surf.blit(sub, ((config.WINDOW_W - sub.get_width()) // 2, config.WINDOW_H - 120))

        cred = get_font(14).render("Simulación estratégica de combates tipo Pokémon · IA UNMSM", True, (60, 60, 60))
        surf.blit(cred, ((config.WINDOW_W - cred.get_width()) // 2, config.WINDOW_H - 36))
