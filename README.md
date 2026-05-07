# Pokefisi · Simulación Estratégica de Combates tipo Pokémon

Proyecto del curso de Inteligencia Artificial (UNMSM). Implementa un sistema
de combate tipo Pokémon para evaluar agentes — desde un baseline aleatorio
hasta una heurística de diferencia de HP — bajo la fórmula de daño del PDF
del curso.

> **Estado: Entrega Parcial (Semana 5)** — Niveles 1 y 2 implementados,
> motor completo, GUI estilo Pokémon Gen 3, smoke test reproducible.

---

## 1. Cómo correrlo

```bash
pip install -r requirements.txt
python main.py
```

- Abre la pantalla de título; pulsa cualquier tecla.
- En **Configuración** eliges tamaño de equipo (3 o 4), si tu equipo y el
  rival se eligen manual o al azar, lo mismo con los movimientos, y la IA
  rival (Nivel 1 Random / Nivel 2 Heurística).
- Luego, según tus elecciones, te lleva a las pantallas de selección.
- Combate clásico Pokémon: menú **Lucha / Pokémon / Huir**, barras de HP
  drenando suave, sprites animados desde tus `.gif`, indicador de tipos.

Para correr el smoke test sin GUI (rápido, ideal para experimentos):

```bash
python main.py --headless
```

Imprime win-rate de Heurística vs Random sobre 50 partidas.

### Importar sprites

Tus sprites originales están en `C:/POKEFILICOS/sprites/<Pokemon>/`. El
importador los copia a `assets/sprites/{front,back}/`:

```bash
python scripts/import_sprites.py            # convención: name.gif=front, name (1).gif=back
python scripts/import_sprites.py --swap     # si en tus carpetas está al revés
```

Si en algún momento detectas que el sprite del jugador y el del rival están
intercambiados, abre `config.py` y pon `SWAP_FRONT_BACK = True`.

### Audio

El proyecto incluye:

```
assets/audio/music/   menu.ogg, battle_wild.ogg, victory.ogg          (de Pokémon Showdown)
assets/audio/cries/   31 .ogg                                          (de Pokémon Showdown)
assets/audio/sfx/     hit.wav, hit_super.wav, hit_weak.wav, faint.wav, select.wav, low_hp.wav
                                                                       (sintetizados por scripts/generate_sfx.py)
```

Los SFX se generan con `python scripts/generate_sfx.py` (estilo retro 8-bit
con numpy). Si quieres regenerarlos o cambiar las frecuencias, edita ese
script. Si falta cualquier archivo, el juego corre en silencio sin crashear.

### Fondos de batalla y video de intro

```
assets/ui/backgrounds/  bg-beach.png, bg-beachshore.png, bg-city.png,
                        bg-dampcave.png, bg-deepsea.png, bg-desert.png,
                        bg-earthycave.png, bg-forest.png
assets/ui/intro/PikachuLoop.mp4
assets/ui/intro/pikachu_loop/  frame_0000.png … (extraídos)
```

- En cada batalla se elige aleatoriamente uno de los 8 fondos.
- Las pantallas pre-batalla (Título, Configuración, Selección de equipo,
  Selección de movs) usan el loop de Pikachu corriendo como fondo (sin audio).
- Los frames del loop se pre-extraen una vez con:
  ```bash
  python scripts/extract_intro.py            # 2 segundos por defecto
  python scripts/extract_intro.py --seconds 3 --scale 0.75
  ```
  Después, la UI sólo necesita Pygame en runtime — `imageio` es dep de
  desarrollo (sólo para el script).

---

## 2. Estructura del proyecto

