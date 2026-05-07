"""Reproduce un loop infinito a partir de una secuencia de PNGs pre-extraídos.

Diseñado para fondos pre-batalla (Pikachu corriendo): no depende de OpenCV
ni de imageio en runtime — sólo de Pygame.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

import pygame


class VideoLoop:
    def __init__(self, frames_dir: Path, target_size: Optional[tuple[int, int]] = None,
                 fallback_fps: float = 24.0):
        self.frames: list[pygame.Surface] = []
        self.fps = fallback_fps
        self.idx = 0
        self.elapsed_ms = 0.0
        self._available = False

        if not frames_dir.exists():
            return

        info_file = frames_dir / "info.txt"
        if info_file.exists():
            try:
                for line in info_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("fps="):
                        self.fps = float(line.split("=", 1)[1])
            except Exception:
                pass

        files = sorted(frames_dir.glob("frame_*.png"))
        for p in files:
            try:
                surf = pygame.image.load(str(p)).convert()
                if target_size and surf.get_size() != target_size:
                    surf = pygame.transform.smoothscale(surf, target_size)
                self.frames.append(surf)
            except pygame.error:
                pass

        self._available = bool(self.frames)
        self._frame_dur_ms = 1000.0 / max(1.0, self.fps)

    @property
    def available(self) -> bool:
        return self._available

    def update(self, dt_ms: int) -> None:
        if not self._available:
            return
        self.elapsed_ms += dt_ms
        while self.elapsed_ms >= self._frame_dur_ms:
            self.elapsed_ms -= self._frame_dur_ms
            self.idx = (self.idx + 1) % len(self.frames)

    def draw(self, surf: pygame.Surface, alpha: int = 255) -> None:
        if not self._available:
            return
        f = self.frames[self.idx]
        if alpha < 255:
            f = f.copy()
            f.set_alpha(alpha)
        surf.blit(f, (0, 0))
