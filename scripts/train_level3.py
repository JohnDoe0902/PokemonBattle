"""Entrenamiento del agente Nivel 3: optimiza los pesos [w1..w5] de la función de
evaluación con un algoritmo genético, jugando contra el Nivel 2 (Heurístico).

Diseño (ver agente 3.md, bloque B):
- Genoma: 5 pesos en el simplex (no negativos, suman 1).
- Fitness: win-rate + margen de HP + rapidez de victoria contra el Nivel 2.
- CRN: todos los genomas de una generación juegan las MISMAS configuraciones
  (comparación pareada, baja varianza); se re-muestrean cada generación.
- Operadores: torneo + elitismo, cruce BLX-α, mutación gaussiana con σ decreciente,
  reparación al simplex.
- Selección FINAL sobre un set HELD-OUT (configuraciones nunca vistas en
  entrenamiento) → win-rate insesgado.
- Salida: data/level3_weights.json con los pesos ganadores y metadatos.

Todo sembrado desde una semilla maestra → entrenamiento reproducible.

Ejemplos:
    py scripts/train_level3.py
    py scripts/train_level3.py --pop 24 --gens 15 --games 30 --holdout 200
    py scripts/train_level3.py --depth 2 --seed 7 --out data/level3_weights.json

Archivo NUEVO: forma parte del agente Nivel 3.
"""
#AGREGADO Inicio
from __future__ import annotations
import os
import sys
import json
import time
import random
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agents import HeuristicAgent
from src.agents.minimax_agent import MinimaxAgent
from src.agents.evaluation import COMPONENT_NAMES
from src.agents.harness import gen_config, play

# Operadores (constantes; ajústalos en el código si quieres experimentar).
ELITES = 2
TOURN_K = 3
BLX_ALPHA = 0.3
SIGMA0 = 0.25
SIGMA_DECAY = 0.80

N_COMPONENTS = len(COMPONENT_NAMES)


def evaluate_weights(weights, configs, depth, top_k, eps_margin, eps_speed):
    """win-rate y fitness denso de `weights` (Minimax, lado 1) vs Nivel 2 (lado 0)."""
    wins = 0
    margin_sum = 0.0
    speed_sum = 0.0
    for i, cfg in enumerate(configs):
        # Agentes sembrados por índice de config (iguales entre genomas → CRN puro).
        a = HeuristicAgent(random.Random(10_000 + i))
        b = MinimaxAgent(weights=weights, depth=depth, top_k=top_k, rng=random.Random(20_000 + i))
        winner, turns, margin = play(cfg, a, b)
        if winner == 1:
            wins += 1
            speed_sum += 1.0 / turns
        margin_sum += margin
    n = len(configs)
    win_rate = wins / n
    fitness = win_rate + eps_margin * (margin_sum / n) + eps_speed * (speed_sum / n)
    return win_rate, fitness


# ─── Evaluación (con paralelismo opcional por genoma) ───────────────────────────
def _eval_task(task):
    """Worker para ProcessPoolExecutor: desempaqueta y evalúa un genoma.

    Debe ser una función a nivel de módulo (Windows usa 'spawn' y necesita
    poder importarla y picklear sus argumentos).
    """
    weights, configs, depth, top_k, eps_margin, eps_speed = task
    return evaluate_weights(weights, configs, depth, top_k, eps_margin, eps_speed)


def eval_many(weight_list, configs, args, executor):
    """Evalúa varios genomas; en paralelo si hay executor. Conserva el orden de entrada
    → resultados idénticos a la versión en serie (la siembra no depende del orden)."""
    tasks = [(w, configs, args.depth, args.top_k, args.eps_margin, args.eps_speed)
             for w in weight_list]
    if executor is None:
        return [_eval_task(t) for t in tasks]
    return list(executor.map(_eval_task, tasks))


# ─── Operadores genéticos (genoma = 5 pesos en el simplex) ──────────────────────
def repair(g):
    g = [max(0.0, x) for x in g]
    s = sum(g)
    return [x / s for x in g] if s > 0 else [1.0 / N_COMPONENTS] * N_COMPONENTS


def random_genome(rng):
    return repair([rng.random() for _ in range(N_COMPONENTS)])


def crossover(p1, p2, rng):
    child = []
    for x, y in zip(p1, p2):
        lo, hi = min(x, y), max(x, y)
        d = hi - lo
        child.append(rng.uniform(lo - BLX_ALPHA * d, hi + BLX_ALPHA * d))
    return repair(child)


def mutate(g, rng, sigma):
    return repair([x + rng.gauss(0, sigma) for x in g])


def tournament(pop_fit, rng):
    cand = rng.sample(pop_fit, TOURN_K)
    return max(cand, key=lambda pf: pf[1])[0]