```
POKEFILICOS/
├── main.py                Entry point (GUI o --headless)
├── config.py              Constantes (K, FPS, paleta, rutas)
├── requirements.txt
│
├── data/
│   ├── pokemon.json       36 Pokémon · tipos · stats base
│   ├── moves.json         144 movs (18 tipos × 8) corregidos
│   ├── type_chart.json    Efectividad 18×18 (Gen 6+)
│   └── learnsets.json     Pool real de movs por especie
│
├── assets/                Sprites (front/back), fuentes y audio
│
├── src/
│   ├── core/              Motor PURO (sin Pygame). Reusable en headless.
│   │   ├── types.py       18 tipos + tabla de efectividad
│   │   ├── move.py        Move + carga de moves.json
│   │   ├── pokemon.py     Especies, instancias de combate, random_moveset
│   │   ├── action.py      Action(attack | switch)
│   │   ├── damage.py      Fórmula del PDF + STAB + efectividad + RNG
│   │   └── battle.py      BattleState, step(), clone(), legal_actions()
│   │
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── random_agent.py    NIVEL 1
│   │   ├── heuristic_agent.py NIVEL 2
│   │   └── human_agent.py
│   │
│   ├── ui/                GUI Pygame
│   │   ├── game.py        Loop principal
│   │   ├── audio.py       mixer wrapper resiliente
│   │   ├── assets_loader  GIF → frames + fuentes
│   │   ├── widgets/       SpriteAnimator, HPBar, TextBox, Menu
│   │   └── scenes/        Menú, Config, TeamSelect, MoveSelect, Battle
│   │
│   └── utils/             logger, rng con semilla
│
└── scripts/
    ├── import_sprites.py
    └── headless_smoke.py
```

Tres convenciones que vale la pena conocer:

1. **`core/` no importa Pygame.** Eso permite simular miles de partidas en
   `--headless` para los experimentos del entregable final.
2. **Agentes con interfaz uniforme.** Para los Niveles 3+, GA y Minimax solo
   se añaden archivos en `src/agents/` que implementen `Agent.choose_action`.
3. **Datos en JSON.** Para rebalancear o cambiar listas no se toca código.

---

## 3. Modelado del combate

### 3.1 Atributos del Pokémon

Tomamos las **stats base canónicas** de Pokémon Showdown / Bulbapedia (Gen 8/9)
y las escalamos a un nivel virtual (`config.LEVEL = 50`) con las fórmulas
estándar de la serie:

```
HP_max = (2 · base_hp + 110) · LEVEL/100 + 10
Stat   = (2 · base_stat) · LEVEL/100 + 5     (Atk, Def, AtkE, DefE, Spd)
```

Cada Pokémon equipa **4 movs** sacados de su `learnset` real. La selección
es manual (UI) o aleatoria (`Pokemon.random_moveset`).

### 3.2 Fórmula de daño

Implementamos la fórmula del PDF en [`src/core/damage.py`](src/core/damage.py):

```
base = (Atk / Def_op) · BasePower − Speed_op · K              ← PDF
final = max(1, base · STAB · type_eff · crit · rand)
```

- `K = 0.35` (`config.DAMAGE_K`).
- **STAB** = 1.5 si el tipo del mov coincide con un tipo del atacante.
- **type_eff**: producto sobre los tipos del defensor según `type_chart.json`
  (Gen 6+, incluye Hada).
- **crit** = 1.5 con probabilidad 1/16.
- **rand** ∈ [0.85, 1.00] uniforme (estilo Showdown).
- **accuracy**: tirada 1–100 vs `move.accuracy`. Movs con `always_hits`
  ignoran la tirada.

`damage.py` devuelve un dict con `damage`, `effectiveness`, `crit`, `missed`
y `no_effect`, que es lo que la UI usa para mostrar “¡Súper eficaz!”, etc.

### 3.3 Reglas del combate

`BattleState` ([`src/core/battle.py`](src/core/battle.py)):

- 3v3 o 4v4, pero **siempre 1v1 simultáneo** en pista (los demás están en
  banca).
- Cada turno los dos lados eligen una `Action` (atacar / cambiar). Los
  cambios resuelven antes que los ataques.
- Entre dos ataques, primero el de mayor `priority` (`Sombra Vil`,
  `Canto Helado`, `Golpe Bajo`); con empate, primero el de mayor `Speed`;
  con segundo empate, desempate aleatorio.
- Si un Pokémon cae a 0 HP, el lado afectado entra en `pending_switch` y
  debe enviar un reemplazo antes del próximo turno.
- La batalla termina cuando un equipo no tiene Pokémon vivos.
- `BattleState.clone()` crea un snapshot profundo para Minimax (Nivel 3+).

