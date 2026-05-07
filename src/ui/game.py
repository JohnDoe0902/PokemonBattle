"""Loop principal de Pygame: gestiona la escena activa y los transitions."""
from __future__ import annotations
import pygame

import config
from src.ui import audio
from src.ui.scenes.menu_scene import MenuScene


def run() -> None:
    pygame.init()
    pygame.display.set_caption(config.WINDOW_TITLE)
    surf = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H))
    clock = pygame.time.Clock()
    audio.init()

    scene = MenuScene()

    running = True
    while running:
        dt = clock.tick(config.FPS)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_F4 and (
                    pygame.key.get_mods() & pygame.KMOD_ALT):
                running = False
            else:
                scene.handle_event(ev)

        scene.update(dt)
        scene.draw(surf)
        pygame.display.flip()

        if scene.done and scene.next is not None:
            scene = scene.next

    pygame.quit()
