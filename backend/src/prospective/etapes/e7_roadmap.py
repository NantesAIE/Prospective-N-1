"""Étape 7 : impact business et roadmap stratégique par backcasting."""

import asyncio
from typing import Literal

from pydantic import BaseModel, field_validator

from prospective import llm
from prospective.etapes.base import Etape, Generation, puces
from prospective.etapes.e4_steepl import borner
from prospective.etapes.e6_scenarios import LivrableScenarios
from prospective.flux import CATALOGUE
from prospective.prompts import messages_etape
from prospective.session import ErreurSession, Session

Horizon = Literal["2040", "2035", "2030", "18 mois", "90 jours"]


class ImpactBusiness(BaseModel):
    offre: str
    clients: str
    modele_economique: str
    risques: list[str]
    opportunites: list[str]


class Robustesse(BaseModel):
    quadrant: str
    titre_scenario: str
    score: int
    commentaire: str

    @field_validator("score")
    @classmethod
    def _borner(cls, v: int) -> int:
        return borner(v)


class Jalon(BaseModel):
    horizon: Horizon
    objectif: str
    actions: list[str]


class Indicateur(BaseModel):
    indicateur: str
    ce_qui_alerte: str
    source_suivi: str
    flux_id: str | None
    hypothese_ia: bool


class PariSansRegret(BaseModel):
    action: str
    justification: str


class LivrableRoadmap(BaseModel):
    impact: ImpactBusiness
    robustesse: list[Robustesse]
    jalons: list[Jalon]
    signaux_a_surveiller: list[Indicateur]
    paris_sans_regret: list[PariSansRegret]


class ImpactRobustesse(BaseModel):
    impact: ImpactBusiness
    robustesse: list[Robustesse]


class Trajectoire(BaseModel):
    jalons: list[Jalon]
    signaux_a_surveiller: list[Indicateur]
    paris_sans_regret: list[PariSansRegret]


CONTEXTE = """Le scénario visé par l'entrepreneur est « {cible.titre} » ({cible.quadrant}).
{vigilance}"""

TACHE_IMPACT = """1. impact : ce que devient le projet dans ce scénario (offre, clients, modèle
   économique, en 2 à 3 phrases chacun), avec {n} risques et {n} opportunités.
2. robustesse : pour chacun des 3 autres scénarios, un score de 1 (le projet ne tient pas)
   à 5 (le projet prospère) et un commentaire d'une phrase."""

TACHE_TRAJECTOIRE = """1. jalons : roadmap par backcasting, du scénario {horizon} vers aujourd'hui, avec
   exactement 5 jalons dans cet ordre : « 2040 », « 2035 », « 2030 », « 18 mois », « 90 jours ».
   Chaque jalon a un objectif et {actions} actions concrètes ; les actions à 90 jours sont
   immédiatement actionnables par l'entrepreneur.
2. signaux_a_surveiller : exactement 5 indicateurs avancés, avec ce qui doit alerter
   (seuil ou tendance) et la source de suivi. Si la source est l'un des flux du catalogue,
   renseigne flux_id ; sinon flux_id null. hypothese_ia vaut true si l'indicateur ne s'appuie
   sur aucune donnée collectée.
3. paris_sans_regret : {paris} actions valables dans les 4 scénarios, avec leur justification."""


