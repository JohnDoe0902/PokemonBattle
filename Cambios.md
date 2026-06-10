# Cambios sobre el código preexistente

> Registro de **modificaciones a archivos que ya existían** en el proyecto
> (lo ajeno al agente Nivel 3), hechas para soportar la implementación del
> Nivel 3 (minimax + algoritmo genético).
>
> **No** se listan aquí los archivos *nuevos* del Nivel 3
> (`src/agents/minimax_agent.py`, `evaluation.py`, `search.py`,
> `data/level3_weights.json`, `scripts/train_level3.py`, `scripts/evaluate.py`):
> esos son código propio del nuevo agente, no cambios sobre lo preestablecido.
>
> **Convención:** todo cambio en el código va marcado en el propio archivo entre
> comentarios `#AGREGADO Inicio … #AGREGADO Fin` (o `#AGREGADO` en línea) para
> poder localizarlo y revertirlo con facilidad.

---

## Índice de cambios

| # | Archivo | Tipo | Resumen |
|---|---------|------|---------|
| 1 | `src/core/battle.py` | Modificación | `clone()` acepta un RNG opcional (higiene de RNG para CRN) |
| 2 | `scripts/headless_smoke.py` | Modificación | Sembrado de los RNG de los agentes (reproducibilidad) |
| 3 | `src/agents/__init__.py` | Modificación | Exporta `MinimaxAgent` (Nivel 3) |
| 4 | `src/ui/scenes/battle_scene.py` | Modificación | Rama del Nivel 3 en `_agent_for` + import |
| 5 | `src/ui/scenes/config_scene.py` | Modificación | Opción "Nivel 3 (Minimax)" + mapeo a 3 valores |
| 6 | `src/ui/scenes/session.py` | Modificación | `opp_agent` admite `"Minimax"` (comentario) |
| 7 | `README.md` | Modificación | Nivel 3 pasa de "trabajo futuro" a "implementado" |

---

## 1. `src/core/battle.py` — `BattleState.clone()` acepta un RNG opcional

**Qué se cambió**

La firma pasó de `clone(self)` a `clone(self, rng=None)`. Cuando se pasa un
`rng`, la clonación lo usa directamente; cuando no (`rng=None`), se conserva el
comportamiento anterior (`random.Random(self.rng.random())`).

**Por qué**

El `clone()` original consumía un número del RNG de la batalla (`self.rng`) en
**cada** llamada. El minimax del Nivel 3 clona el estado cientos/miles de veces
por decisión, así que esa deliberación **perturbaría las tiradas reales de la
batalla** y rompería los "números aleatorios comunes" (CRN) del entrenamiento
del GA: dos genomas distintos consumirían distinta cantidad del RNG y las
partidas divergirían de forma injusta. (Detalle completo en
[`agente 3.md`](agente%203.md) §6.)

Con el parámetro, la búsqueda pasará su propio RNG independiente y **no tocará**
el RNG de la batalla.

**Compatibilidad**

- La ruta por defecto (`rng=None`) es **byte-idéntica** a la anterior, por lo que
  el Nivel 2 y el smoke test headless no cambian su comportamiento.
- Cambio retrocompatible: los llamadores existentes (`state.clone()`) siguen
  funcionando sin tocarlos.

**Verificación**

Smoke test ejecutado tras el cambio: corre sin errores y el Nivel 2 sigue
ganando al Random con normalidad.

---

## 2. `scripts/headless_smoke.py` — sembrado de los RNG de los agentes

**Qué se cambió**

En `run()`, los agentes se creaban sin semilla:

```python
rng = random.Random(42)
a, b = RandomAgent(), HeuristicAgent()
```

Ahora se derivan tres streams independientes de una semilla maestra:

```python
MASTER_SEED = 42
rng = random.Random(MASTER_SEED)                    # RNG exclusivo de la batalla
a = RandomAgent(random.Random(MASTER_SEED + 1))     # RNG propio del agente A
b = HeuristicAgent(random.Random(MASTER_SEED + 2))  # RNG propio del agente B
```

**Por qué**

El smoke test fijaba solo el RNG de la batalla, pero los agentes usaban un RNG
**sin semilla** (entropía del sistema). Por eso `py main.py --headless` daba un
resultado **distinto en cada corrida** (se observó un rango de ~72 %–88 %), pese
a que el README lo describía como reproducible. Cada agente recibe ahora su
propio stream, independiente del de la batalla — la misma convención de sembrado
que usará el GA.

**Efecto observable**

- El resultado pasó a ser **reproducible**: corridas repetidas dan exactamente
  82 % / 18 % y 10.6 turnos de media.
- Nota: 82 % es el valor reproducible real con esta semilla; el 88 % que figuraba
  en el README provenía de un sembrado distinto/inexistente.

**Verificación**

Dos corridas consecutivas de `py main.py --headless` produjeron resultados
idénticos.

---

## 3. `src/agents/__init__.py` — exporta `MinimaxAgent`

Se añade `from .minimax_agent import MinimaxAgent` y se incluye en `__all__`, para
que el resto del proyecto (en particular la GUI) pueda importar el agente Nivel 3
con `from src.agents import MinimaxAgent`.

---

## 4. `src/ui/scenes/battle_scene.py` — rama del Nivel 3 en `_agent_for`

- Import ampliado a `MinimaxAgent`.
- `_agent_for(name)` ahora devuelve `MinimaxAgent.from_weights_file()` cuando
  `name == "Minimax"` (carga los pesos entrenados de `data/level3_weights.json`).
  El resto (Random/Heuristic) no cambia.

---

## 5. `src/ui/scenes/config_scene.py` — opción "Nivel 3 (Minimax)"

- Se añade `"Nivel 3 (Minimax)"` a las opciones de "Inteligencia del rival".
- El mapeo índice↔string, antes **binario** (`0 if Random else 1`), pasa a 3 vías
  mediante diccionarios: lectura `{"Random":0,"Heuristic":1,"Minimax":2}` y
  escritura `{0:"Random",1:"Heuristic",2:"Minimax"}`.

---

## 6. `src/ui/scenes/session.py` — `opp_agent` admite `"Minimax"`

Sólo se amplía el comentario del campo `opp_agent` a `"Random" | "Heuristic" |
"Minimax"`. El campo ya era un `str`, así que no hubo cambio funcional.

---

## 7. `README.md` — Nivel 3 de "futuro" a "implementado"

Actualización de documentación (marcada con comentarios HTML
`<!--AGREGADO ...-->` para no romper el renderizado):
- Fila "Nivel 3 — Minimax α-β + AG | Listo" en la tabla de estado.
- Párrafo de pendientes: ahora solo queda el artículo científico.
- Nueva subsección "Nivel 3 — MinimaxAgent" con política, componentes, pesos y
  resultados honestos.
- Se corrigen menciones que trataban el Nivel 3 como trabajo futuro.

---

## Notas de entorno

- En esta máquina el intérprete es **`py`** (Windows), no `python` (este último
  apunta al alias del Microsoft Store y falla).
