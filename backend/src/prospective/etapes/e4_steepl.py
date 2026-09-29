"""Étape 4 : qualification STEEPL."""

import asyncio
from typing import Literal

from pydantic import BaseModel, field_validator

from prospective import llm
from prospective.etapes.base import Etape, Generation, lien_source
from prospective.etapes.e2_collecte import sources_des_signaux
from prospective.modeles import LIBELLES_AXES, Axe, Signal
from prospective.prompts import formater_signaux, messages_etape
from prospective.session import Session, Source

Categorie = Literal["signal_faible", "tendance_lourde", "incertitude"]
Origine = Literal["collecte", "entretiens", "ia"]

LIBELLES_CATEGORIES = {
    "signal_faible": "Signal faible",
    "tendance_lourde": "Tendance lourde",
    "incertitude": "Incertitude",
}


def borner(valeur: int) -> int:
    return max(1, min(5, int(valeur)))


class ElementExtrait(BaseModel):
    ref: str | None
    origine: Origine
    titre: str
    description: str
    axe: Axe
    categorie: Categorie
    impact: int
    incertitude: int
    justification: str


class Qualification(BaseModel):
    elements: list[ElementExtrait]


class ElementQualifie(BaseModel):
    id: str
    titre: str
    description: str
    axe: Axe
    categorie: Categorie
    impact: int
    incertitude: int
    justification: str
    origine: Origine
    ref_signal: str | None = None
    source: str | None = None
    url: str | None = None
    date: str | None = None
    hypothese_ia: bool = False

    @field_validator("impact", "incertitude")
    @classmethod
    def _borner(cls, v: int) -> int:
        return borner(v)


class LivrableSteepl(BaseModel):
    elements: list[ElementQualifie]


TACHE = """Qualifie la matière retenue (signaux de l'étape 2 et enseignements des entretiens
simulés de l'étape 3) en {nombre} éléments prospectifs. Chaque élément est :
- un signal faible : émergent, peu visible, potentiellement structurant ;
- une tendance lourde : installée, prévisible, forte inertie ;
- ou une incertitude : issue ouverte, fort impact possible.
Pour chaque élément :
- ref : l'identifiant du signal source (ex. « s04 ») s'il vient de la collecte, sinon null ;
- origine : « collecte », « entretiens » ou « ia » (déduction de ta part, sans donnée) ;
- titre, description (une phrase, orientée vers {horizon}) ;
- axe STEEPL, categorie ;
- impact sur le projet de 1 (faible) à 5 (majeur) et incertitude de 1 (quasi certain) à 5 (totalement ouvert) ;
- justification des scores en 15 mots au plus.
Regroupe les signaux qui décrivent le même phénomène. Identifie au moins
2 incertitudes à fort impact : elles serviront à construire les scénarios."""


class EtapeSteepl(Etape):
    numero = 4
    titre = "Qualification STEEPL"
    fichier = "04-steepl"
    modele = LivrableSteepl

    async def generer(self, gen: Generation) -> LivrableSteepl:
        session = gen.session
        signaux = [Signal(**s) for s in session.livrable(2)["signaux"]]
        synthese = session.livrable(3)["synthese"]
        entretiens = "\n".join(
            [
                "Attentes majeures : " + " ; ".join(synthese["attentes_majeures"]),
                "Irritants : " + " ; ".join(synthese["irritants"]),
                "Usages émergents : " + " ; ".join(synthese["usages_emergents"]),
                "Enseignements : " + " ; ".join(synthese["enseignements"]),
            ]
        )
        # Deux qualifications parallèles, par groupes d'axes : sorties plus courtes, donc
        # plus rapides ; les enseignements des entretiens vont au groupe social
        groupes = [
            ({Axe.S, Axe.T, Axe.E1}, "Social, Technologique, Économique", True),
            ({Axe.E2, Axe.P, Axe.L}, "Environnemental, Politique, Légal", False),
        ]

        async def qualifier(axes: set[Axe], libelle: str, avec_entretiens: bool):
            retenus = [s for s in signaux if s.axe in axes]
            resultat = await llm.generer_structure(
                Qualification,
                messages_etape(
                    session,
                    tache=TACHE.format(
                        horizon=session.saisie.horizon,
                        nombre="4 à 7" if gen.demo else "7 à 12",
                    )
                    + f"\nTraite uniquement les axes {libelle}.",
                    nom_outil="qualification_steepl",
                    acquis=(
                        [("Synthèse des entretiens simulés (étape 3)", entretiens)]
                        if avec_entretiens
                        else None
                    ),
                    donnees="Signaux retenus (étape 2) :\n" + formater_signaux(retenus),
                    consigne=gen.consigne,
                    version_precedente=gen.version_precedente,
                ),
                nom_outil="qualification_steepl",
                description="Enregistre les éléments qualifiés STEEPL.",
                max_tokens=8_000,
                rapide=gen.demo,
            )
            return resultat.elements

        lots = await asyncio.gather(*(qualifier(*g) for g in groupes))
        par_id = {s.id: s for s in signaux if s.retenu}
        elements = []
        for i, ext in enumerate((e for lot in lots for e in lot), start=1):
            element = ElementQualifie(
                id=f"q{i:02d}",
                **ext.model_dump(exclude={"ref"}),
            )
            signal = par_id.get(ext.ref or "")
            if signal and not signal.hypothese_ia:
                element.ref_signal = signal.id
                element.source, element.url, element.date = signal.source, signal.url, signal.date
                element.origine = "collecte"
            elif ext.origine == "entretiens":
                element.source = "Entretiens simulés par IA (étape 3)"
                element.hypothese_ia = True
            else:
                element.origine = "ia" if not signal else element.origine
                element.hypothese_ia = True
            elements.append(element)
        return LivrableSteepl(elements=elements)

    def markdown(self, livrable: LivrableSteepl, session: Session) -> str:
        blocs = []
        for axe in Axe:
            lignes = [
                f"| {e.id} | {e.titre} | {LIBELLES_CATEGORIES[e.categorie]} | {e.impact} | "
                f"{e.incertitude} | {e.justification} | "
                f"{lien_source(e.source, e.url, e.date) if not e.hypothese_ia or e.source else 'hypothèse IA'} |"
                for e in livrable.elements
                if e.axe == axe
            ]
            if lignes:
                blocs.append(
                    f"### {LIBELLES_AXES[axe]}\n\n"
                    "| Id | Élément | Catégorie | Impact | Incertitude | Justification | Source |\n"
                    "|---|---|---|---|---|---|---|\n" + "\n".join(lignes)
                )
        critiques = sorted(
            (e for e in livrable.elements if e.categorie == "incertitude"),
            key=lambda e: e.impact * e.incertitude,
            reverse=True,
        )[:4]
        blocs.append(
            "### Incertitudes critiques (impact × incertitude)\n\n"
            + "\n".join(
                f"- {e.id} {e.titre} : {e.impact} × {e.incertitude} = {e.impact * e.incertitude}"
                for e in critiques
            )
        )
        return "\n\n".join(blocs)

    def sources(self, livrable: LivrableSteepl) -> list[Source]:
        return sources_des_signaux(
            [
                Signal(
                    id=e.id,
                    titre=e.titre,
                    resume="",
                    axe=e.axe,
                    source=e.source,
                    url=e.url,
                    date=e.date,
                )
                for e in livrable.elements
                if e.url
            ]
        )
