# Diseño del Agente Nivel 3 — Minimax con pesos optimizados por algoritmo genético

> Documento de diseño vivo. Recoge **todas las decisiones tomadas hasta ahora**
> para el agente de Nivel 3 de POKE-FISI, con su justificación. Sirve de
> referencia antes de escribir una sola línea de código.
>
> Estado: bloques 0, A, B y C **cerrados** e **implementados**. Resultados
> finales en §7.

---

## 0. Contexto y motivación

POKE-FISI es un simulador de combate Pokémon por turnos con IA intercambiable.
Todos los agentes implementan la misma interfaz
[`Agent.choose_action(state, side)`](src/agents/base_agent.py). Hay tres niveles:

- **Nivel 1 — RandomAgent**: elige una acción legal uniformemente al azar. Baseline.
- **Nivel 2 — HeuristicAgent**: lookahead voraz de 1 turno con una única
  heurística (diferencia de HP).
- **Nivel 3 — (este documento)**: minimax con poda α-β y una función de
  evaluación multi-componente cuyos pesos se optimizan con un algoritmo genético.

### 0.1. Diagnóstico del Nivel 2 (por qué hace falta el Nivel 3)

El Nivel 2 ([`src/agents/heuristic_agent.py`](src/agents/heuristic_agent.py))
es un agente **débil-a-intermedio**, claramente mejorable. Sus límites
estructurales —y que el Nivel 3 ataca directamente— son:

1. **Profundidad 1 (voraz).** Solo simula un turno hacia adelante. No puede
   planear secuencias (sacrificar un Pokémon para entrar con ventaja, aguantar
   un turno malo por una ganancia posterior).
2. **Modelo del rival ingenuo.** Asume que el rival siempre usa su ataque de
   máximo daño y **nunca cambia**. Es un punto ciego explotable.
3. **Una sola componente de evaluación (HP).** Ignora ventaja de tipo,
   velocidad, número de Pokémon vivos y amenazas de KO.
4. **Casi nunca cambia de Pokémon.** Como evalúa el estado un turno después, un
   cambio (que cuesta un turno y un golpe gratis) casi siempre puntúa peor que
   atacar. El agente solo cambia cuando está forzado, perdiendo todo el juego
   posicional de cambios.

El Nivel 3 corrige los cuatro puntos: profundidad de búsqueda real (1),
modelo adversarial del rival (2), evaluación multi-componente (3) y capacidad de
valorar cambios estratégicos porque la búsqueda ve los turnos siguientes (4).

### 0.2. Restricción que hace todo esto posible

El motor de combate ([`src/core/`](src/core/battle.py)) es **puro**: no importa
Pygame ni hace I/O. Eso permite que el agente **clone el estado y simule miles
de turnos** internamente, que es la base tanto del minimax como del
entrenamiento del genético en modo headless.

---

## 1. Arquitectura general del Nivel 3

El agente se compone de **dos piezas independientes**:

```
        ┌─────────────────────────────┐
        │  BÚSQUEDA (Minimax + α-β)    │  ← Bloque A
        │  Decide la mejor acción      │
        │  explorando varios turnos    │
        └──────────────┬──────────────┘
                       │ llama en cada hoja
                       ▼
        ┌─────────────────────────────┐
        │  EVALUACIÓN  H = Σ wᵢ·Cᵢ     │  ← Componentes (Bloque A)
        │  Puntúa un estado del juego  │
        └──────────────┬──────────────┘
                       │ los pesos wᵢ los fija…
                       ▼
        ┌─────────────────────────────┐
        │  ALGORITMO GENÉTICO          │  ← Bloque B (pendiente)
        │  Optimiza el vector [w1..w5] │
        └─────────────────────────────┘
```

Idea clave: **el minimax es solo la búsqueda; la "inteligencia" de qué es un
buen estado vive en la función de evaluación; y el genético afina esa función.**

---

## 2. Función de evaluación: los componentes (C1–C5)

### 2.1. Principio de diseño

La evaluación de un estado es una **combinación lineal ponderada**:

```
H(state, side) = w1·C1 + w2·C2 + w3·C3 + w4·C4 + w5·C5
```

El algoritmo genético optimiza el vector de pesos `w = [w1, w2, w3, w4, w5]`.
Para que esto funcione bien, **todos los componentes cumplen dos reglas**:

1. **Cada Cᵢ es un diferencial "yo − rival" normalizado a `[-1, 1]`**
   (positivo = me favorece). Así todos viven en la misma escala y los pesos son
   directamente comparables: el GA no tiene que compensar unidades distintas.
2. **Son baratos de calcular.** El minimax los llama en cada hoja del árbol; no
   se simula ningún turno dentro de la evaluación.

