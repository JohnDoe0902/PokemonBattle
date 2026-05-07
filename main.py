"""Entrypoint del juego.

Uso:
    python main.py             # lanza la GUI
    python main.py --headless  # corre simulaciones de consola (smoke test)
"""
import sys


def main() -> int:
    if "--headless" in sys.argv:
        from scripts.headless_smoke import run as smoke
        smoke()
        return 0
    from src.ui.game import run
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
