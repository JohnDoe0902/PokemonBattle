"""Benchmark de agentes: enfrenta dos agentes N partidas y reporta win-rate,
margen de HP y duración, sobre configuraciones reproducibles (CRN).

Agentes disponibles: random (N1), heuristic (N2), minimax (N3).
Para el minimax se eligen los pesos con --weights:
  - un preset:   uniforme | prior | hp_only | macro | equal
  - 'trained':   carga data/level3_weights.json
  - una lista:   "0.4,0.3,0.1,0.1,0.1"
  - una ruta:    a un JSON con clave "weights"

Ejemplos:
    # Nivel 3 (pesos entrenados) vs Nivel 2, 300 partidas
    py scripts/evaluate.py --p0 heuristic --p1 minimax --weights trained --games 300

    # Barrido estándar de pesos del minimax vs Nivel 2
    py scripts/evaluate.py --sweep --games 300 --depth 2

    # Nivel 3 vs Nivel 1
    py scripts/evaluate.py --p0 random --p1 minimax --weights trained --games 300

    # Barrido de profundidad (pesos entrenados) vs Nivel 2
    py scripts/evaluate.py --depth-sweep 1,2,3 --weights trained --games 200

Archivo NUEVO: forma parte del agente Nivel 3.
"""
#AGREGADO Inicio
from __future__ import annotations
import sys
import json
import time
import random
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config
from src.agents import RandomAgent, HeuristicAgent
from src.agents.minimax_agent import MinimaxAgent
from src.agents.evaluation import COMPONENT_NAMES
from src.agents.harness import gen_config, play

PRESETS = {
    "uniforme": [0.2, 0.2, 0.2, 0.2, 0.2],
    "equal":    [0.2, 0.2, 0.2, 0.2, 0.2],
    "prior":    [0.35, 0.30, 0.15, 0.05, 0.15],
    "hp_only":  [1.0, 0.0, 0.0, 0.0, 0.0],
    "macro":    [0.5, 0.5, 0.0, 0.0, 0.0],
}


def resolve_weights(spec):
    if spec is None:
        return list(PRESETS["uniforme"])
    if spec in PRESETS:
        return list(PRESETS[spec])
    if spec == "trained":
        path = config.DATA_DIR / "level3_weights.json"
        return json.load(open(path, encoding="utf-8"))["weights"]
    if "," in spec:
        return [float(x) for x in spec.split(",")]
    # tratar como ruta a un JSON con clave "weights"
    return json.load(open(spec, encoding="utf-8"))["weights"]


def make_agent(kind, side_seed, weights, depth, top_k):
    rng = random.Random(side_seed)
    if kind == "random":
        return RandomAgent(rng)
    if kind == "heuristic":
        return HeuristicAgent(rng)
    if kind == "minimax":
        return MinimaxAgent(weights=weights, depth=depth, top_k=top_k, rng=rng)
    raise ValueError(f"Agente desconocido: {kind}")


def run_match(label, p0, p1, weights, depth, top_k, configs):
    w0 = w1 = draws = 0
    margin = 0.0
    durs = []
    t0 = time.time()
    for i, cfg in enumerate(configs):
        a0 = make_agent(p0, 10_000 + i, weights, depth, top_k)
        a1 = make_agent(p1, 20_000 + i, weights, depth, top_k)
        winner, turns, m = play(cfg, a0, a1)
        if winner == 0: w0 += 1
        elif winner == 1: w1 += 1
        else: draws += 1
        margin += m
        durs.append(turns)
    n = len(configs)
    r1 = w1 / n
    se = (r1 * (1 - r1) / n) ** 0.5
    print(f"  {label:34s} | lado0={w0/n:5.1%}  lado1={r1:5.1%} (±{se:.1%})  "
          f"draws={draws:2d}  margen(L1)={margin/n:+.3f}  turnos={sum(durs)/len(durs):.1f}  [{time.time()-t0:.0f}s]")
    return r1