> **Decisión tomada:** arrancamos con el **núcleo C1–C5** (ni el mínimo C1–C3,
> ni el extendido con C6/C7). Razón: cubre lo "macro" (quién gana la partida) y
> lo "micro" (quién gana el enfrentamiento actual) sin inflar el vector de pesos
> ni arriesgar sobreajuste en un juego mecánicamente simple.

### 2.2. Componentes "macro" (quién va ganando la partida)

**C1 — Diferencial de HP** *(es la H1 del Nivel 2; lo reutilizamos)*

```
C1 = Σ hp_propio / Σ hp_max_propio  −  Σ hp_rival / Σ hp_max_rival     ∈ [-1, 1]
```

Mide el desgaste global de ambos equipos.

**C2 — Diferencial de Pokémon vivos**

```
C2 = vivos_propios / N_propio  −  vivos_rival / N_rival                ∈ [-1, 1]
```

**Crítico y ausente en el Nivel 2.** Ganar es llevar al rival a 0 Pokémon vivos,
no a 0 HP. Distingue "4 Pokémon al 25 %" de "1 Pokémon al 100 %" (que C1 puntúa
casi igual) y empuja al agente a **rematar** en lugar de repartir daño.

### 2.3. Componentes "micro" (quién gana el enfrentamiento actual)

Es justo lo que el Nivel 2 ignora y por lo que pierde posicionalmente.

**C3 — Ventaja de tipo del Pokémon activo** (escala logarítmica para simetría)

```
off_mía  = máx. efectividad de mis movimientos de daño contra su activo
off_suya = máx. efectividad de sus movimientos de daño contra mi activo
C3 = ( log₂(clamp(off_mía,  0.25..4)) − log₂(clamp(off_suya, 0.25..4)) ) / 4   ∈ [-1, 1]
```

- Uso `log₂` para que "×2 ofensivo" y "½ defensivo" pesen de forma simétrica
  (×0.25→−2, ×1→0, ×4→+2).
- La inmunidad (efectividad 0) la trato como el extremo `−2` en log
  (ofensivamente inútil / defensivamente óptima).
- Solo cuento movimientos con `power > 0`: en este motor los movimientos de
  poder 0 no hacen nada.

**C4 — Ventaja de velocidad del activo** (acotada, sin escala mágica)

```
C4 = (v_mío − v_rival) / (v_mío + v_rival)                             ∈ [-1, 1]
```

En este motor la velocidad es **doblemente decisiva**: define el orden del turno
*y* aparece restando en la fórmula de daño (`− Speed_op · K`). Esta fórmula da el
signo (quién pega primero) y una magnitud acotada de una sola expresión.

**C5 — Presión de KO** (umbral binario, con daño esperado sin RNG)

```
yo_tumbo  = 1 si _expected_damage(mi_mejor_mov)  ≥ hp_su_activo  si no 0
me_tumban = 1 si _expected_damage(su_mejor_mov)  ≥ hp_mi_activo  si no 0
C5 = yo_tumbo − me_tumban                                              ∈ {-1, 0, +1}
```

Reutiliza la función `_expected_damage` que ya existe en el Nivel 2. Combinada
con C4 modela el núcleo táctico real: *si voy más rápido **y** puedo tumbar, gano
el intercambio limpio.*

> **Decisión tomada:** C4 (velocidad) y C5 (KO) llevan **pesos separados**, no
> combinados en un único término de "tempo". Razón: el GA decide
> independientemente cuánto vale cada uno y podemos diagnosticar qué importa.

### 2.4. Componentes descartados (por ahora)

- **C6 — Calidad del mejor relevo en banca**: el mejor matchup de tipo
  disponible al cambiar. Modelaría mejor *cuándo cambiar*, pero es parcialmente
  redundante con C3.
- **C7 — Recursos (PP)**: bajo impacto en este modelo; probablemente ruido para
  el GA.

Se añadirán **solo si** los experimentos muestran una debilidad concreta que el
núcleo C1–C5 no cierra. En un juego mecánicamente simple, más componentes ≠
mejor agente: arriesga **sobreajuste** del genético a ruido.

### 2.5. Nota sobre la linealidad

Una combinación lineal **no puede representar interacciones** tipo "voy más
rápido **Y** puedo tumbar" (eso sería un producto C4×C5). **No hace falta
codificarlo**: el propio minimax, al buscar 2+ turnos, *ve* ocurrir el KO en el
turno siguiente. Por eso C4/C5 importan sobre todo en la **frontera de búsqueda**
(las hojas), para orientar; las tácticas dentro del horizonte las descubre la
búsqueda. Esto justifica mantener la evaluación lineal y simple.

---

## 3. Bloque A — Búsqueda Minimax

### 3.1. El problema central: el juego es de movimiento simultáneo

