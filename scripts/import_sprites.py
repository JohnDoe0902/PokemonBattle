"""Copia los .gif desde C:/POKEFILICOS/sprites/<Pokemon>/ a assets/sprites/{front,back}/.

Convención por defecto:
    <name>.gif       → front (rival)
    <name> (1).gif   → back  (jugador)

Si en tus carpetas el orden está al revés, pasa --swap o pon SWAP_FRONT_BACK=True
en config.py — el juego también respeta ese flag al cargar.
"""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path

# Permitir imports relativos al root del repo
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--swap", action="store_true",
                        help="Invierte qué archivo es front y cuál back.")
    parser.add_argument("--source", default=str(config.EXTERNAL_SPRITES_DIR),
                        help="Carpeta origen con subcarpetas por Pokémon.")
    args = parser.parse_args()

    src_root = Path(args.source)
    if not src_root.exists():
        print(f"[ERROR] Carpeta origen no existe: {src_root}")
        return 1

    with open(config.DATA_DIR / "pokemon.json", "r", encoding="utf-8") as f:
        species = json.load(f)["pokemon"]

    front_dir = config.SPRITES_FRONT_DIR
    back_dir = config.SPRITES_BACK_DIR
    front_dir.mkdir(parents=True, exist_ok=True)
    back_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    missing = []
    for sp in species:
        sub = src_root / sp["sprite_dir"]
        if not sub.exists():
            missing.append(sp["sprite_dir"])
            continue
        base = sp["sprite_base"]
        front_src = sub / f"{base}.gif"
        back_src = sub / f"{base} (1).gif"
        if args.swap:
            front_src, back_src = back_src, front_src

        if front_src.exists():
            target = front_dir / sp["sprite_dir"]
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(front_src, target / f"{base}.gif")
            copied += 1
        if back_src.exists():
            target = back_dir / sp["sprite_dir"]
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(back_src, target / f"{base} (1).gif")
            copied += 1

    print(f"Listo. Copiados {copied} archivos. Faltantes: {len(missing)}")
    if missing:
        print("Carpetas no encontradas:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