# ─── Bucle del GA ───────────────────────────────────────────────────────────────
def main(args):
    t_start = time.time()
    workers = args.workers if args.workers and args.workers > 0 else (os.cpu_count() or 1)
    rng = random.Random(args.seed)            # rng de los operadores del GA

    pop = [random_genome(rng) for _ in range(args.pop)]
    pop[0] = [0.2, 0.2, 0.2, 0.2, 0.2]                   # uniforme (no informado)
    pop[1] = [0.35, 0.30, 0.15, 0.05, 0.15]             # prior hecho a mano
    pop[2] = [1.0, 0.0, 0.0, 0.0, 0.0]                  # solo HP (≈ Nivel 2)

    print(f"=== GA Nivel 3 vs Nivel 2 | pop={args.pop} gens={args.gens} games={args.games} "
          f"depth={args.depth} seed={args.seed} workers={workers} ===\n", flush=True)
    print(f"{'gen':>3} | {'best_fit':>8} {'best_win':>8} | pesos (hp,vivos,tipo,vel,ko)", flush=True)

    # Executor reutilizado en todo el entrenamiento (None → serie).
    executor = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None

    history = []
    candidates = []

    for gen in range(args.gens):
        cfg_rng = random.Random(args.seed + 1000 + gen)
        configs = [gen_config(cfg_rng, args.size) for _ in range(args.games)]

        results = eval_many(pop, configs, args, executor)
        scored = [(pop[i], results[i][1], results[i][0]) for i in range(len(pop))]

        scored.sort(key=lambda s: -s[1])
        best_g, best_fit, best_wr = scored[0]
        history.append({"gen": gen, "best_fit": best_fit, "best_win": best_wr})
        candidates.append(best_g)

        pesos = ", ".join(f"{w:.2f}" for w in best_g)
        print(f"{gen:>3} | {best_fit:>8.3f} {best_wr:>8.1%} | {pesos}", flush=True)

        new = [scored[i][0] for i in range(ELITES)]
        sigma = SIGMA0 * (SIGMA_DECAY ** gen)
        pop_fit = [(g, fit) for g, fit, _ in scored]
        while len(new) < args.pop:
            p1 = tournament(pop_fit, rng)
            p2 = tournament(pop_fit, rng)
            new.append(mutate(crossover(p1, p2, rng), rng, sigma))
        pop = new

    # ─── Selección FINAL sobre held-out ─────────────────────────────────────────
    print("\n-- Selección final sobre set held-out --", flush=True)
    holdout_rng = random.Random(args.seed + 999_999)
    holdout = [gen_config(holdout_rng, args.size) for _ in range(args.holdout)]

    refs = [("uniforme", [0.2] * 5), ("prior", [0.35, 0.30, 0.15, 0.05, 0.15])]
    seen = set()
    ga_cands = []
    for g in candidates:
        key = tuple(round(x, 3) for x in g)
        if key not in seen:
            seen.add(key); ga_cands.append(g)

    cand_named = refs + [(f"GA#{i}", g) for i, g in enumerate(ga_cands)]
    ho_results = eval_many([g for _, g in cand_named], holdout, args, executor)

    best = None
    best_wr = best_fit = -1.0
    best_holdout_fit = -1.0
    for (name, g), (wr, fit) in zip(cand_named, ho_results):
        if name.startswith("GA") and fit > best_holdout_fit:
            best_holdout_fit, best, best_wr, best_fit = fit, g, wr, fit
        pesos = ", ".join(f"{w:.2f}" for w in g)
        print(f"  {name:10s} win={wr:5.1%} fit={fit:.3f}  [{pesos}]", flush=True)

    if best is None:                       # sin candidatos GA (improbable): cae al primero
        best = ga_cands[0]
        best_wr, best_fit = ho_results[len(refs)]

    if executor is not None:
        executor.shutdown()

    out = {
        "weights": [round(w, 5) for w in best],
        "components": list(COMPONENT_NAMES),
        "meta": {
            "holdout_winrate": round(best_wr, 4),
            "holdout_fitness": round(best_fit, 4),
            "population": args.pop, "generations": args.gens, "games_per_eval": args.games,
            "holdout_games": args.holdout, "depth_train": args.depth,
            "top_k": args.top_k, "master_seed": args.seed,
            "trained_against": "Nivel2-Heuristic",
        },
        "history": history,
    }
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\nMejor (held-out): win={best_wr:.1%}  pesos={[round(w, 3) for w in best]}")
    print(f"Guardado en: {out_path}")
    print(f"Tiempo total: {time.time() - t_start:.0f}s")


def parse_args():
    p = argparse.ArgumentParser(description="Entrena los pesos del Nivel 3 con un AG (vs Nivel 2).")
    p.add_argument("--pop", type=int, default=16, help="tamaño de población")
    p.add_argument("--gens", type=int, default=8, help="número de generaciones")
    p.add_argument("--games", type=int, default=20, help="partidas por evaluación de fitness (CRN)")
    p.add_argument("--holdout", type=int, default=80, help="partidas del set held-out final")
    p.add_argument("--depth", type=int, default=2, help="profundidad del minimax en entrenamiento")
    p.add_argument("--top-k", dest="top_k", type=int, default=2, help="poda de cambios (top-K)")
    p.add_argument("--size", type=int, default=4, help="tamaño de equipo (3 o 4)")
    p.add_argument("--seed", type=int, default=42, help="semilla maestra")
    p.add_argument("--eps-margin", dest="eps_margin", type=float, default=0.10, help="peso del margen en el fitness")
    p.add_argument("--eps-speed", dest="eps_speed", type=float, default=0.10, help="peso de la rapidez en el fitness")
    p.add_argument("--workers", type=int, default=0, help="procesos en paralelo (0=auto=nº de núcleos; 1=serie)")
    p.add_argument("--out", type=str, default="data/level3_weights.json", help="ruta de salida del JSON")
    return p.parse_args()


if __name__ == "__main__":
    main(parse_args())
#AGREGADO Fin