El minimax clásico asume **turnos alternados**: yo juego, tú ves mi jugada, tú
respondes. Pero [`step(action_a, action_b)`](src/core/battle.py) recibe **las dos
acciones a la vez**: ambos comprometen su jugada sin ver la del otro. Es
estructuralmente como un piedra-papel-tijera en cada turno. El minimax puro no
aplica directo; hay que abstraer la simultaneidad en el árbol.

> **Decisión tomada: colapso secuencial "paranoico" + α-β.**
>
> Finjo que yo elijo primero y que el rival ve mi jugada y responde de forma
> óptima. Como le doy *más* información de la que tiene en realidad, mi
> estimación es **pesimista/segura** (juego a prueba del peor caso). Resulta en
> un árbol minimax normal: nodo MAX (yo) → nodo MIN (rival) → aplico el turno →
> recursión. Integra con α-β sin dependencias extra y es lo que usan en la
> práctica los bots de Pokémon.
>
> **Alternativas descartadas:**
> - *Nash matricial por turno* (matriz de pagos + equilibrio de estrategia
>   mixta vía LP de scipy en cada nodo): teóricamente correcto para juego
>   simultáneo, pero más complejo y caro. Sobreingeniería para este proyecto.
> - *Mejor-respuesta vs modelo fijo (expectimax)*: el rival juega una política
>   fija (máx. daño estilo Nivel 2) y solo ramifican mis acciones. Mucho más
>   rápido, pero explotable y "menos minimax".

### 3.2. Estructura del árbol (pseudocódigo)

Cada nivel de recursión = **un turno completo**, resuelto en dos capas de
decisión (yo elijo → el rival responde viendo mi jugada) pero **una sola
transición** del estado:

```python
def search(state, depth, α, β):
    if state.is_over():
        return terminal_value(state, depth)        # ±TERMINAL ∓ turnos
    if depth == 0:
        return evaluate(state, me)                  # w1·C1 + … + w5·C5

    best = -inf
    for a in ordered_actions(state, me):            # capa MAX (mis acciones)
        worst = +inf
        for b in ordered_actions(state, rival):     # capa MIN (rival ve mi 'a' → paranoico)
            child = simulate_turn(state, a, b)       # transición DETERMINISTA, una sola vez
            v = search(child, depth - 1, α, β)       # valor SIEMPRE desde MI perspectiva
            worst = min(worst, v)
            if worst <= α:
                break                                # corte α
        best = max(best, worst)
        if best >= β:
            break                                    # corte β
        α = max(α, best)
    return best
```

**Por qué MAX/MIN explícito y no negamax:** la simultaneidad hace que un turno
abarque dos capas de decisión pero **una sola transición** de estado. Mantener la
evaluación siempre desde mi perspectiva y hacer MAX/MIN explícito es más claro
que negamax (que voltearía la perspectiva por capa). La antisimetría de C1–C5
—`eval(estado, rival) = −eval(estado, yo)`— sigue garantizando que el juego es de
suma cero, lo que valida usar una sola ventana α-β.

**Conteo de profundidad:** `depth` se mide en **turnos completos**. Cada
recursión consume una unidad de `depth` (aunque internamente sean dos capas de
decisión). `depth = 3` ⇒ 3 turnos completos de anticipación.

### 3.3. Las cuatro piezas de soporte

**1. `simulate_turn(state, a, b)` — transición determinista**

Clona el estado y replica el orden de resolución de
[`step`](src/core/battle.py) (cambios primero → orden por prioridad/velocidad)
pero usando **daño esperado**: factor random promediado (~0.925), sin crítico,
precisión como multiplicador. No usa `rng`, así que el árbol es **determinista y
reproducible**.

> **Por qué una transición propia y no `step`:** el `step` real usa RNG (crítico,
> factor random, precisión, desempate de velocidad). Si el árbol usara
> transiciones estocásticas, los valores de los nodos serían inconsistentes y el
> minimax dejaría de ser válido (necesitaríamos expectimax con nodos de azar →
> explosión del árbol).
>
> *Detalle de implementación:* `simulate_turn` no debe tocar el `rng` del agente,
> para no contaminar el desempate de la raíz.

**2. `ordered_actions(state, side)` — generación + ordenado + poda**

- Deriva de [`legal_actions`](src/core/battle.py) → maneja `pending_switch`
  (cambios forzados tras un debilitamiento) **sin caso especial**: si un lado
  está obligado a cambiar, `legal_actions` ya devuelve solo cambios.
- **Ataques primero**, ordenados por daño esperado / flag de KO → mejora los
  cortes de α-β (probar primero las mejores jugadas poda más rama).
- **Cambios: solo top-K** por mejora de matchup.

