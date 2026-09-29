"""Registre des 9 étapes du parcours."""

from prospective.etapes.base import Etape, Generation
from prospective.etapes.e0_contexte import EtapeContexte
from prospective.etapes.e1_flux import EtapeFlux
from prospective.etapes.e2_collecte import EtapeCollecte
from prospective.etapes.e3_entretiens import EtapeEntretiens
from prospective.etapes.e4_steepl import EtapeSteepl
from prospective.etapes.e5_cone import EtapeCone
from prospective.etapes.e6_scenarios import EtapeScenarios
from prospective.etapes.e7_roadmap import EtapeRoadmap
from prospective.etapes.e8_restitution import EtapeRestitution

ETAPES: list[Etape] = [
    EtapeContexte(),
    EtapeFlux(),
    EtapeCollecte(),
    EtapeEntretiens(),
    EtapeSteepl(),
    EtapeCone(),
    EtapeScenarios(),
    EtapeRoadmap(),
    EtapeRestitution(),
]

__all__ = ["ETAPES", "Etape", "Generation"]
