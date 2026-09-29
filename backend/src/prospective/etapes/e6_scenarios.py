"""Étape 6 : scénarios 2040, « où tu veux aller »."""

import asyncio
from typing import Any, Literal

from pydantic import BaseModel

from prospective import llm
from prospective.etapes.base import Etape, Generation, puces
from prospective.etapes.e4_steepl import LIBELLES_CATEGORIES, ElementQualifie
from prospective.prompts import messages_etape
from prospective.session import ErreurSession, Session

Quadrant = Literal["++", "+-", "-+", "--"]
QUADRANTS: tuple[Quadrant, ...] = ("++", "+-", "-+", "--")


class AxeScenario(BaseModel):
    element_id: str
    intitule: str
    pole_moins: str
    pole_plus: str


class Scenario(BaseModel):
    quadrant: Quadrant
    titre: str
    recit: str
    elements_menants: list[str]
    conditions_bascule: list[str]
    implication_projet: str


class ScenariosExtraits(BaseModel):
    axe_x: AxeScenario
    axe_y: AxeScenario
    scenarios: list[Scenario]


class Choix(BaseModel):
    cible: Quadrant | None = None
    vigilance: Quadrant | None = None


class LivrableScenarios(ScenariosExtraits):
    choix: Choix = Choix()

    def scenario(self, quadrant: str | None) -> Scenario | None:
        return next((s for s in self.scenarios if s.quadrant == quadrant), None)


class Axes(BaseModel):
    axe_x: AxeScenario
    axe_y: AxeScenario


class ScenarioRedige(BaseModel):
    titre: str
    recit: str
    elements_menants: list[str]
    conditions_bascule: list[str]
    implication_projet: str


TACHE_AXES = """Prépare une matrice 2x2 de scénarios à l'horizon {horizon} à partir des deux
incertitudes critiques suivantes :
- axe X : [{x.id}] {x.titre} : {x.description}
- axe Y : [{y.id}] {y.titre} : {y.description}
Pour chaque axe (element_id = identifiant qN), nomme l'incertitude en quelques mots (intitule)
et décris ses deux pôles contrastés en une courte phrase chacun (pole_moins, pole_plus)."""

TACHE_SCENARIO = """Rédige le scénario à l'horizon {horizon} du quadrant « {quadrant} » de la matrice :
- axe X, {x.intitule} : {pole_x} ;
- axe Y, {y.intitule} : {pole_y}.
Les trois autres quadrants sont traités à part : reste strictement dans cette combinaison.
- titre évocateur ;
- recit : environ {mots} mots, au présent, décrivant le monde en {horizon} sur le territoire ;
- elements_menants : identifiants qN des signaux et tendances qui y mènent ;
- conditions_bascule : 2 à 3 événements qui feraient basculer vers ce scénario ;
- implication_projet : ce que ce futur signifie pour le projet, en deux phrases.
Le scénario doit être plausible et cohérent avec les tendances lourdes."""


def incertitudes_critiques(elements: list[ElementQualifie]) -> list[ElementQualifie]:
    """Éléments triés par criticité (impact × incertitude), incertitudes en premier."""
    return sorted(
        elements,
        key=lambda e: (e.categorie == "incertitude", e.impact * e.incertitude, e.impact),
        reverse=True,
    )


