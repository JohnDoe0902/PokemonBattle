"""Wrapper de pygame.mixer. Si no hay archivos, juega en silencio sin crashear.

Soporta:
- Música de fondo (BGM) con loop.
- SFX cortos en assets/audio/sfx/<name>.{wav,ogg,mp3}
- Cries de Pokémon en assets/audio/cries/<sprite_base>.ogg
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

import pygame
import config
from src.utils.logger import warn


_INITIALIZED = False
_CURRENT_TRACK: Optional[str] = None
_SFX_CACHE: dict[str, Optional[pygame.mixer.Sound]] = {}
_CRY_DIR = config.ASSETS_DIR / "audio" / "cries"


def init() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    try:
        pygame.mixer.init()
        pygame.mixer.music.set_volume(config.MUSIC_VOLUME)
        _INITIALIZED = True
    except pygame.error as e:
        warn(f"No se pudo inicializar mixer: {e}")


def play_music(name: str, loop: bool = True) -> None:
    if not _INITIALIZED:
        init()
    if not _INITIALIZED:
        return
    global _CURRENT_TRACK
    if _CURRENT_TRACK == name:
        return
    for ext in ("ogg", "mp3", "wav"):
        p = config.AUDIO_MUSIC_DIR / f"{name}.{ext}"
        if p.exists():
            try:
                pygame.mixer.music.load(str(p))
                pygame.mixer.music.play(-1 if loop else 0)
                _CURRENT_TRACK = name
                return
            except pygame.error as e:
                warn(f"Error reproduciendo {p}: {e}")
    warn(f"Música '{name}' no encontrada en {config.AUDIO_MUSIC_DIR}")


def stop_music() -> None:
    if _INITIALIZED:
        pygame.mixer.music.stop()
    global _CURRENT_TRACK
    _CURRENT_TRACK = None


def _load_sound(path: Path) -> Optional[pygame.mixer.Sound]:
    try:
        snd = pygame.mixer.Sound(str(path))
        snd.set_volume(config.SFX_VOLUME)
        return snd
    except pygame.error as e:
        warn(f"SFX error {path}: {e}")
        return None


def play_sfx(name: str) -> None:
    """Reproduce un SFX corto. 'name' es el nombre sin extensión, busca en sfx/."""
    if not _INITIALIZED:
        init()
    if not _INITIALIZED:
        return
    if name in _SFX_CACHE:
        s = _SFX_CACHE[name]
        if s is not None:
            s.play()
        return
    for ext in ("wav", "ogg", "mp3"):
        p = config.AUDIO_SFX_DIR / f"{name}.{ext}"
        if p.exists():
            snd = _load_sound(p)
            _SFX_CACHE[name] = snd
            if snd is not None:
                snd.play()
            return
    _SFX_CACHE[name] = None  # marca como ausente para no reescanear cada vez


def play_hit(effectiveness: float = 1.0) -> None:
    """Variante de SFX según efectividad: súper (>1.0), normal (1.0), poco (<1.0)."""
    if effectiveness > 1.0:
        play_sfx("hit_super")
    elif effectiveness < 1.0:
        play_sfx("hit_weak")
    else:
        play_sfx("hit")


def play_cry(sprite_base: str) -> None:
    """Reproduce el grito (cry) de un Pokémon. 'sprite_base' viene del JSON."""
    if not _INITIALIZED:
        init()
    if not _INITIALIZED:
        return
    key = f"cry_{sprite_base}"
    if key in _SFX_CACHE:
        s = _SFX_CACHE[key]
        if s is not None:
            s.play()
        return
    for ext in ("ogg", "mp3", "wav"):
        p = _CRY_DIR / f"{sprite_base}.{ext}"
        if p.exists():
            snd = _load_sound(p)
            _SFX_CACHE[key] = snd
            if snd is not None:
                snd.play()
            return
    _SFX_CACHE[key] = None  # cry inexistente, no reintentar
