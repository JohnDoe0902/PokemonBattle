"""Pre-extrae frames de PikachuLoop.mp4 a PNGs.

Como Pikachu corre en bucle, basta con extraer un ciclo corto: por defecto
2 s (~48 frames a 24 fps). Después la UI los reproduce en loop infinito y
no depende de imageio en runtime.

Uso:
    python scripts/extract_intro.py            # default: 2 segundos
    python scripts/extract_intro.py --seconds 3
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import imageio.v3 as iio
from PIL import Image

import config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=2.0,
                        help="Cuántos segundos de video extraer (default 2).")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Reducir resolución por este factor (1.0 = original).")
    args = parser.parse_args()

    src = config.ASSETS_DIR / "ui" / "intro" / "PikachuLoop.mp4"
    if not src.exists():
        print(f"[ERROR] No existe {src}")
        return 1

    out_dir = src.parent / "pikachu_loop"
    out_dir.mkdir(parents=True, exist_ok=True)

    for old in out_dir.glob("frame_*.png"):
        old.unlink()

    try:
        meta = iio.immeta(str(src))
        fps = meta.get("fps") or 24.0
    except Exception:
        fps = 24.0

    max_frames = int(fps * args.seconds)

    n = 0
    for frame in iio.imiter(str(src)):
        if n >= max_frames:
            break
        if frame.ndim == 2:
            mode = "L"
        elif frame.shape[2] == 4:
            mode = "RGBA"
        else:
            mode = "RGB"
        img = Image.fromarray(frame, mode=mode)
        if args.scale != 1.0:
            w, h = img.size
            img = img.resize((int(w * args.scale), int(h * args.scale)), Image.LANCZOS)
        img.save(out_dir / f"frame_{n:04d}.png", optimize=True)
        n += 1

    (out_dir / "info.txt").write_text(f"fps={fps}\nframes={n}\n", encoding="utf-8")
    total_kb = sum(p.stat().st_size for p in out_dir.glob("*.png")) / 1024
    print(f"Extraidos {n} frames a {out_dir} (fps={fps}, total ~ {total_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