class EtapeRoadmap(Etape):
    numero = 7
    titre = "Impact business et roadmap"
    fichier = "07-roadmap"
    modele = LivrableRoadmap

    async def generer(self, gen: Generation) -> LivrableRoadmap:
        session = gen.session
        scenarios = LivrableScenarios(**session.livrable(6))
        cible = scenarios.scenario(scenarios.choix.cible)
        if cible is None:
            raise ErreurSession("Aucun scénario visé n'a été choisi à l'étape 6.")
        vigilance = scenarios.scenario(scenarios.choix.vigilance)
        contexte = CONTEXTE.format(
            cible=cible,
            vigilance=(
                f"Le scénario de vigilance est « {vigilance.titre} » : les signaux à surveiller "
                "doivent permettre de détecter tôt une bascule vers ce futur."
                if vigilance
                else ""
            ),
        )
        recits = "\n\n".join(
            f"### {s.quadrant} {s.titre}\n{s.recit}\nConditions de bascule : "
            + " ; ".join(s.conditions_bascule)
            for s in scenarios.scenarios
        )
        acquis = [
            (
                "Axes des scénarios (étape 6)",
                f"X : {scenarios.axe_x.intitule} ; Y : {scenarios.axe_y.intitule}",
            ),
            ("Scénarios (étape 6)", recits),
        ]
        catalogue = "\n".join(f"- {f.id} : {f.nom}" for f in CATALOGUE)

        # Deux appels parallèles : impact et robustesse d'un côté, trajectoire de l'autre
        impact, trajectoire = await asyncio.gather(
            llm.generer_structure(
                ImpactRobustesse,
                messages_etape(
                    session,
                    tache=contexte + TACHE_IMPACT.format(n="3" if gen.demo else "3 à 5"),
                    nom_outil="impact",
                    acquis=acquis,
                    consigne=gen.consigne,
                    version_precedente=gen.version_precedente,
                ),
                nom_outil="impact",
                description="Enregistre l'impact business et la robustesse du projet.",
                rapide=gen.demo,
                max_tokens=6_000,
            ),
            llm.generer_structure(
                Trajectoire,
                messages_etape(
                    session,
                    tache=contexte
                    + TACHE_TRAJECTOIRE.format(
                        horizon=session.saisie.horizon,
                        actions="2" if gen.demo else "2 à 4",
                        paris="3" if gen.demo else "3 à 5",
                    ),
                    nom_outil="trajectoire",
                    acquis=acquis,
                    donnees="Catalogue des flux de suivi disponibles :\n" + catalogue,
                    consigne=gen.consigne,
                    version_precedente=gen.version_precedente,
                ),
                nom_outil="trajectoire",
                description="Enregistre la roadmap, les signaux à surveiller et les paris.",
                rapide=gen.demo,
                max_tokens=6_000,
            ),
        )
        livrable = LivrableRoadmap(**impact.model_dump(), **trajectoire.model_dump())
        ids_flux = {f.id for f in CATALOGUE}
        for indicateur in livrable.signaux_a_surveiller:
            if indicateur.flux_id not in ids_flux:
                indicateur.flux_id = None
        return livrable

    def markdown(self, livrable: LivrableRoadmap, session: Session) -> str:
        i = livrable.impact
        robustesse = "\n".join(
            f"| {r.quadrant} {r.titre_scenario} | {r.score}/5 | {r.commentaire} |"
            for r in livrable.robustesse
        )
        jalons = "\n\n".join(
            f"**{j.horizon}** : {j.objectif}\n\n" + puces(j.actions) for j in livrable.jalons
        )
        indicateurs = "\n".join(
            f"| {s.indicateur} | {s.ce_qui_alerte} | {s.source_suivi}"
            f"{' (hypothèse IA)' if s.hypothese_ia else ''} |"
            for s in livrable.signaux_a_surveiller
        )
        paris = "\n".join(
            f"- **{p.action}** : {p.justification}" for p in livrable.paris_sans_regret
        )
        return "\n\n".join(
            [
                "### Impact business dans le scénario visé",
                f"**Offre** : {i.offre}",
                f"**Clients** : {i.clients}",
                f"**Modèle économique** : {i.modele_economique}",
                "**Risques**\n\n" + puces(i.risques),
                "**Opportunités**\n\n" + puces(i.opportunites),
                "### Robustesse dans les autres scénarios\n\n"
                "| Scénario | Score | Commentaire |\n|---|---|---|\n" + robustesse,
                "### Roadmap par backcasting\n\n" + jalons,
                "### Signaux à surveiller\n\n"
                "| Indicateur | Ce qui doit alerter | Source de suivi |\n|---|---|---|\n"
                + indicateurs,
                "### Paris sans regret\n\n" + paris,
            ]
        )
