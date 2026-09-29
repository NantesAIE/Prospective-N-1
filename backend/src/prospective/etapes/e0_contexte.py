"""Étape 0 : strong context et user context."""

from pydantic import BaseModel

from prospective import llm
from prospective.etapes.base import Etape, Generation, puces
from prospective.flux import geocoder
from prospective.modeles import ContexteUtilisateur, Localisation
from prospective.prompts import messages_etape
from prospective.session import Session


class FicheContexte(BaseModel):
    probleme: str
    cible: str
    proposition_valeur: str
    territoire: str
    hypotheses_implicites: list[str]
    questions_ouvertes: list[str]
    mots_cles: list[str]
    mots_cles_en: list[str]
    codes_naf: list[str]


class LivrableContexte(BaseModel):
    fiche: FicheContexte
    localisation: Localisation


TACHE = """Reformule le projet en une fiche contexte structurée :
- probleme : le problème ou besoin adressé, en deux phrases au plus ;
- cible : les clients visés, segmentés si utile ;
- proposition_valeur : la proposition de valeur pressentie ;
- territoire : le territoire d'implantation et ses spécificités connues, à partir de la localisation fournie ;
- hypotheses_implicites : 3 à 6 hypothèses que l'entrepreneur fait sans le dire (marché, usages, modèle économique) ;
- questions_ouvertes : 2 à 4 questions à clarifier avec l'entrepreneur ;
- mots_cles : 4 à 6 termes de recherche courts en français (1 à 3 mots chacun, sans nom de lieu),
  du plus central au plus périphérique, pour interroger la presse, les bases d'entreprises et la
  recherche (ex. « sport santé », « seniors ») ;
- mots_cles_en : les mêmes termes en anglais, pour les sources internationales ;
- codes_naf : 2 à 5 codes NAF rév. 2 (format « 93.13Z ») correspondant à l'activité et à ses concurrents directs.
Reste fidèle à ce qu'a écrit l'entrepreneur : reformule, n'invente pas de faits sur son projet."""


class EtapeContexte(Etape):
    numero = 0
    titre = "Strong context et user context"
    fichier = "00-contexte"
    modele = LivrableContexte

    async def generer(self, gen: Generation) -> LivrableContexte:
        localisation = await geocoder(gen.session.saisie)
        messages = messages_etape(
            gen.session,
            tache=TACHE,
            nom_outil="fiche_contexte",
            donnees=f"Géocodage de la localisation : {localisation.model_dump_json(exclude_none=True)}",
            consigne=gen.consigne,
            version_precedente=gen.version_precedente,
        )
        fiche = await llm.generer_structure(
            FicheContexte,
            messages,
            nom_outil="fiche_contexte",
            description="Enregistre la fiche contexte structurée du projet.",
            rapide=gen.demo,
        )
        gen.flux_utilises = ["geo"]
        return LivrableContexte(fiche=fiche, localisation=localisation)

    def markdown(self, livrable: LivrableContexte, session: Session) -> str:
        f, loc = livrable.fiche, livrable.localisation
        return "\n\n".join(
            [
                f"**Problème** : {f.probleme}",
                f"**Cible** : {f.cible}",
                f"**Proposition de valeur pressentie** : {f.proposition_valeur}",
                f"**Territoire** : {f.territoire}",
                "**Hypothèses implicites**\n\n" + puces(f.hypotheses_implicites),
                "**Questions ouvertes**\n\n" + puces(f.questions_ouvertes),
                f"**Mots-clés** : {', '.join(f.mots_cles)} ({', '.join(f.mots_cles_en)})",
                f"**Codes NAF** : {', '.join(f.codes_naf)}",
                "**Géocodage** : "
                + ", ".join(
                    str(v)
                    for v in [loc.ville, loc.code_postal, loc.departement, loc.region, loc.pays]
                    if v
                )
                + (f" (lat {loc.lat}, lon {loc.lon})" if loc.lat is not None else ""),
            ]
        )

    def apres_validation(self, livrable: LivrableContexte, session: Session) -> None:
        session.contexte = ContexteUtilisateur(
            saisie=session.saisie,
            localisation=livrable.localisation,
            mots_cles=livrable.fiche.mots_cles,
            mots_cles_en=livrable.fiche.mots_cles_en,
            codes_naf=livrable.fiche.codes_naf,
        )
