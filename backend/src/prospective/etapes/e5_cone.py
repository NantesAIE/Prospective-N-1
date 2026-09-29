"""Étape 5 : cône des futurs."""

from typing import Literal

from pydantic import BaseModel, field_validator

from prospective import llm
from prospective.etapes.base import Etape, Generation
from prospective.etapes.e4_steepl import LIBELLES_CATEGORIES, ElementQualifie
from prospective.modeles import LIBELLES_AXES
from prospective.prompts import messages_etape
from prospective.session import Session

Zone = Literal["probable", "plausible", "possible", "souhaitable"]
JALONS = (2030, 2035, 2040)

LIBELLES_ZONES = {
    "probable": "Probable",
    "plausible": "Plausible",
    "possible": "Possible",
    "souhaitable": "Souhaitable",
}


def jalon_proche(annee: int) -> int:
    return min(JALONS, key=lambda j: abs(j - annee))


class PositionExtraite(BaseModel):
    element_id: str
    zone: Zone
    jalon: int
    commentaire: str


class DescriptionZone(BaseModel):
    zone: Zone
    description: str


class ConeExtrait(BaseModel):
    zones: list[DescriptionZone]
    positions: list[PositionExtraite]


class Position(BaseModel):
    element_id: str
    titre: str
    categorie: str
    axe: str
    zone: Zone
    jalon: int
    commentaire: str

    @field_validator("jalon")
    @classmethod
    def _jalon(cls, v: int) -> int:
        return jalon_proche(v)


class LivrableCone(BaseModel):
    zones: list[DescriptionZone]
    positions: list[Position]


TACHE = """Positionne chaque élément qualifié à l'étape 4 dans le cône des futurs, d'aujourd'hui
à {horizon} :
- probable : ce qui adviendra si les tendances actuelles se prolongent ;
- plausible : ce qui pourrait advenir compte tenu des connaissances actuelles ;
- possible : ce qui pourrait advenir, même improbable (ruptures, jokers) ;
- souhaitable : ce qui serait favorable au projet de l'entrepreneur, quelle que soit la probabilité.
Pour chaque élément (element_id = identifiant qN) : la zone, le jalon (2030, 2035 ou 2040)
où son effet devient visible, et un commentaire d'une phrase.
Décris aussi en 1 à 2 phrases chacune des quatre zones du cône pour ce projet (zones)."""


class EtapeCone(Etape):
    numero = 5
    titre = "Cône des futurs"
    fichier = "05-cone-des-futurs"
    modele = LivrableCone

    async def generer(self, gen: Generation) -> LivrableCone:
        session = gen.session
        elements = [ElementQualifie(**e) for e in session.livrable(4)["elements"]]
        donnees = "\n".join(
            f"[{e.id}] ({LIBELLES_CATEGORIES[e.categorie]}, {LIBELLES_AXES[e.axe]}, "
            f"impact {e.impact}, incertitude {e.incertitude}) {e.titre} : {e.description}"
            for e in elements
        )
        extrait = await llm.generer_structure(
            ConeExtrait,
            messages_etape(
                session,
                tache=TACHE.format(horizon=session.saisie.horizon),
                nom_outil="cone_des_futurs",
                donnees="Éléments qualifiés (étape 4) :\n" + donnees,
                consigne=gen.consigne,
                version_precedente=gen.version_precedente,
            ),
            nom_outil="cone_des_futurs",
            description="Enregistre le positionnement des éléments dans le cône des futurs.",
            rapide=gen.demo,
        )
        par_id = {e.id: e for e in elements}
        positions = [
            Position(
                element_id=p.element_id,
                titre=par_id[p.element_id].titre,
                categorie=par_id[p.element_id].categorie,
                axe=par_id[p.element_id].axe,
                zone=p.zone,
                jalon=p.jalon,
                commentaire=p.commentaire,
            )
            for p in extrait.positions
            if p.element_id in par_id
        ]
        return LivrableCone(zones=extrait.zones, positions=positions)

    def markdown(self, livrable: LivrableCone, session: Session) -> str:
        blocs = []
        descriptions = {z.zone: z.description for z in livrable.zones}
        for zone, libelle in LIBELLES_ZONES.items():
            lignes = [
                f"| {p.jalon} | {p.element_id} | {p.titre} | {p.commentaire} |"
                for p in sorted(livrable.positions, key=lambda p: p.jalon)
                if p.zone == zone
            ]
            blocs.append(
                f"### Futurs {libelle.lower()}s\n\n{descriptions.get(zone, '')}\n\n"
                + (
                    "| Jalon | Id | Élément | Commentaire |\n|---|---|---|---|\n"
                    + "\n".join(lignes)
                    if lignes
                    else "Aucun élément."
                )
            )
        return "\n\n".join(blocs)