> **Decisión tomada: poda dirigida de cambios (top-K por matchup).**
>
> Solo se consideran los cambios que mejoran el matchup de tipo (traer un
> Pokémon que resiste el STAB rival), limitados a los mejores K. Reduce la
> ramificación de ~7 a ~4-5 por lado manteniendo el cambio estratégico.
>
> **Alternativas descartadas:** *todos los cambios* (correcto pero árbol mucho
> mayor, entrenamiento del GA más lento) y *solo cambios forzados* (lo más
> rápido, pero pierde el cambio estratégico, que es justo la debilidad del
> Nivel 2 que queremos corregir).
>
> Para la capa MIN ordeno las acciones del rival por **cuánto me dañan**, de modo
> que la refutación fuerte aparezca primero y poda más.

**3. `evaluate(state, me)` — las hojas**

La combinación lineal `Σ wᵢ·Cᵢ` de la sección 2. Es donde el genético inyecta
los pesos.

**4. `terminal_value(state, depth)` — estados finales**

`+TERMINAL` si gano / `−TERMINAL` si pierdo, con `TERMINAL ≫ Σ|wᵢ|` (una victoria
siempre vale más que cualquier estado heurístico "bonito") más un bonus por
**ganar en menos turnos** (usa el `depth` restante para premiar remates rápidos y
evitar que alargue partidas ganadas).

### 3.4. Factor de ramificación y rendimiento

En 4v4, `legal_actions` da hasta 4 ataques + 3 cambios = **7 acciones por lado**
→ hasta 49 combinaciones por turno. A profundidad 3 son ~118k nodos antes de
podar. Los **cambios** son el principal inflador del árbol; por eso la poda
top-K (pieza 2) y el ordenado de movimientos (mejores cortes α-β) son esenciales.

**Acoplamiento con el genético:** el coste del GA es
`población × generaciones × partidas × turnos × coste_búsqueda`. La profundidad
del minimax multiplica todo eso. Plan: **entrenar el GA con profundidad 2** y
**evaluar el agente final con profundidad 3–4**.

### 3.5. Parámetros expuestos (irán a `config.py` / al genético)

| Parámetro              | Default propuesto        | Notas                                          |
|------------------------|--------------------------|------------------------------------------------|
| `MINIMAX_DEPTH`        | 3 turnos (entrenar a 2)  | la profundidad multiplica el coste del GA      |
| `SWITCH_TOPK`          | 2 en raíz / 1 en profundo| control de ramificación de cambios             |
| `TERMINAL` + bonus     | `≫ Σ|wᵢ|`                | la victoria domina cualquier valor heurístico  |
| `w1..w5`               | lo optimiza el GA        | vector genoma del bloque B                      |

- **Desempate en la raíz:** acciones con igual valor → `rng` sembrado
  (reproducible), igual que en el Nivel 2.
- **Optimizaciones opcionales, fuera del MVP:** tabla de transposición y
  profundización iterativa con límite de tiempo. No son necesarias a
  profundidad 3; se dejan para después de validar lo básico.

### 3.6. Funciones a implementar (resumen)

```
search(state, depth, α, β)          → minimax con α-β (núcleo)
simulate_turn(state, a, b)          → transición determinista
ordered_actions(state, side)        → generación + ordenado + poda top-K
evaluate(state, me)                 → Σ wᵢ·Cᵢ  (hojas)
terminal_value(state, depth)        → ±TERMINAL con bonus de turnos
_expected_damage(...)               → ya existe en el Nivel 2; se reutiliza
```

---

## 4. Bloque B — Algoritmo genético

Su trabajo es **encontrar el vector de pesos `[w1..w5]`** que hace que la función
de evaluación del bloque A juegue lo mejor posible. El espacio es pequeño (5
dimensiones continuas), así que el reto no es la convergencia sino **medir bien
el fitness sin que sea carísimo ni se sobreajuste**.

### 4.1. El genoma

```
genoma = [w1, w2, w3, w4, w5]      # un real por componente
```

> **Decisión tomada: simplex no-negativo.** `wᵢ ≥ 0`, normalizados a `Σwᵢ = 1`.
>
> Ventajas:
> 1. **Codifica el conocimiento de dominio** "cada componente es favorable cuando
>    es positivo" (por diseño todos los Cᵢ lo son) → encoge el espacio de
>    búsqueda y reduce el sobreajuste.
> 2. **Escala fija:** `Σ|wᵢ| = 1` siempre, así el `TERMINAL` del bloque A solo
>    necesita superar 1.
> 3. **Interpretables:** cada peso es el "porcentaje de importancia" de su
>    componente — útil para el artículo.
>
> **Alternativa descartada:** *real libre (con negativos)*. Más expresivo, pero
> arriesga descubrir pesos sin sentido físico y sobreajustar.

### 4.2. La función de fitness

El fitness de un genoma = **jugar partidas con esos pesos y medir qué tan bien le
va**. Se define en tres ejes:

**Eje 1 — ¿Contra quién juega?**

