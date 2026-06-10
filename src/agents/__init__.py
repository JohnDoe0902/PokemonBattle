from .base_agent import Agent
from .random_agent import RandomAgent
from .heuristic_agent import HeuristicAgent
from .human_agent import HumanAgent
#AGREGADO Inicio
from .minimax_agent import MinimaxAgent
#AGREGADO Fin

#AGREGADO Inicio (MinimaxAgent añadido a la API pública del paquete)
__all__ = ["Agent", "RandomAgent", "HeuristicAgent", "HumanAgent", "MinimaxAgent"]
#AGREGADO Fin