def main(args):
    cfg_rng = random.Random(args.seed)
    configs = [gen_config(cfg_rng, args.size) for _ in range(args.games)]
    depth, top_k = args.depth, args.top_k

    print(f"=== Benchmark: {args.games} partidas {args.size}v{args.size}, CRN, seed={args.seed} ===")
    print(f"    (lado0 = p0,  lado1 = p1;  win-rate reportado del lado1)\n")

    if args.sweep:
        # Minimax(lado1) con varios pesos vs Heuristic(lado0).
        print(f"-- Barrido de PESOS: minimax(depth={depth}) vs heuristic --")
        for name in ("uniforme", "prior", "hp_only", "macro"):
            run_match(f"minimax[{name}]", "heuristic", "minimax", PRESETS[name], depth, top_k, configs)
        try:
            tw = resolve_weights("trained")
            run_match("minimax[trained]", "heuristic", "minimax", tw, depth, top_k, configs)
        except FileNotFoundError:
            print("  (sin data/level3_weights.json: corre train_level3.py para incluir 'trained')")
        return

    if args.ablation:
        # Parte de un vector con los 5 componentes activos y anula cada uno.
        base = resolve_weights("equal" if args.weights == "trained" else args.weights)
        print(f"-- ABLACIÓN: minimax(depth={depth}) vs heuristic, base={['%.2f' % w for w in base]} --")
        base_wr = run_match("base (todos)", "heuristic", "minimax", base, depth, top_k, configs)
        for i, name in enumerate(COMPONENT_NAMES):
            w = list(base); w[i] = 0.0
            s = sum(w)
            w = [x / s for x in w] if s > 0 else w
            wr = run_match(f"sin {name}", "heuristic", "minimax", w, depth, top_k, configs)
            print(f"        -> contribución de '{name}': {base_wr - wr:+.1%}")
        return

    if args.depth_sweep:
        depths = [int(d) for d in args.depth_sweep.split(",")]
        w = resolve_weights(args.weights)
        print(f"-- Barrido de PROFUNDIDAD: minimax[{args.weights}] vs heuristic --")
        for d in depths:
            run_match(f"minimax depth={d}", "heuristic", "minimax", w, d, top_k, configs)
        return

    # Enfrentamiento simple p0 vs p1.
    w = resolve_weights(args.weights)
    label = f"{args.p0} vs {args.p1}"
    if "minimax" in (args.p0, args.p1):
        label += f" (w={args.weights}, depth={depth})"
    run_match(label, args.p0, args.p1, w, depth, top_k, configs)


def parse_args():
    p = argparse.ArgumentParser(description="Benchmark de agentes (N1/N2/N3) con CRN.")
    p.add_argument("--p0", default="heuristic", choices=["random", "heuristic", "minimax"], help="agente del lado 0")
    p.add_argument("--p1", default="minimax", choices=["random", "heuristic", "minimax"], help="agente del lado 1")
    p.add_argument("--weights", default="trained", help="pesos del minimax: preset | trained | 'a,b,c,d,e' | ruta.json")
    p.add_argument("--depth", type=int, default=2, help="profundidad del minimax")
    p.add_argument("--top-k", dest="top_k", type=int, default=2, help="poda de cambios (top-K)")
    p.add_argument("--games", type=int, default=200, help="número de partidas")
    p.add_argument("--size", type=int, default=4, help="tamaño de equipo (3 o 4)")
    p.add_argument("--seed", type=int, default=555_555, help="semilla de las configuraciones (held-out)")
    p.add_argument("--sweep", action="store_true", help="barrido de pesos del minimax vs heuristic")
    p.add_argument("--ablation", action="store_true", help="ablación: anula cada componente y mide su contribución")
    p.add_argument("--depth-sweep", dest="depth_sweep", default=None, help="barrido de profundidad, p.ej. '1,2,3'")
    return p.parse_args()


if __name__ == "__main__":
    main(parse_args())
#AGREGADO Fin