> **Decisión tomada: Nivel 2 fijo.** Cada genoma se mide por su win-rate contra
> el agente heurístico Nivel 2. Mide directamente el objetivo del proyecto
> ("superar al Nivel 2"), es limpio y reportable.
>
> **Alternativas descartadas:** *gauntlet (Nivel 1 + Nivel 2)* — robusto pero el
> Nivel 1 aporta señal débil al ser tan fácil; *coevolución (vs la propia
> población)* — vistoso pero sufre dinámicas cíclicas "Red Queen", más caro y más
> difícil de reportar.

**Eje 2 — ¿Qué señal mide?**

> **Decisión tomada: win-rate + margen.** Ganar/perder como señal principal, y
> como desempate **denso** el **HP restante** y la **rapidez de la victoria**.
>
> Da un gradiente más fino que el win-rate puro (señal escasa 0/1 por partida) →
> converge con **menos partidas**, que es justo lo caro. Esquema propuesto:
>
> ```
> fitness = victorias
>         + ε · (HP_propio_restante_medio − HP_rival_restante_medio)   # desempate
>         + δ · (rapidez de las victorias)                              # premia rematar
> ```
> con `ε, δ` pequeños para que nunca dominen sobre ganar/perder.

**Eje 3 — Número de partidas y anti-sobreajuste** *(fijado por buenas prácticas,
no se sometió a decisión)*

- Cada generación se muestrea un **conjunto de configuraciones** (equipos y
  movesets aleatorios de ambos lados, semillas) → los pesos deben **generalizar**,
  no ganarle a un matchup concreto.
- **Números aleatorios comunes (CRN):** *todos* los genomas de una generación
  juegan **las mismas** configuraciones → comparación pareada, mucha menos
  varianza por partida jugada. Se **re-muestrean** las configuraciones cada
  generación para no fijar el aprendizaje a un set.
- **Validación final en un conjunto held-out** de configuraciones/semillas nunca
  vistas en entrenamiento → win-rate insesgado para el artículo.
- `N ≈ 20–40` partidas por genoma y generación, con la **búsqueda a
  profundidad 2** (según el bloque A).

### 4.3. Operadores genéticos

Defaults estándar para optimización de vectores reales; no requirieron decisión:

| Pieza              | Elección                                                        | Razón                                                                 |
|--------------------|-----------------------------------------------------------------|-----------------------------------------------------------------------|
| **Selección**      | Torneo (tamaño 3) + **elitismo** (1–2 mejores pasan intactos)   | Robusto al escalado del fitness; el elitismo evita perder al mejor     |
| **Cruce**          | Aritmético / BLX-α                                              | Apropiado para vectores reales (mezcla suave entre padres)            |
| **Mutación**       | Gaussiana `N(0, σ)` por gen, con **σ decreciente** por gen.     | Exploración amplia al inicio, ajuste fino al final                    |
| **Reparación**     | Tras cruce/mutación: re-clip a `≥0` y **re-normalizar** a suma 1| Mantiene el genoma dentro del simplex                                  |
| **Inicialización** | Aleatoria en el simplex, **sembrando** 1–2 priores             | "Todo el peso en HP" (= Nivel 2) y "pesos iguales": no empezar peor que el Nivel 2 y acelerar |
| **Población / gen**| ~30 / ~30, con **parada temprana** por estancamiento           | 5-D es fácil; no hace falta más                                       |
| **Terminación**    | Máx. generaciones o K generaciones sin mejora                  | —                                                                     |

### 4.4. Coste y reproducibilidad

- **Coste total** ≈ `población × generaciones × N × turnos × coste_búsqueda`. Por
  eso se **entrena a profundidad 2** y se **evalúa el agente final a 3–4**.
- Las partidas de cada genoma son independientes → **paralelizable por núcleos**
  (opcional).
- Todo bajo una **semilla maestra** fija → entrenamiento reproducible.
- **Salida del entrenamiento:** el vector `[w1..w5]` ganador se guarda (p. ej. en
  `config.py` o un JSON) y el agente Nivel 3 lo carga en producción; no se
  re-entrena en cada ejecución.

## 5. Bloque C — Integración y experimentos

### 5.0. Lo que el código ya nos da a favor

- **Interfaz de agente uniforme:** [`battle_scene.py`](src/ui/scenes/battle_scene.py)
  mapea el agente rival en `_agent_for(name)` (línea ~55) y el bucle de combate
  llama `choose_action` / `choose_forced_switch` (líneas ~318 y ~373) **sin saber
  qué agente es**. Conectar el Nivel 3 es añadir una rama.
- **Bucle headless reutilizable:** [`headless_smoke.py`](scripts/headless_smoke.py)
  ya tiene `play_once(agent_a, agent_b, size, rng)` **genérico** → sirve tal cual
  para enfrentar cualquier par de agentes.
