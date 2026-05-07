"""Logger sencillo. Imprime con prefijo y soporta silenciar globalmente."""
import sys

VERBOSE = True


def log(*parts, end: str = "\n") -> None:
    if not VERBOSE:
        return
    print(*parts, end=end, file=sys.stdout, flush=True)


def warn(*parts) -> None:
    print("[WARN]", *parts, file=sys.stderr, flush=True)
