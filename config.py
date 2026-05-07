"""
Configuración global de Pokefisi.

Cualquier valor de balanceo, ruta o flag de UI vive acá. Pensado para que
balancear el juego no requiera tocar lógica.
"""
from pathlib import Path

# ─── Rutas ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ASSETS_DIR = ROOT / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
SPRITES_FRONT_DIR = SPRITES_DIR / "front"
SPRITES_BACK_DIR = SPRITES_DIR / "back"
FONTS_DIR = ASSETS_DIR / "fonts"
AUDIO_MUSIC_DIR = ASSETS_DIR / "audio" / "music"
AUDIO_SFX_DIR = ASSETS_DIR / "audio" / "sfx"
# Fallback opcional: si existe una carpeta `sprites/` en la raíz del proyecto
# (con la estructura original `<Pokemon>/<name>.gif`), el loader la usará
# como respaldo. Es relativa al repo → si renombras la carpeta del proyecto
# todo sigue funcionando.
EXTERNAL_SPRITES_DIR = ROOT / "sprites"

# ─── Combate ──────────────────────────────────────────────────────────────────
TEAM_SIZE_OPTIONS = (3, 4)
DEFAULT_TEAM_SIZE = 4
MOVES_PER_POKEMON = 4

# K de la fórmula del PDF: Damage = (Atk/Def) * BasePower − Speed_op * K
DAMAGE_K = 0.35
# Factor random aplicado al daño (estilo Showdown 0.85–1.00).
DAMAGE_RANDOM_RANGE = (0.85, 1.0)
# Bonus por mismo tipo del atacante (STAB).
STAB_MULTIPLIER = 1.5
# Daño mínimo de un movimiento que sí golpeó.
MIN_DAMAGE = 1
# Nivel virtual de los Pokémon (estiliza HP). 1 nivel → HP_max ≈ 2*HP_base + 110.
LEVEL = 50

# Si tus carpetas tienen el front en (1).gif y el back en .gif, pon True.
SWAP_FRONT_BACK = False

# ─── Interfaz ─────────────────────────────────────────────────────────────────
WINDOW_TITLE = "POKEFISI"
WINDOW_W = 960
WINDOW_H = 640
FPS = 60

# Paleta estilo Pokémon Gen 3
COLOR_BG          = (248, 248, 248)
COLOR_BG_BATTLE   = (224, 240, 232)
COLOR_TEXT        = ( 32,  32,  32)
COLOR_TEXT_LIGHT  = (248, 248, 248)
COLOR_BOX         = (248, 232, 200)
COLOR_BOX_BORDER  = ( 96,  72,  56)
COLOR_HP_HIGH     = ( 96, 200,  96)
COLOR_HP_MID      = (240, 200,  64)
COLOR_HP_LOW      = (224,  64,  64)
COLOR_BUTTON      = (240, 240, 248)
COLOR_BUTTON_SEL  = (255, 200,  64)
COLOR_ACCENT      = ( 56, 104, 200)

TEXT_SPEED_CPS = 60       # caracteres por segundo del typewriter
HP_BAR_DRAIN_PER_S = 80   # px/s al vaciar la barra
SCENE_FADE_MS = 400

# ─── Audio ────────────────────────────────────────────────────────────────────
MUSIC_VOLUME = 0.35
SFX_VOLUME = 0.55

# ─── Misc ─────────────────────────────────────────────────────────────────────
RNG_SEED = None  # fija un entero para reproducibilidad en experimentos