- **`core/` puro:** el entrenamiento del GA corre miles de partidas sin Pygame.

### 5.1. Archivos nuevos

```
src/agents/minimax_agent.py     # el Agent: choose_action / choose_forced_switch
src/agents/evaluation.py        # C1–C5 + carga de pesos  (H = Σ wᵢ·Cᵢ)
src/agents/search.py            # search() α-β + simulate_turn() + ordered_actions()
data/level3_weights.json        # vector [w1..w5] entrenado (+ metadatos)
scripts/train_level3.py         # corre el GA headless → escribe level3_weights.json
scripts/evaluate.py             # torneo entre agentes → tabla de resultados del artículo
```

> El reparto en 3 módulos (`minimax_agent` / `evaluation` / `search`) es por
> legibilidad; podría consolidarse en `minimax_agent.py`.

### 5.2. Conexión del agente (motor)

Una rama nueva en `_agent_for` de
[`battle_scene.py`](src/ui/scenes/battle_scene.py) (~línea 55):

```python
def _agent_for(name):
    if name == "Random":   return RandomAgent()
    if name == "Minimax":  return MinimaxAgent.from_weights_file()   # lee el JSON
    return HeuristicAgent()
```

`MinimaxAgent` implementa `Agent.choose_action` (la búsqueda del bloque A) y
hereda/define `choose_forced_switch` para los cambios forzados.

### 5.3. Integración en la GUI

> **Decisión tomada: jugable + experimentos.** Además del harness headless, se
> expone el Nivel 3 en la pantalla de configuración para que un humano juegue
> contra él. Toca tres sitios (cambio pequeño):
>
> - [`config_scene.py`](src/ui/scenes/config_scene.py) línea 29: añadir
>   `"Nivel 3 (Minimax)"` a las opciones de "Inteligencia del rival".
> - `config_scene.py` líneas 41 y 93: el mapeo actual es **binario**
>   (`0 if Random else 1`) → generalizarlo a 3 opciones (índice ↔ string).
> - [`session.py`](src/ui/scenes/session.py) línea 14: el campo `opp_agent`
>   admite ahora `"Minimax"`.
>
> **Alternativa descartada:** *solo headless* (menos trabajo, pero no se podría
> jugar contra el Nivel 3 desde la interfaz).

### 5.4. Almacenamiento de los pesos

> **Decisión tomada: JSON en `data/`.** El vector entrenado vive en
> `data/level3_weights.json`, junto al resto de datos del juego.
>
> Ventajas: re-entrenar **no toca código**, sigue la convención del proyecto
> ("los datos viven en JSON") y permite guardar **metadatos** (fitness alcanzado,
> semilla, generaciones, fecha) junto a los pesos. Esquema propuesto:
>
> ```json
> {
>   "weights": [0.0, 0.0, 0.0, 0.0, 0.0],
>   "components": ["hp", "vivos", "tipo", "velocidad", "ko"],
>   "meta": {"fitness": 0.0, "seed": 42, "generations": 30, "depth_train": 2}
> }
> ```
>
> **Alternativa descartada:** *constante en `config.py`*. Más simple, pero mezcla
> parámetros aprendidos con configuración y re-entrenar implica editar código.

### 5.5. Flujo de entrenamiento (`train_level3.py`)

Corre el algoritmo genético del **bloque B** con semilla maestra fija y escribe
`data/level3_weights.json` con el vector ganador y sus metadatos. **Se ejecuta
una vez, offline**; el agente en producción solo *lee* el JSON (no se re-entrena
en cada partida). Entrena con **búsqueda a profundidad 2** (sección 3.4).

### 5.6. Flujo de evaluación (`evaluate.py`)

Torneo headless sobre un **conjunto held-out** de configuraciones (equipos,
movesets y semillas **nunca vistos en entrenamiento**) → win-rate insesgado.
Reutiliza el `play_once` genérico de `headless_smoke.py`. Evalúa el agente final
a **profundidad 3–4**.

### 5.7. Métricas para el artículo científico

| Métrica                                            | Para qué                                          |
|----------------------------------------------------|---------------------------------------------------|
| **Win-rate N3 vs N2** (con intervalo de confianza) | el resultado principal del entregable             |
| Win-rate N3 vs N1, y N2 vs N1                       | escalera completa de la jerarquía de agentes      |
| Duración media (turnos)                            | eficiencia del juego                              |
| **Curva de convergencia del GA** (fitness/gen.)    | evidencia de que el GA aprende                    |
| **Ablación por componente** (re-evaluar con wᵢ=0)  | cuánto aporta cada Cᵢ                             |
| **Win-rate vs profundidad** (1 / 2 / 3 / 4)        | efecto de la búsqueda minimax                     |
| Vector `[w1..w5]` aprendido                         | interpretación de qué priorizó el GA              |