---

## 4. Datos del juego

### 4.1 Movimientos (144 = 18 tipos × 8)

Los datos parten del listado proporcionado, **con las siguientes
correcciones aplicadas** durante la validación:

| # | Tipo | Movimiento | Problema | Corrección |
|---|---|---|---|---|
| 1 | Eléctrico | Voz Cautivadora | Es de tipo Hada (ya está ahí) | Sustituido por **Carga Parabólica** (Especial 65/100/20) |
| 2 | Normal | Cuerpo Pesado | Es de tipo Acero (ya está ahí) | Sustituido por **Golpe Cuerpo** (Físico 85/100/15) |
| 3 | Acero | Alarido de Metal | Es un mov de **estado** (0 poder) | Sustituido por **Eco Metálico** (Especial 65/85/10) |
| 4 | Eléctrico | Onda Voltio | Poder real es 70, no 60 | Pot 60 → **70** |
| 5 | Planta | Hierba Lazo | Categoría real es **Especial**, no Físico | Físico → **Especial** |

Algunos movs llevan flags adicionales (`drain`, `recoil`, `multi_hit`,
`priority`, `recharge`, etc.) que ya están parseadas pero solo unas pocas
están aplicadas en el motor (priority sí; el resto se irá sumando si
afecta los experimentos).

### 4.2 Pokémon (36)

Stats base de Pokémon Showdown. Cada uno trae su `sprite_dir` y
`sprite_base` para mapear las carpetas tal como están en disco
(con el caso especial de `Kommo-o → kommoo`).

### 4.3 Learnsets (movsets canónicos)

`data/learnsets.json` lista, por especie, **solo movs que ese Pokémon puede
aprender en las series principales** (level-up + MTs + tutores en Gen 8/9).
Los IDs deben coincidir con `data/moves.json`. Validación automática:

```bash
python -c "import json; m=json.load(open('data/moves.json',encoding='utf-8')); l=json.load(open('data/learnsets.json',encoding='utf-8')); ids={mv['id'] for mv in m['moves']}; bad={k:[x for x in v if x not in ids] for k,v in l['learnsets'].items() if any(x not in ids for x in v)}; print('roto' if bad else 'OK', bad)"
```

Promedios actuales: 19–32 movs por Pokémon (avg ≈ 23). El motor pide
mínimo 8.

---

## 5. Niveles de inteligencia

### Nivel 1 — RandomAgent (`src/agents/random_agent.py`)

Política trivial: `random.choice(state.legal_actions(side))`. **Baseline.**
No distingue entre atacar y cambiar; todo equiprobable. Su utilidad es
servir de piso contra el cual medir cualquier otra heurística.

### Nivel 2 — HeuristicAgent (`src/agents/heuristic_agent.py`)

Cumple lo que pide el PDF para Nivel 2: **diferencia de HP entre
jugadores**. Política:

1. Para cada acción legal, **simula 1 turno** con `state.clone()`
   asumiendo que el rival usará su movimiento de **mayor daño esperado**
   (modelo simple del oponente).
2. Sobre el estado resultante calcula la heurística:

```
H1(state, side) = HP_propio_normalizado − HP_rival_normalizado    ∈ [-1, 1]

donde
  HP_propio_normalizado = Σ HP_actual_propio / Σ HP_máx_propio
  HP_rival_normalizado  = Σ HP_actual_rival / Σ HP_máx_rival
```

3. Elige la acción con H1 máxima; empates se rompen al azar.

El **lookahead de 1 ply usa daño esperado** (sin RNG): se promedia el
factor random ([0.85, 1.0] → 0.925) y se multiplica por la accuracy del
mov, pero los HP, tipos y stats sí se simulan exactos. Esto hace al agente
**determinista dado el mismo estado**, lo cual es deseable para los
experimentos.

> **Por qué normalizar**: el PDF marca explícitamente “Todos los factores
> deben estar normalizados” en el Nivel 3 — adelantamos la normalización
> aquí para que H1 viva en `[-1, 1]` y sea directamente combinable con las
> componentes del Nivel 3 sin reescribir nada.

