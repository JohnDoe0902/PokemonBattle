"""Reproduce las frames de un .gif con su timing original."""
from __future__ import annotations
import pygame


class SpriteAnimator:
    def __init__(self, frames: list[pygame.Surface], durations: list[int],
                 scale: float = 1.0):
        self.frames = frames
        self.durations = durations or [80] * len(frames)
        self.scale = scale
        self.idx = 0
        self.elapsed = 0
        # Tweens visuales
        self.offset_x = 0
        self.offset_y = 0
        self.alpha = 255
        self._shake_t = 0.0
        self._shake_amp = 0.0

    @property
    def current(self) -> pygame.Surface | None:
        if not self.frames:
            return None
        f = self.frames[self.idx % len(self.frames)]
        if self.scale != 1.0:
            w, h = f.get_size()
            f = pygame.transform.scale(f, (int(w * self.scale), int(h * self.scale)))
        return f

    def update(self, dt_ms: int) -> None:
        if not self.frames:
            return
        self.elapsed += dt_ms
        cur_dur = self.durations[self.idx % len(self.durations)]
        if self.elapsed >= cur_dur:
            self.elapsed -= cur_dur
            self.idx = (self.idx + 1) % len(self.frames)
        if self._shake_t > 0:
            self._shake_t -= dt_ms / 1000
            import math, random
            self.offset_x = int(math.sin(self._shake_t * 60) * self._shake_amp * (self._shake_t / 0.4))
            self.offset_y = int(random.uniform(-self._shake_amp, self._shake_amp) * (self._shake_t / 0.4))
            if self._shake_t <= 0:
                self.offset_x = 0
                self.offset_y = 0

    def shake(self, amplitude: float = 8, duration_s: float = 0.4) -> None:
        self._shake_amp = amplitude
        self._shake_t = duration_s

    def draw(self, surf: pygame.Surface, center: tuple[int, int]) -> None:
        img = self.current
        if img is None:
            return
        if self.alpha < 255:
            img = img.copy()
            img.set_alpha(self.alpha)
        rect = img.get_rect(center=(center[0] + self.offset_x, center[1] + self.offset_y))
        surf.blit(img, rect)