class EtapeScenarios(Etape):
    numero = 6
    titre = "Scénarios 2040"
    fichier = "06-scenarios"
    modele = LivrableScenarios

    async def generer(self, gen: Generation) -> LivrableScenarios:
        session = gen.session
        elements = [ElementQualifie(**e) for e in session.livrable(4)["elements"]]
        par_id = {e.id: e for e in elements}
        choisis = [i for i in gen.options.get("incertitudes", []) if i in par_id]
        if len(choisis) != 2 or choisis[0] == choisis[1]:
            choisis = [e.id for e in incertitudes_critiques(elements)[:2]]
        x, y = par_id[choisis[0]], par_id[choisis[1]]

        cone = session.livrable(5)
        donnees = "\n".join(
            f"[{e.id}] ({LIBELLES_CATEGORIES[e.categorie]}, impact {e.impact}, "
            f"incertitude {e.incertitude}) {e.titre} : {e.description}"
            for e in elements
        )
        zones = "\n".join(f"- {z['zone']} : {z['description']}" for z in cone["zones"])
        acquis = [("Cône des futurs (étape 5)", zones)]
        donnees = "Éléments qualifiés (étape 4) :\n" + donnees
        axes = await llm.generer_structure(
            Axes,
            messages_etape(
                session,
                tache=TACHE_AXES.format(horizon=session.saisie.horizon, x=x, y=y),
                nom_outil="axes",
                donnees=donnees,
                consigne=gen.consigne,
            ),
            nom_outil="axes",
            description="Enregistre les deux axes de la matrice et leurs pôles.",
            rapide=True,
            max_tokens=3_000,
        )
        axes.axe_x.element_id, axes.axe_y.element_id = x.id, y.id

        # Un appel par quadrant, en parallèle
        async def rediger(quadrant: Quadrant) -> Scenario:
            ax, ay = axes.axe_x, axes.axe_y
            redige = await llm.generer_structure(
                ScenarioRedige,
                messages_etape(
                    session,
                    tache=TACHE_SCENARIO.format(
                        horizon=session.saisie.horizon,
                        quadrant=quadrant,
                        x=ax,
                        y=ay,
                        pole_x=ax.pole_plus if quadrant[0] == "+" else ax.pole_moins,
                        pole_y=ay.pole_plus if quadrant[1] == "+" else ay.pole_moins,
                        mots=80 if gen.demo else 150,
                    ),
                    nom_outil="scenario",
                    acquis=acquis,
                    donnees=donnees,
                    consigne=gen.consigne,
                    version_precedente=gen.version_precedente,
                ),
                nom_outil="scenario",
                description="Enregistre le scénario du quadrant.",
                rapide=gen.demo,
                max_tokens=4_000,
            )
            return Scenario(quadrant=quadrant, **redige.model_dump())

        scenarios = await asyncio.gather(*(rediger(q) for q in QUADRANTS))
        return LivrableScenarios(axe_x=axes.axe_x, axe_y=axes.axe_y, scenarios=list(scenarios))

    def avant_validation(
        self, livrable: LivrableScenarios, options: dict[str, Any]
    ) -> LivrableScenarios:
        choix = Choix(**{**livrable.choix.model_dump(), **options.get("choix", {})})
        if choix.cible is None:
            raise ErreurSession("Choisissez le scénario visé avant de valider.")
        if choix.vigilance == choix.cible:
            choix.vigilance = None
        livrable.choix = choix
        return livrable

    def markdown(self, livrable: LivrableScenarios, session: Session) -> str:
        x, y = livrable.axe_x, livrable.axe_y
        blocs = [
            f"**Axe X** : {x.intitule} ({x.element_id}), de « {x.pole_moins} » à « {x.pole_plus} »",
            f"**Axe Y** : {y.intitule} ({y.element_id}), de « {y.pole_moins} » à « {y.pole_plus} »",
        ]
        cible = livrable.scenario(livrable.choix.cible)
        vigilance = livrable.scenario(livrable.choix.vigilance)
        if cible:
            blocs.append(f"**Scénario visé (« où tu veux aller »)** : {cible.titre}")
        if vigilance:
            blocs.append(f"**Scénario de vigilance** : {vigilance.titre}")
        for s in livrable.scenarios:
            role = " (visé)" if s is cible else " (vigilance)" if s is vigilance else ""
            blocs.append(
                f"### {s.quadrant} {s.titre}{role}\n\n{s.recit}\n\n"
                f"**Implication pour le projet** : {s.implication_projet}\n\n"
                f"**Signaux et tendances qui y mènent** : {', '.join(s.elements_menants)}\n\n"
                "**Conditions de bascule**\n\n" + puces(s.conditions_bascule)
            )
        return "\n\n".join(blocs)