### Heurísticas adicionales (preparadas para Nivel 3, no activas todavía)

`src/core/types.py` ya expone `type_effectiveness` para que el Nivel 3
use componentes adicionales:

- **H2 — Pokémon vivos**: `(viv_propios − viv_rivales) / N`
- **H3 — Velocidad relativa**: `tanh((Spd_propia − Spd_rival) / Spd_rival)`
- **H4 — Ventaja de tipo del activo**: efectividad media de mis movs vs el
  activo rival, recortada a `[0, 1]`.
- **H5 — Estado del combate**: bonus si ya cayó algún rival (`viv_rival/N`).

La heurística avanzada del Nivel 3 será una combinación lineal:

```
H_avanzada = w₁·H1 + w₂·H2 + w₃·H3 + w₄·H4 + w₅·H5
```

Con `w₁..w₅` primero ajustados manualmente, luego optimizados con un
algoritmo genético (Nivel 4 de la entrega final). El esqueleto y el slot
del agente están listos.

### Nivel 3+ y Minimax (entrega final, NO en este entregable)

`BattleState.clone()` ya está implementado y la interfaz `Agent` permite
implementar Minimax sin tocar nada del motor. Plan:

- `MinimaxAgent(depth=k)` con poda α-β.
- Función de evaluación `H_avanzada` (5 componentes normalizadas).
- Optimización de pesos con GA: cada individuo es un vector `(w₁..w₅)`,
  fitness = win-rate vs Heurística-HP en N partidas.

---

## 6. Resultados preliminares

Smoke test reproducible (seed = 42, 50 partidas, 4v4, movs aleatorios):

| Agente A | Agente B | Win A | Win B | Empate | Turnos avg |
|---|---|---:|---:|---:|---:|
| Random | Heuristic-HP | **12 %** | **88 %** | 0 | 11.7 |

La heurística básica supera con holgura al baseline aleatorio, validando
que H1 captura correctamente la dirección de “gana quien tenga más HP”.
Los experimentos completos (vs profundidad de Minimax, vs pesos
optimizados con GA) van en la entrega final.

---

## 7. Controles de la interfaz

| Acción | Teclado | Mouse |
|---|---|---|
| Mover cursor | ↑ ↓ ← → / WASD | Mover el ratón |
| Confirmar | Enter / Espacio / Z | Click izquierdo |
| Cancelar | Esc / Backspace / X | — |
| Saltar texto | Enter / Espacio / Z | Click |
| Confirmar selección de equipo / movs | Tab | Click en “Confirmar” |

---

## 8. Próximos pasos (entrega final)

- [ ] `MinimaxAgent` con poda α-β y profundidad configurable.
- [ ] `EvolutionaryOptimizer`: GA sobre los pesos de la heurística avanzada.
- [ ] Suite de experimentos:
  - [ ] Random vs Heur vs Heur-Avanzada vs Heur-Optimizada.
  - [ ] Profundidad 1/3/5 de Minimax.
  - [ ] Win-rate, duración de partidas, varianza.
- [ ] Artículo científico (formato del curso).

---

## 9. Créditos

- Sprites: Pokémon (©Nintendo / Game Freak) — uso académico no comercial.
- Fórmula de daño: adaptada de la consigna del curso (PDF del profesor
  Marco Sobrevilla, UNMSM 2026).
- Tabla de tipos: Gen 6+ (con Hada), normalizada de Bulbapedia.

---

## 10. Apéndice: glosario de archivos

| Archivo | Qué tocar para… |
|---|---|
| `config.py` | cambiar K, FPS, paleta, ruta de sprites, semilla RNG |
| `data/pokemon.json` | añadir/quitar Pokémon, ajustar stats |
| `data/moves.json` | rebalancear movs, añadir flags |
| `data/learnsets.json` | corregir movsets canónicos |
| `data/type_chart.json` | (no debería tocarse — es la tabla oficial) |
| `src/core/damage.py` | tunear la fórmula (STAB, crit, random) |
| `src/agents/heuristic_agent.py` | cambiar la heurística H1 |
| `src/ui/scenes/battle_scene.py` | tocar el render del combate |