Todas reproducibles con semilla fija, en línea con el `--headless` que ya existe
en [`main.py`](main.py).

---

## 6. Corrección del harness de simulación (verificado contra el código)

Antes de implementar el entrenamiento del GA se auditó el motor para garantizar
que la simulación masiva de partidas no introduce errores sutiles. Resumen de la
verificación y del único arreglo necesario.

### 6.1. Lo que ya está correcto

**Turnos bien intercalados / agentes diferenciados.** El bucle de
[`play_once`](scripts/headless_smoke.py) es correcto:

```python
a = agent_a.choose_action(state, 0)   # agente A ↔ lado 0
b = agent_b.choose_action(state, 1)   # agente B ↔ lado 1
state.step(a, b)
```

Los dos agentes eligen desde el **mismo estado previo** (ninguno ve la jugada del
otro) y un **único `step` atómico** resuelve el turno (cambios primero → ataques
por prioridad/velocidad/desempate, [`battle.py`](src/core/battle.py) ~99-117).
Es lo correcto para un juego simultáneo: **no** ocurre que un agente lea el estado
ya mutado por el otro, ni que se llame `step` dos veces. Los lados quedan fijos
toda la batalla y `pending_switch` se maneja por separado para cada lado.

**Movimientos aleatorios al inicio de cada batalla.**
[`make_team`](scripts/headless_smoke.py) → [`random_moveset`](src/core/pokemon.py)
hace `rng.sample(learnset, 4)` por Pokémon al construir el equipo.

**Solo esos 4 movimientos durante toda la batalla.**
[`Pokemon.build`](src/core/pokemon.py) fija `moves` y `pp` una sola vez; nunca se
regeneran. `legal_actions` itera exactamente `active.moves`, y —clave para el
minimax— [`Pokemon.clone`](src/core/pokemon.py) copia `moves=list(self.moves)` y
`pp=list(self.pp)`: dentro de la búsqueda los clones conservan los mismos 4 movs
y su PP.

### 6.2. ⚠️ Problema detectado: `clone()` consume del RNG de la batalla

[`BattleState.clone`](src/core/battle.py) hace:

```python
new = BattleState(..., rng=random.Random(self.rng.random()))
```

**Cada `clone()` extrae un número del RNG de la batalla** (`self.rng`), el mismo
que `step()` usa para daño, críticos, precisión y desempate de velocidad. El
minimax llama a `clone()` cientos o miles de veces por decisión, con estas
consecuencias para el entrenamiento del GA:

1. **Rompe los números aleatorios comunes (CRN).** Dos genomas distintos, sobre
   la misma configuración y semilla, exploran/podan diferente → llaman a `clone()`
   un número distinto de veces → consumen distinta cantidad del RNG → **las
   tiradas de daño reales divergen entre genomas**. La reducción de varianza por
   comparación pareada (§4.2, eje 3) deja de funcionar, en silencio.
2. **El resultado de la batalla pasa a depender de cuánto "pensó" el agente**,
   lo cual es conceptualmente incorrecto y dificulta la reproducibilidad.

> El turno en sí sigue siendo lógicamente correcto; el problema es de **higiene
> de RNG** y afecta a la *equidad y eficiencia* de la comparación de fitness, no
> a quién gana una partida aislada.

### 6.3. Solución (requisito de diseño antes de entrenar)

La deliberación del agente **nunca debe tocar el RNG de la batalla**. Como
`simulate_turn` (bloque A) ya es **determinista** (daño esperado, sin RNG), el
arreglo es directo:

1. **`clone()` debe aceptar un RNG independiente (o ninguno):** firma
   `clone(self, rng=None)`. La búsqueda pasa un RNG propio/desechable; como
   `simulate_turn` no usa RNG, ese RNG nunca importa.
2. **El RNG de la batalla queda exclusivo para el `step()` real**, sembrado por
   configuración → CRN intacto.
3. **Cada agente con su propio RNG** para desempates, sembrado por separado y
   **nunca el mismo objeto** que el de la batalla. `MinimaxAgent`/`HeuristicAgent`
   ya reciben su `rng`; basta con que el harness no les pase el de la batalla.

### 6.4. Notas menores del harness de entrenamiento

- **Reconstruir equipos frescos por partida.** Los `Pokemon` se mutan (HP, PP)
  durante el combate. Para CRN, guardar cada configuración como
  `(nombres, movesets, semilla_batalla)` y **reconstruir Pokémon nuevos** en cada
  partida de cada genoma — no reutilizar los mismos objetos.
- **Movesets garantizados de 4.** Los learnsets tienen 19–32 movs, así que
  `random_moveset` siempre devuelve 4; la rama `if len(pool) <= k` no se activa
  con los datos actuales.

---

