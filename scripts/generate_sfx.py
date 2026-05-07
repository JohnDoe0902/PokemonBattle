"""Genera SFX cortos (hit, faint, select, low_hp) por síntesis.

Suenan retro a propósito (ondas cuadradas + ruido) — estilo Game Boy.
Se invocan con: python scripts/generate_sfx.py
"""
from __future__ import annotations
import wave
import struct
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config

SR = 22050  # samplerate (suficiente para SFX cortos, archivos pequeños)


def _save(path: Path, samples: np.ndarray) -> None:
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def _envelope(n: int, attack: float = 0.01, decay: float = 0.2) -> np.ndarray:
    """Envolvente AD lineal (en segundos)."""
    a = int(SR * attack)
    d = int(SR * decay)
    env = np.ones(n)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if d > 0:
        env[-d:] = np.linspace(1, 0, d)
    return env


def square(freq: float, dur: float, duty: float = 0.5) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    phase = (t * freq) % 1.0
    return np.where(phase < duty, 1.0, -1.0)


def noise(dur: float) -> np.ndarray:
    n = int(SR * dur)
    return np.random.uniform(-1, 1, n)


def hit_normal() -> np.ndarray:
    n = int(SR * 0.18)
    s = noise(0.18) * 0.6
    s += square(220, 0.18) * 0.3
    return s * _envelope(n, 0.005, 0.16)


def hit_super() -> np.ndarray:
    n = int(SR * 0.32)
    # combo ruido grave + sweep
    s1 = noise(0.32) * 0.8
    t = np.arange(n) / SR
    sweep = np.sin(2 * np.pi * (220 + 600 * t / 0.32) * t) * 0.4
    s = s1 + sweep
    return s * _envelope(n, 0.005, 0.30)


def hit_weak() -> np.ndarray:
    n = int(SR * 0.12)
    s = noise(0.12) * 0.25
    s += square(440, 0.12, duty=0.25) * 0.15
    return s * _envelope(n, 0.005, 0.10)


def faint() -> np.ndarray:
    # Glissando descendente
    dur = 0.9
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = 660 - 600 * (t / dur) ** 1.4   # baja de 660 a 60
    phase = 2 * np.pi * np.cumsum(freq) / SR
    s = np.sign(np.sin(phase)) * 0.5  # square
    return s * _envelope(n, 0.01, 0.5)


def select() -> np.ndarray:
    n = int(SR * 0.06)
    s = square(880, 0.06, duty=0.5) * 0.5
    return s * _envelope(n, 0.003, 0.04)


def low_hp_beep() -> np.ndarray:
    # Bip-bip-bip clásico de HP bajo
    beep = square(1100, 0.08, duty=0.5) * 0.45
    silence = np.zeros(int(SR * 0.08))
    one = np.concatenate([beep * _envelope(len(beep), 0.002, 0.07), silence])
    return np.tile(one, 3)


def main() -> None:
    out = config.AUDIO_SFX_DIR
    print(f"Generando SFX en {out}")
    _save(out / "hit.wav",        hit_normal())
    _save(out / "hit_super.wav",  hit_super())
    _save(out / "hit_weak.wav",   hit_weak())
    _save(out / "faint.wav",      faint())
    _save(out / "select.wav",     select())
    _save(out / "low_hp.wav",     low_hp_beep())
    print("Listo.")


if __name__ == "__main__":
    main()
