# POKE-FISI

> Simulación estratégica de combates tipo Pokémon con agentes de IA.
> Proyecto del curso de **Inteligencia Artificial — UNMSM**, primer entregable.

Un sistema completo de batallas Pokémon por turnos donde se enfrentan
distintos niveles de inteligencia artificial, desde un baseline aleatorio
hasta heurísticas que evalúan el estado del combate. Pensado para que un
humano pueda jugar contra la máquina o para correr experimentos masivos
máquina-vs-máquina sin abrir la GUI.

---

## Tabla de contenidos

1. [Estado del entregable](#-estado-del-entregable)
2. [Tecnologías](#-tecnologías)
3. [Cómo ejecutarlo](#-cómo-ejecutarlo)
4. [Características](#-características)
5. [Agentes implementados](#-agentes-implementados)
6. [Modelado del combate](#-modelado-del-combate)
7. [Datos del juego](#-datos-del-juego)
8. [Resultados preliminares](#-resultados-preliminares)
9. [Estructura del repositorio](#-estructura-del-repositorio)
10. [Controles](#-controles)
11. [Próximos pasos](#-próximos-pasos)
12. [Créditos](#-créditos)

---

## Estado del entregable

Este repo cubre la **Entrega Parcial (Semana 5)** del curso. Lo que pide
el enunciado y lo que está hecho:

| Requisito | Estado |
|---|:---:|
| Sistema funcional de combate (3v3 o 4v4) | Listo |
| 30+ Pokémon con HP / Atk / Def / Vel | 36 Pokémon |
| ≥8 movimientos por Pokémon, atributos relevantes | 144 movs / 18 tipos |
| Selección aleatoria de 4 movimientos | Listo |
| Posibilidad de cambiar Pokémon durante la batalla | Listo |
| Fórmula de daño del PDF | Listo |
| **Nivel 1 — Aleatorio** | Listo |
| **Nivel 2 — Heurística básica (HP)** | Listo |
| Interfaz gráfica | Listo (estilo Pokémon Gen 3) |
| Resultados preliminares | Smoke test reproducible |

Lo que queda para la **Entrega Final (Semana 7)**: Nivel 3 (heurística
avanzada), Minimax con poda α-β, optimización con algoritmo genético y
artículo científico. La estructura del repo ya está preparada para
añadirlos como módulos nuevos sin reescribir lo existente.

---

## Tecnologías

| Capa | Herramienta |
|---|---|
| Lenguaje principal | **Python 3.10+** |
| Renderizado / audio | **Pygame 2.5+** |
| Decodificación de GIFs animados | **Pillow** |
| Generación de SFX por síntesis | **NumPy** |
| Pre-extracción de frames del intro de Pikachu | **imageio** + **imageio-ffmpeg** *(solo desarrollo)* |
| Datos del juego | JSON editable (Pokémon, movimientos, learnsets, tabla de tipos) |
| Tipografía | **Press Start 2P** (Google Fonts, OFL) |

Toda la lógica de combate y de los agentes está en Python puro: el módulo
`src/core/` no importa Pygame, así que se puede simular sin GUI para los
experimentos.

---

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
python main.py
```

Lo que verás:
- **Pantalla de título** con animación de Pikachu corriendo de fondo.
- **Configuración del combate** — tamaño del equipo (3 v 3 o 4 v 4),
  selección manual o aleatoria de equipos y movs, e inteligencia del rival
  (Nivel 1 Random o Nivel 2 Heurística).
- **Selección de equipo** en grilla 6×6 con tarjeta de stats.
- **Selección de movimientos** filtrada por el learnset real de cada
  Pokémon, con sprite animado y tipos.
- **Combate** estilo Pokémon Gen 3, con sprites GIF animados, fondo
  aleatorio (8 escenarios distintos), música y SFX.

### Modo headless (para experimentos)

```bash
python main.py --headless
```

Corre 50 batallas Random vs Heurística con semilla fija e imprime el
win-rate. Ideal para los reportes.

---

## Características

### Pre-batalla configurable

Antes de cada combate puedes elegir:
- **Tamaño del equipo:** 3 v 3 o 4 v 4 (siempre 1 v 1 simultáneo en pista)
- **Equipo del jugador:** elegirlo manualmente entre los 36 disponibles, o aleatorio
- **Equipo del rival:** igual
- **Movimientos del jugador y del rival:** manuales (de su learnset) o aleatorios
- **Inteligencia del rival:** Nivel 1 (Random) o Nivel 2 (Heurística HP)

Toda la configuración persiste si retrocedes con **Esc**: si elegiste un
equipo y vuelves atrás, no se pierde — solo lo invalida si lo editas.

### Interfaz estilo Pokémon Gen 3

- Sprites animados (front y back) desde GIFs reales.
- 8 fondos de combate aleatorios (playa, ciudad, cueva, desierto, bosque, etc.).
- Loop de Pikachu corriendo en las pantallas pre-batalla.
- HUDs uniformes con barra de HP que drena con tween, tipos como tags,
  iconos pixel del equipo abajo (silueta negra cuando un Pokémon cae).
- Caja de diálogo con efecto typewriter.
- Música y efectos: BGM de Pokémon Showdown, SFX retro 8-bit
  sintetizados, cries reales de los Pokémon al entrar a la pista.

### Combate

- Cambio de Pokémon voluntario o forzado (al caer uno, eliges reemplazo).
- Movimientos con tipo, categoría (físico/especial), poder, precisión y PPs.
- Efectividades de tipo Gen 6+ (incluye Hada).
- STAB, críticos y factor random estilo Showdown.
- Eventos del turno encadenados ("¡X usó Y!" → daño → "¡Súper eficaz!" → "¡Z se debilitó!").

---

## Agentes implementados

Los dos agentes del primer entregable comparten una interfaz común
(`Agent.choose_action`) → para añadir Nivel 3 / Minimax / GA solo se
crea un archivo nuevo en `src/agents/`.

### Nivel 1 — RandomAgent

Archivo: [`src/agents/random_agent.py`](src/agents/random_agent.py)

**Política:** elige uniformemente entre las acciones legales del turno
(atacar con cualquier mov o cambiar a cualquier Pokémon vivo del banquillo).
No discrimina entre atacar y cambiar.

**Para qué sirve:** es el **baseline** del proyecto. Cualquier agente
posterior tiene que ganarle holgadamente. Sirve también como grupo de
control en los experimentos de comparación.

### Nivel 2 — HeuristicAgent

Archivo: [`src/agents/heuristic_agent.py`](src/agents/heuristic_agent.py)

**Política — lookahead 1-ply:** para cada acción legal, el agente:

1. Clona el estado actual del combate (`state.clone()`).
2. Predice qué hará el rival — modelo simple: el rival usa su movimiento
   con **mayor daño esperado**.
3. Avanza un turno completo en la simulación (`sim.step`).
4. Puntúa el estado resultante con la heurística **H1**.
5. Elige la acción con mayor puntuación; los empates se rompen al azar.

**Heurística H1 — diferencia de HP normalizada:**

```
H1 = HP_propio_normalizado − HP_rival_normalizado

donde
  HP_propio_normalizado = Σ HP_actual_propio / Σ HP_máx_propio
  HP_rival_normalizado  = Σ HP_actual_rival / Σ HP_máx_rival

H1 ∈ [-1, 1]
```

**Por qué normalizada:** el PDF exige normalización para la heurística
avanzada del Nivel 3. La adelantamos aquí para que H1 viva en el mismo
rango que las componentes futuras (vivos, velocidades, ventajas de tipo)
y la combinación lineal del Nivel 3 funcione sin reescalar.

**Daño esperado sin RNG:** dentro del lookahead, el daño se calcula con
la fórmula del PDF pero usando el promedio del factor random (~0.925) y
multiplicando por la accuracy. Así el agente es determinista dado el
mismo estado — vital para que los experimentos sean reproducibles.

---

## Modelado del combate

### Fórmula de daño (la del PDF, literal)

```
Damage = (Attack / Defense_op) · BasePower − Speed_op · K
```

Implementada en [`src/core/damage.py`](src/core/damage.py). Encima
añadimos los bonificadores estándar de la serie:

- **STAB** (×1.5 si el tipo del mov coincide con un tipo del atacante)
- **Efectividad de tipo** (tabla Gen 6+, incluye Hada)
- **Crítico** (×1.5 con probabilidad 1/16)
- **Factor random** uniforme entre 0.85 y 1.00 (estilo Showdown)
- **Tirada de precisión** contra `move.accuracy`

`K = 0.35` (configurable en [`config.py`](config.py)).

### Stats efectivas

Las stats base se toman de Pokémon Showdown / Bulbapedia y se escalan a
nivel virtual 50 con las fórmulas estándar de la serie:

```
HP_max = (2 · base_hp + 110) · 50/100 + 10
Stat   = (2 · base_stat) · 50/100 + 5     (Atk, Def, AtkE, DefE, Vel)
```

### Reglas del turno

1. Ambos jugadores eligen su acción (atacar / cambiar).
2. Los **cambios** resuelven primero (estilo Showdown).
3. Entre dos ataques: orden por **prioridad** del movimiento, luego por
   **velocidad**, luego desempate aleatorio.
4. Si un Pokémon cae a 0 HP, su entrenador entra en `pending_switch` y
   debe enviar reemplazo antes del próximo turno.
5. El combate termina cuando un equipo no tiene Pokémon vivos.

`BattleState.clone()` ya está implementado → consumible directamente por
el `MinimaxAgent` que vendrá en la entrega final.

---

## Datos del juego

Todos los datos están en JSON editable, dentro de `data/`:

| Archivo | Contenido |
|---|---|
| `pokemon.json` | 36 Pokémon con tipos, stats base y rutas a sprites |
| `moves.json` | 144 movimientos (18 tipos × 8) con tipo, categoría, poder, precisión, PP y flags |
| `learnsets.json` | Pool real de movs por especie (level-up + MTs + tutores en Gen 8/9). 19–32 movs por Pokémon |
| `type_chart.json` | Matriz 18 × 18 de efectividades, Gen 6+ |

Para rebalancear el juego no hay que tocar código: editar el JSON y listo.

---

## Resultados preliminares

```
=== Smoke test: 50 partidas, 4v4, semilla 42 ===
Random   ganó:   6  (12%)
Heur(HP) ganó:  44  (88%)
Empates:          0
Duración media: 11.7 turnos
```

El Heurístico vence al Random ~88% de las veces con una sola componente
(H1) y un solo turno de lookahead. Resultado coherente — H1 está
capturando la dirección correcta de "estado favorable" — y es la base
para medir cuánto suma cada componente que añadiremos en el Nivel 3.

Reproducible con `python main.py --headless`.

---

## Estructura del repositorio

```
.
├── main.py                   Entrypoint (GUI o --headless)
├── config.py                 Constantes globales (K, FPS, paleta, rutas)
├── requirements.txt
│
├── data/                     ◀ DATOS DEL JUEGO (JSON editable)
│   ├── pokemon.json
│   ├── moves.json
│   ├── learnsets.json
│   └── type_chart.json
│
├── assets/                   ◀ ARTE Y AUDIO
│   ├── sprites/
│   │   ├── front/            sprites animados del rival
│   │   ├── back/             sprites animados del jugador
│   │   └── icons/            iconos pixel estáticos
│   ├── ui/
│   │   ├── backgrounds/      8 fondos de combate
│   │   └── intro/pikachu_loop/  frames del loop pre-batalla
│   ├── fonts/                Press Start 2P
│   └── audio/
│       ├── music/            BGM (de Showdown)
│       ├── cries/            grito de cada Pokémon
│       └── sfx/              hits, faint, select (sintetizados)
│
├── src/                      ◀ CÓDIGO FUENTE
│   ├── core/                 Motor PURO de combate (sin Pygame)
│   │   ├── types.py          Tipos + tabla de efectividad
│   │   ├── move.py           Modelo Move + carga de moves.json
│   │   ├── pokemon.py        Especies, instancias, random_moveset
│   │   ├── action.py         Action(attack | switch)
│   │   ├── damage.py         Fórmula del PDF + bonificadores
│   │   └── battle.py         BattleState + step + clone
│   │
│   ├── agents/               IA intercambiable
│   │   ├── base_agent.py     Interfaz Agent (abstracta)
│   │   ├── random_agent.py   ◀ NIVEL 1
│   │   ├── heuristic_agent.py ◀ NIVEL 2
│   │   └── human_agent.py    Para que el jugador humano "actúe"
│   │
│   ├── ui/                   Capa Pygame (estilo Pokémon Gen 3)
│   │   ├── game.py           Loop principal
│   │   ├── audio.py          Wrapper resiliente de mixer
│   │   ├── assets_loader.py  GIFs animados, iconos pixel, fuentes
│   │   ├── widgets/          SpriteAnimator, HPBar, TextBox, Menu, VideoLoop
│   │   └── scenes/           Menú, Config, TeamSelect, MoveSelect, Battle
│   │
│   └── utils/                logger, RNG con semilla
│
└── scripts/
    ├── import_sprites.py     Migra GIFs a assets/sprites/{front,back}
    ├── extract_intro.py      Pre-extrae frames del PikachuLoop.mp4
    ├── generate_sfx.py       Genera SFX 8-bit por síntesis
    └── headless_smoke.py     50 partidas Random vs Heurística
```

Tres convenciones que vale la pena conocer:

1. **`core/` es Pygame-agnóstico.** Permite simular miles de partidas en
   modo headless para los experimentos de la entrega final.
2. **Los agentes son intercambiables.** Para el Nivel 3 / Minimax / GA
   solo se añaden archivos en `src/agents/` que implementen
   `Agent.choose_action`.
3. **Los datos viven en JSON.** Tu compañero puede balancear movs sin
   tocar código.

---

## Controles

| Acción | Teclado | Mouse |
|---|---|---|
| Mover cursor | `↑ ↓ ← →` o `WASD` | mover el ratón |
| Confirmar | `Enter` / `Espacio` / `Z` | clic izquierdo |
| Cancelar | `Esc` / `Backspace` / `X` | — |
| Saltar texto | `Enter` / `Espacio` | clic |
| Confirmar selección de equipo / movs | `Tab` | clic en *Confirmar* |
| Volver atrás (escenas pre-batalla) | `Esc` | — |

---


## Créditos

- **Curso:** Inteligencia Artificial — UNMSM 2026, prof. Marco Sobrevilla.
- **Sprites de Pokémon:** © Nintendo / Game Freak — uso académico no comercial.
- **Música y cries:** Pokémon Showdown (`play.pokemonshowdown.com/audio/`).
- **Fondos de combate y video del intro:** ofrecidos por el equipo.
- **Fórmula de daño:** adaptada al curso.
- **Tabla de efectividad de tipos:** Bulbapedia, Gen 6+.