## 7. Resultados y estado de implementación

### 7.1. Estado de implementación

Todo el diseño está implementado y verificado:

| Pieza | Archivo | Estado |
|---|---|---|
| Higiene de RNG (`clone(rng=…)`) | `src/core/battle.py` | ✅ |
| Componentes C1–C5 + evaluación | `src/agents/evaluation.py` | ✅ |
| Transición determinista | `src/agents/search.py` (`simulate_turn`) | ✅ |
| Minimax α-β + poda top-K | `src/agents/search.py` | ✅ |
| Agente + cargador de pesos | `src/agents/minimax_agent.py` | ✅ |
| Algoritmo genético (paralelo) | `scripts/train_level3.py` | ✅ |
| Benchmarks + ablación | `scripts/evaluate.py` | ✅ |
| Pesos entrenados | `data/level3_weights.json` | ✅ |
| Integración en la GUI | `config_scene` / `session` / `battle_scene` | ✅ |

### 7.2. Resultados (todos vs Nivel 2, configuraciones CRN reproducibles)

**Barrido de profundidad** (100 partidas, pesos prior): la profundidad **se
satura en 2** — más allá no hay ganancia y el coste se dispara.

| Profundidad | win-rate N3 |
|---|---|
| 1 | 55% |
| 2 | 62% |
| 3 | 62% (sin mejora) |

**Comparación de pesos** (held-out independiente, 300 partidas, ±2.9%):

| Pesos | win-rate | margen HP |
|---|---|---|
| uniforme | 54.0% | +0.076 |
| prior (a mano) | 57.3% | +0.137 |
| hp_only | 57.7% | +0.141 |
| macro (hp+vivos) | 58.7% | +0.149 |
| **convergidos del GA** `[0.51,0.39,0.09,0.01,0.01]` | **59.0%** | **+0.156** |

**Convergencia del GA** (pop=25, games=60, gens=50): la población convergió de
forma estable a **HP+vivos dominantes** (~90% del peso) con velocidad/KO≈0.

**Ablación leave-one-out** (300 partidas, base = pesos uniformes, ±2.9%):

| Componente anulado | Contribución al win-rate |
|---|---|
| vivos | **+6.0%** (significativo) |
| HP | **+5.7%** (significativo) |
| tipo | +1.3% (ruido) |
| velocidad | +0.3% (≈0) |
| KO | +0.3% (≈0) |

### 7.3. Conclusión honesta

- **La búsqueda aporta el grueso del valor** (~58% vs Nivel 2). La profundidad se
  satura en 2 turnos.
- **Entre los componentes de evaluación, solo HP y vivos importan** (~6% cada uno);
  tipo, velocidad y KO son ≈0 contra el Nivel 2. Confirmado por **dos vías
  independientes**: la convergencia del GA y la ablación.
- **El GA no mejora el win-rate sobre un prior sensato** (todos los sets "buenos"
  quedan en ~57–59%, dentro del ruido). Su aporte real es **descubrir
  automáticamente qué componentes importan** — coincide con la ablación hecha a
  mano. Es un resultado negativo honesto y reportable: en un juego mecánicamente
  simple y contra un rival voraz, el ajuste fino de pesos tiene margen marginal.
- **Lección metodológica:** la selección held-out de 80 partidas sufrió maldición
  del ganador (un candidato dio 62.5% que en un set fresco grande regresó a ~56%).
  Por eso se shippean los pesos **convergidos** (representativos y mejor medidos),
  no el "mejor de held-out".

---

## Apéndice — Decisiones tomadas (registro rápido)

| # | Decisión                                  | Elección                                  |
|---|-------------------------------------------|-------------------------------------------|
| 1 | Conjunto de componentes                   | Núcleo **C1–C5**                          |
| 2 | Velocidad (C4) y KO (C5)                   | **Pesos separados**                       |
| 3 | Abstracción del movimiento simultáneo     | **Secuencial paranoico + α-β**            |
| 4 | Manejo de cambios en la ramificación      | **Poda dirigida (top-K por matchup)**     |
| 5 | Codificación del genoma                    | **Simplex no-negativo** (Σwᵢ=1)           |
| 6 | Oponente de fitness                        | **Nivel 2 fijo**                          |
| 7 | Señal de fitness                           | **Win-rate + margen**                     |
| 8 | Almacenamiento de pesos                    | **JSON en `data/`**                       |
| 9 | Alcance de integración en GUI              | **Jugable + experimentos**                |

**Requisito de implementación (no negociable, ver §6):** `BattleState.clone()`
debe recibir un RNG independiente para que la búsqueda del minimax **no consuma
del RNG de la batalla** — imprescindible para que el CRN del entrenamiento del GA
funcione.

Todas las decisiones de diseño están tomadas. El documento está listo para
guiar la implementación.
