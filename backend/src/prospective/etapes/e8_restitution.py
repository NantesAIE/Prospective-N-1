"""Étape 8 : restitution, narratif et artefact de design fiction."""

import asyncio
from typing import Literal

from pydantic import BaseModel

from prospective import llm
from prospective.etapes.base import Etape, Generation, puces
from prospective.etapes.e6_scenarios import LivrableScenarios
from prospective.prompts import messages_etape
from prospective.session import ErreurSession, Session

FormatArtefact = Literal[
    "une_de_presse", "publicite", "fiche_produit", "avis_client", "offre_emploi", "notification"
]
FORMATS: dict[str, str] = {
    "une_de_presse": "une de presse locale datée de {horizon}",
    "publicite": "publicité",
    "fiche_produit": "fiche produit",
    "avis_client": "avis client",
    "offre_emploi": "offre d'emploi",
    "notification": "notification d'application",
}

TypeBloc = Literal[
    "surtitre", "titre", "chapo", "paragraphe", "encadre", "citation", "liste", "prix", "mention"
]


class Bloc(BaseModel):
    type: TypeBloc
    texte: str


class Artefact(BaseModel):
    format: FormatArtefact
    media: str
    date_fictive: str
    titre: str
    blocs: list[Bloc]


class Narratif(BaseModel):
    titre: str
    texte: str


class LivrableRestitution(BaseModel):
    narratif: Narratif
    artefact: Artefact
    synthese_executive: str


class RecitSynthese(BaseModel):
    narratif: Narratif
    synthese_executive: str


class ObjetFutur(BaseModel):
    artefact: Artefact


TACHE_RECIT = """Rends tangible le scénario visé « {cible.titre} ».
1. narratif : le récit d'une journée type en {horizon} dans ce scénario, du point de vue d'un
   client du business ({mots} mots, au présent, sensoriel et concret, avec un titre).
2. synthese_executive : 120 à 180 mots qui résument le dossier : le scénario visé, pourquoi,
   la trajectoire et les trois premières actions.
Le narratif est une fiction assumée : n'y cite aucune source réelle."""

TACHE_ARTEFACT = """Rends tangible le scénario visé « {cible.titre} » par un objet venu du futur
au format « {format} », daté de {horizon} (artefact) :
- media : le nom du support (journal local, marque, application...), inventé mais crédible ;
- date_fictive : la date affichée sur l'objet, en {horizon} ;
- titre : le titre principal ;
- blocs : le contenu, dans l'ordre d'affichage, avec les types adaptés au format (surtitre,
  titre, chapo, paragraphe, encadre, citation, liste, prix, mention) ; {blocs} blocs.
L'objet doit être plausible, précis, et intégrer des éléments des signaux et de la roadmap.
C'est une fiction assumée : n'y cite aucune source réelle."""


class EtapeRestitution(Etape):
    numero = 8
    titre = "Restitution et design fiction"
    fichier = "08-restitution"
    modele = LivrableRestitution

    async def generer(self, gen: Generation) -> LivrableRestitution:
        session = gen.session
        scenarios = LivrableScenarios(**session.livrable(6))
        cible = scenarios.scenario(scenarios.choix.cible)
        if cible is None:
            raise ErreurSession("Aucun scénario visé n'a été choisi à l'étape 6.")
        roadmap = session.livrable(7)
        format_artefact = gen.options.get("format_artefact", "une_de_presse")
        if format_artefact not in FORMATS:
            format_artefact = "une_de_presse"
        horizon = session.saisie.horizon
        jalons = "\n".join(
            f"- {j['horizon']} : {j['objectif']} ({'; '.join(j['actions'])})"
            for j in roadmap["jalons"]
        )
        acquis = [
            ("Scénario visé (étape 6)", f"{cible.titre}\n{cible.recit}"),
            ("Impact business (étape 7)", roadmap["impact"]["offre"]),
            ("Roadmap (étape 7)", jalons),
        ]

        # Deux appels parallèles : récit et synthèse d'un côté, artefact de l'autre
        recit, objet = await asyncio.gather(
            llm.generer_structure(
                RecitSynthese,
                messages_etape(
                    session,
                    tache=TACHE_RECIT.format(
                        cible=cible, horizon=horizon, mots="200 à 250" if gen.demo else "400 à 500"
                    ),
                    nom_outil="recit",
                    acquis=acquis,
                    consigne=gen.consigne,
                    version_precedente=gen.version_precedente,
                ),
                nom_outil="recit",
                description="Enregistre le narratif et la synthèse exécutive.",
                rapide=gen.demo,
                max_tokens=5_000,
            ),
            llm.generer_structure(
                ObjetFutur,
                messages_etape(
                    session,
                    tache=TACHE_ARTEFACT.format(
                        cible=cible,
                        horizon=horizon,
                        format=FORMATS[format_artefact].format(horizon=horizon),
                        blocs="6 à 8" if gen.demo else "8 à 12",
                    ),
                    nom_outil="artefact",
                    acquis=acquis,
                    consigne=gen.consigne,
                ),
                nom_outil="artefact",
                description="Enregistre l'artefact de design fiction.",
                rapide=gen.demo,
                max_tokens=5_000,
            ),
        )
        objet.artefact.format = format_artefact
        return LivrableRestitution(
            narratif=recit.narratif,
            artefact=objet.artefact,
            synthese_executive=recit.synthese_executive,
        )

    def markdown(self, livrable: LivrableRestitution, session: Session) -> str:
        a = livrable.artefact
        contenu = []
        for b in a.blocs:
            match b.type:
                case "titre":
                    contenu.append(f"#### {b.texte}")
                case "surtitre" | "mention":
                    contenu.append(f"*{b.texte}*")
                case "chapo":
                    contenu.append(f"**{b.texte}**")
                case "citation" | "encadre":
                    contenu.append(f"> {b.texte}")
                case "liste":
                    contenu.append(
                        puces([l.strip("-• ") for l in b.texte.splitlines() if l.strip()])
                    )
                case _:
                    contenu.append(b.texte)
        return "\n\n".join(
            [
                f"### Synthèse exécutive\n\n{livrable.synthese_executive}",
                f"### {livrable.narratif.titre}\n\n{livrable.narratif.texte}",
                f"### Artefact de design fiction : {FORMATS[a.format].format(horizon=session.saisie.horizon)}",
                f"**{a.media}**, {a.date_fictive}\n\n### {a.titre}\n\n" + "\n\n".join(contenu),
                "> *Fiction prospective générée par IA.*",
            ]
        )
