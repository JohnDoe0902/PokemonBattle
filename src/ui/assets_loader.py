"""Carga de assets: GIFs (con Pillow), fuentes y audio.

Los GIFs animados se descomponen frame a frame; cada frame se convierte en
un Surface de Pygame para reproducirlos a 60 FPS. Si un sprite/fuente/audio
no existe, no rompemos: devolvemos un placeholder y avisamos por consola.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

import pygame
from PIL import Image, ImageSequence

import config
from src.utils.logger import warn


# ─── Sprites GIF ──────────────────────────────────────────────────────────────
def load_gif_frames(path: Path) -> tuple[list[pygame.Surface], list[int]]:
    """Devuelve (frames, durations_ms). Si falla, retorna ([], [])."""
    if not path.exists():
        warn(f"GIF no encontrado: {path}")
        return ([], [])
    try:
        img = Image.open(path)
    except Exception as e:
        warn(f"No pude abrir {path}: {e}")
        return ([], [])

    frames: list[pygame.Surface] = []
    durations: list[int] = []
    for frame in ImageSequence.Iterator(img):
        rgba = frame.convert("RGBA")
        surf = pygame.image.fromstring(rgba.tobytes(), rgba.size, "RGBA").convert_alpha()
        frames.append(surf)
        durations.append(int(frame.info.get("duration", 80)))
    return frames, durations


def load_pokemon_sprites(species) -> dict:
    """Carga front + back del Pokémon."""
    base = species.sprite_base
    front_filename = f"{base}.gif"
    back_filename = f"{base} (1).gif"
    if config.SWAP_FRONT_BACK:
        front_filename, back_filename = back_filename, front_filename

    front_dirs = [
        config.SPRITES_FRONT_DIR / species.sprite_dir,
        config.SPRITES_DIR / species.sprite_dir,
        config.EXTERNAL_SPRITES_DIR / species.sprite_dir,
    ]
    back_dirs = [
        config.SPRITES_BACK_DIR / species.sprite_dir,
        config.SPRITES_DIR / species.sprite_dir,
        config.EXTERNAL_SPRITES_DIR / species.sprite_dir,
    ]
    front_path = _find_in_dirs(front_dirs, front_filename)
    back_path  = _find_in_dirs(back_dirs, back_filename)

    front_frames, front_dur = load_gif_frames(front_path) if front_path else ([], [])
    back_frames, back_dur   = load_gif_frames(back_path)  if back_path  else ([], [])
    return {
        "front_frames": front_frames, "front_durations": front_dur,
        "back_frames":  back_frames,  "back_durations":  back_dur,
    }


def _find_in_dirs(dirs, filename: str) -> Optional[Path]:
    for d in dirs:
        p = Path(d) / filename
        if p.exists():
            return p
    return None


# ─── Fuentes ──────────────────────────────────────────────────────────────────
_FONT_CACHE: dict[tuple[str, int, bool], pygame.font.Font] = {}

# Press Start 2P es muy ancha; las "alturas equivalentes" típicas son ~70% del
# tamaño real. Aplicamos un ajuste para que `get_font(22)` se vea similar de
# alto a Arial 22 — pero con look pixel.
_PIXEL_SIZE_FACTOR = 0.72


def get_font(size: int, bold: bool = False, family: str = "pixel") -> pygame.font.Font:
    """Devuelve una fuente. Por defecto usa Press Start 2P (pixel art)."""
    key = (family, size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    font = None
    if family in ("pixel", "pokemon"):
        for candidate in (
            "PressStart2P-Regular.ttf",
            "pokemon-classic.ttf",
            "pokemon-gb.ttf",
            "PokemonGB-Regular.ttf",
        ):
            p = config.FONTS_DIR / candidate
            if p.exists():
                try:
                    eff = max(8, int(size * _PIXEL_SIZE_FACTOR))
                    font = pygame.font.Font(str(p), eff)
                    break
                except Exception:
                    pass
    if font is None:
        font = pygame.font.SysFont("consolas,segoe ui,arial", size, bold=bold)
    _FONT_CACHE[key] = font
    return font


# ─── Iconos estáticos pixelados ───────────────────────────────────────────────
_ICONS_DIR = config.SPRITES_DIR / "icons"
_ICON_CACHE: dict[tuple[str, int], pygame.Surface] = {}


def load_pokemon_icon(species, size: int = 96) -> pygame.Surface:
    """Carga el PNG estático pixelado del Pokémon en `assets/sprites/icons/`.

    Si falta, hace fallback al primer frame del GIF de front. Si tampoco hay,
    devuelve un placeholder gris.
    """
    key = (species.sprite_dir, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    surf: pygame.Surface | None = None
    p = _ICONS_DIR / f"{species.sprite_dir}.png"
    if p.exists():
        try:
            raw = pygame.image.load(str(p)).convert_alpha()
            surf = pygame.transform.scale(raw, (size, size))
        except pygame.error:
            surf = None

    if surf is None:
        # Fallback: primer frame del GIF de front
        data = load_pokemon_sprites(species)
        if data["front_frames"]:
            f0 = data["front_frames"][0]
            surf = pygame.transform.smoothscale(f0, (size, size))

    if surf is None:
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((180, 180, 180, 100))

    _ICON_CACHE[key] = surf
    return surf


# ─── Fondos de batalla ────────────────────────────────────────────────────────
_BG_DIR = config.ASSETS_DIR / "ui" / "backgrounds"
_INTRO_DIR = config.ASSETS_DIR / "ui" / "intro" / "pikachu_loop"


def list_battle_backgrounds() -> list[Path]:
    """PNGs disponibles en assets/ui/backgrounds/ (cualquier nombre)."""
    if not _BG_DIR.exists():
        return []
    return sorted(_BG_DIR.glob("*.png"))


def load_random_battle_background(size: tuple[int, int],
                                  rng=None) -> pygame.Surface:
    """Devuelve un fondo aleatorio escalado a `size`. Si no hay PNGs, fallback procedural."""
    import random as _rnd
    rng = rng or _rnd
    bgs = list_battle_backgrounds()
    if not bgs:
        return make_battle_background(size)
    path = rng.choice(bgs)
    try:
        img = pygame.image.load(str(path)).convert()
        return pygame.transform.smoothscale(img, size)
    except pygame.error:
        return make_battle_background(size)


def intro_loop_dir() -> Path:
    """Carpeta con los frames del loop de Pikachu (extract_intro.py)."""
    return _INTRO_DIR


# ─── Imagen de fondo (placeholder generado si faltan los PNGs) ────────────────
def make_battle_background(size: tuple[int, int]) -> pygame.Surface:
    """Si no hay BG, genera uno tipo arena con horizonte y plataformas."""
    w, h = size
    surf = pygame.Surface(size).convert()
    # cielo→tierra gradiente
    for y in range(h):
        t = y / h
        if t < 0.5:
            c = (
                int(168 + (216 - 168) * (t / 0.5)),
                int(216 + (240 - 216) * (t / 0.5)),
                int(232 + (240 - 232) * (t / 0.5)),
            )
        else:
            c = (
                int(216 + (160 - 216) * ((t - 0.5) / 0.5)),
                int(240 + (200 - 240) * ((t - 0.5) / 0.5)),
                int(240 + (160 - 240) * ((t - 0.5) / 0.5)),
            )
        pygame.draw.line(surf, c, (0, y), (w, y))
    # Plataformas
    pygame.draw.ellipse(surf, (148, 200, 120), (w * 0.55, h * 0.42, w * 0.40, h * 0.10))
    pygame.draw.ellipse(surf, (110, 168,  96), (w * 0.55, h * 0.46, w * 0.40, h * 0.04))
    pygame.draw.ellipse(surf, (148, 200, 120), (w * 0.05, h * 0.74, w * 0.40, h * 0.10))
    pygame.draw.ellipse(surf, (110, 168,  96), (w * 0.05, h * 0.78, w * 0.40, h * 0.04))
    return surf
