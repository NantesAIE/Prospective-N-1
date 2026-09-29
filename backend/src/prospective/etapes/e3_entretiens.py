"""Étape 3 : entretiens simulés.

Une base de 100 personas, tirée de la démographie réelle du territoire (sans appel au modèle),
sert de population de référence ; le modèle n'y ajoute que les usages, les attentes et
l'opinion. Seul un panel représentatif est interrogé (6 personas en mode démo, 15 en mode
complet), en parallèle de cet enrichissement : l'étape reste rapide. En mode démo, la base
n'est pas enrichie : seuls les personas du panel reçoivent une opinion.
"""

import asyncio
from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel

from prospective import llm
from prospective.etapes.base import Etape, Generation, puces
from prospective.etapes.base_personas import generer_base
from prospective.flux import profil_demographique
from prospective.modeles import Signal
from prospective.prompts import formater_signaux, messages_etape
from prospective.session import ErreurSession, Session, Source

MENTION = "Entretiens simulés par IA, à confirmer par de vrais entretiens terrain."
NB_PERSONAS = 100
TAILLE_PANEL = {True: 6, False: 15}  # clé : mode démo
PERSONAS_PAR_ENTRETIEN = 3
PERSONAS_PAR_ENRICHISSEMENT = 10

Opinion = Literal["tres_favorable", "favorable", "neutre", "reserve", "hostile"]
LIBELLES_OPINIONS = {
    "tres_favorable": "Très favorable",
    "favorable": "Favorable",
    "neutre": "Neutre",
    "reserve": "Réservé",
    "hostile": "Hostile",
}


class GuideEntretien(BaseModel):
    questions: list[str]


class Enrichissement(BaseModel):
    persona_id: str
    usages: str
    attentes: str
    opinion: Opinion


class LotEnrichi(BaseModel):
    personas: list[Enrichissement]


class Entretien(Enrichissement):
    reponses: list[str]


class Entretiens(BaseModel):
    entretiens: list[Entretien]


class PersonaEnregistre(BaseModel):
    id: str
    prenom: str
    age: int
    genre: str
    situation: str
    csp: str
    lieu_de_vie: str
    usages: str = ""
    attentes: str = ""
    opinion: Opinion | None = None  # inconnue si la base n'a pas été enrichie (mode démo)
    reponses: list[str] = []  # vide si le persona n'est pas dans le panel


class Verbatim(BaseModel):
    persona_id: str
    citation: str


class SyntheseEntretiens(BaseModel):
    attentes_majeures: list[str]
    irritants: list[str]
    usages_emergents: list[str]
    verbatims: list[Verbatim]
    enseignements: list[str]


class Repartition(BaseModel):
    opinion: Opinion
    nombre: int


class LivrableEntretiens(BaseModel):
    avertissement: str = MENTION
    guide: list[str]
    profil_demographique: str
    source_demographique: Source | None = None
    personas: list[PersonaEnregistre]
    panel: list[str] = []
    synthese: SyntheseEntretiens
    repartition: list[Repartition]


TACHE_GUIDE = """Rédige un guide d'entretien court de 5 questions ouvertes, destiné à des habitants
du territoire susceptibles d'être clients du projet. Les questions explorent les usages actuels,
les attentes, les freins, la disposition à payer et la vision de l'avenir à l'horizon {horizon}.
Formule-les simplement, sans jargon."""

TACHE_ENRICHISSEMENT = """Voici des habitants du territoire (profils tirés du recensement). Pour
chacun (persona_id identique), indique en 6 mots au plus ses usages actuels liés à la thématique,
en 6 mots au plus ses attentes, et son opinion globale sur le projet. Les opinions doivent être
réalistes et variées : beaucoup de personnes sont peu concernées, sceptiques ou contraintes par
leur budget."""

TACHE_ENTRETIENS = """Simule l'entretien des personas ci-dessous avec le guide fourni. Pour chacun
(persona_id identique) : ses usages actuels et ses attentes (6 mots au plus chacun), son opinion
globale sur le projet, puis une réponse par question, dans l'ordre, à la première personne, dans
un langage oral naturel ({longueur}), cohérente avec son âge, sa situation et sa CSP.
Pas de complaisance : fais entendre aussi les sceptiques et les personnes non concernées."""

TACHE_SYNTHESE = """Voici les réponses du panel représentatif interrogé, et la répartition des
opinions sur {nb} personas. Produis une synthèse :
- attentes_majeures : {n} attentes, de la plus à la moins partagée ;
- irritants : {n} freins ou irritants ;
- usages_emergents : {n_usages} usages émergents repérés ;
- verbatims : {nb_verbatims} citations représentatives, copiées mot pour mot des réponses, avec
  l'identifiant du persona (ex. p007), en couvrant la diversité des opinions ;
- enseignements : {n} enseignements pour la prospective du projet.
Chaque élément tient en une phrase."""


def choisir_panel(personas: list[PersonaEnregistre], taille: int) -> list[PersonaEnregistre]:
    """Panel représentatif : réparti régulièrement sur les âges de la base."""
    tries = sorted(personas, key=lambda p: (p.age, p.id))
    pas = len(tries) / taille
    return sorted((tries[int(i * pas + pas / 2)] for i in range(taille)), key=lambda p: p.id)


def fiche(p: PersonaEnregistre) -> str:
    return f"{p.id} : {p.prenom}, {p.genre}, {p.age} ans, {p.situation}, {p.csp}, {p.lieu_de_vie}"


class EtapeEntretiens(Etape):
    numero = 3
    titre = "Entretiens simulés (panel de 100 personas)"
    fichier = "03-entretiens"
    modele = LivrableEntretiens

    async def generer(self, gen: Generation) -> LivrableEntretiens:
        session = gen.session
        if session.contexte is None:
            raise ErreurSession("Validez d'abord l'étape 0.")
        signaux = [Signal(**s) for s in session.livrable(2)["signaux"]]
        questions_ajoutees = [q for q in gen.options.get("questions_ajoutees", []) if q.strip()]
        reprise = (
            gen.partiel if (gen.partiel and not gen.consigne and not questions_ajoutees) else {}
        )
        partiel: dict[str, Any] = {"enrichis": {}, "entretiens": {}, **reprise}
        verrou = asyncio.Lock()

        async def sauver() -> None:
            async with verrou:
                if gen.sauver_partiel:
                    await gen.sauver_partiel(partiel)

        # Profil démographique réel du territoire, puis base de personas tirée de ce profil
        if "profil" not in partiel:
            partiel["profil"] = await profil_demographique(session.contexte.localisation)
        profil = partiel["profil"]
        gen.flux_utilises = ["demographie"]
        loc = session.contexte.localisation
        base = [
            PersonaEnregistre(id=f"p{i:03d}", **p)
            for i, p in enumerate(
                generer_base(profil, loc.ville or loc.pays, NB_PERSONAS, session.id), start=1
            )
        ]
        panel = choisir_panel(base, TAILLE_PANEL[gen.demo])
        ids_panel = {p.id for p in panel}

        if "guide" not in partiel:
            resultat = await llm.generer_structure(
                GuideEntretien,
                messages_etape(
                    session,
                    tache=TACHE_GUIDE.format(horizon=session.saisie.horizon),
                    nom_outil="guide_entretien",
                    consigne=gen.consigne,
                ),
                nom_outil="guide_entretien",
                description="Enregistre le guide d'entretien.",
                rapide=True,
                max_tokens=2_000,
            )
            partiel["guide"] = resultat.questions[:5] + questions_ajoutees
            await sauver()
        questions = partiel["guide"]
        guide_texte = "\n".join(f"Q{i}. {q}" for i, q in enumerate(questions, start=1))

        async def interroger(groupe: list[PersonaEnregistre]) -> None:
            if all(p.id in partiel["entretiens"] for p in groupe):
                return
            resultat = await llm.generer_structure(
                Entretiens,
                messages_etape(
                    session,
                    tache=TACHE_ENTRETIENS.format(
                        longueur="1 à 2 phrases" if gen.demo else "2 à 3 phrases"
                    ),
                    nom_outil="entretiens",
                    donnees=f"Guide :\n{guide_texte}\n\nPersonas interrogés :\n"
                    + "\n".join(fiche(p) for p in groupe),
                    consigne=gen.consigne,
                ),
                nom_outil="entretiens",
                description="Enregistre l'entretien de chaque persona interrogé.",
                rapide=True,
                max_tokens=8_000,
            )
            for e in resultat.entretiens:
                partiel["entretiens"][e.persona_id] = e.model_dump()
            await sauver()

        async def enrichir(groupe: list[PersonaEnregistre]) -> None:
            if all(p.id in partiel["enrichis"] for p in groupe):
                return
            resultat = await llm.generer_structure(
                LotEnrichi,
                messages_etape(
                    session,
                    tache=TACHE_ENRICHISSEMENT,
                    nom_outil="enrichissement",
                    donnees="\n".join(fiche(p) for p in groupe),
                ),
                nom_outil="enrichissement",
                description="Enregistre usages, attentes et opinion de chaque persona.",
                rapide=True,
                # Marge pour la réflexion interne du modèle, décomptée de max_tokens
                max_tokens=8_000,
            )
            for e in resultat.personas:
                partiel["enrichis"][e.persona_id] = e.model_dump()
            await sauver()

        # Entretiens du panel et enrichissement du reste de la base, en parallèle
        hors_panel = [] if gen.demo else [p for p in base if p.id not in ids_panel]
        taches = [
            interroger(panel[i : i + PERSONAS_PAR_ENTRETIEN])
            for i in range(0, len(panel), PERSONAS_PAR_ENTRETIEN)
        ] + [
            enrichir(hors_panel[i : i + PERSONAS_PAR_ENRICHISSEMENT])
            for i in range(0, len(hors_panel), PERSONAS_PAR_ENRICHISSEMENT)
        ]
        issues = await asyncio.gather(*taches, return_exceptions=True)
        self._verifier(issues, "les entretiens ou l'enrichissement de la base")

        for p in base:
            donnees = partiel["entretiens"].get(p.id) or partiel["enrichis"].get(p.id) or {}
            p.usages = donnees.get("usages", "")
            p.attentes = donnees.get("attentes", "")
            p.opinion = donnees.get("opinion")
            p.reponses = donnees.get("reponses", [])
        interroges = [p for p in base if p.reponses]
        comptes = Counter(p.opinion for p in base if p.opinion)
        repartition = [Repartition(opinion=o, nombre=comptes.get(o, 0)) for o in LIBELLES_OPINIONS]

        reponses = "\n".join(
            f"{p.id} ({p.age} ans, {p.situation}, {LIBELLES_OPINIONS[p.opinion]}) : "
            + " | ".join(p.reponses)
            for p in interroges
        )
        opinions = ", ".join(f"{LIBELLES_OPINIONS[r.opinion]} {r.nombre}" for r in repartition)
        nb_opinions = sum(comptes.values())
        nb_verbatims = min(len(interroges), 4 if gen.demo else 10)
        synthese = await llm.generer_structure(
            SyntheseEntretiens,
            messages_etape(
                session,
                tache=TACHE_SYNTHESE.format(
                    nb=nb_opinions,
                    nb_verbatims=nb_verbatims,
                    n="3" if gen.demo else "3 à 5",
                    n_usages="2" if gen.demo else "2 à 4",
                ),
                nom_outil="synthese_entretiens",
                acquis=[("Signaux collectés (étape 2)", formater_signaux(signaux))],
                donnees=(
                    f"Guide :\n{guide_texte}\n\nRépartition des opinions sur la base : {opinions}"
                    f"\n\nRéponses du panel :\n{reponses}"
                ),
                consigne=gen.consigne,
                version_precedente=gen.version_precedente,
            ),
            nom_outil="synthese_entretiens",
            description="Enregistre la synthèse des entretiens simulés.",
            rapide=True,
            max_tokens=4_000,
        )
        ids_interroges = {p.id for p in interroges}
        synthese.verbatims = [v for v in synthese.verbatims if v.persona_id in ids_interroges]

        source = (
            Source(nom=profil["source"], url=profil["url"])
            if profil.get("source") and profil.get("url")
            else None
        )
        return LivrableEntretiens(
            guide=questions,
            profil_demographique=resumer_profil(profil),
            source_demographique=source,
            personas=base,
            panel=sorted(ids_interroges),
            synthese=synthese,
            repartition=repartition,
        )

    @staticmethod
    def _verifier(issues: list[Any], quoi: str) -> None:
        echecs = [e for e in issues if isinstance(e, BaseException)]
        if echecs:
            raise llm.ErreurLLM(
                f"Échec partiel sur {quoi} ({echecs[0]}). "
                "Les résultats obtenus sont conservés : relancez pour compléter."
            )

    def markdown(self, livrable: LivrableEntretiens, session: Session) -> str:
        s = livrable.synthese
        personas = {p.id: p for p in livrable.personas}
        panel = set(livrable.panel)
        tableau = "\n".join(
            f"| {p.id} | {p.prenom} | {p.age} | {p.genre} | {p.situation} | {p.csp} | "
            f"{p.lieu_de_vie} | {LIBELLES_OPINIONS.get(p.opinion, '')} | {'oui' if p.id in panel else ''} |"
            for p in livrable.personas
        )
        entretiens = "\n\n".join(
            f"**{p.id}, {p.prenom}, {p.age} ans** ({LIBELLES_OPINIONS[p.opinion]})\n\n"
            + "\n".join(f"{i}. « {r} »" for i, r in enumerate(p.reponses, start=1))
            for p in livrable.personas
            if p.id in panel
        )
        verbatims = "\n\n".join(
            f"> « {v.citation} »\n> — {v.persona_id}"
            + (
                f", {personas[v.persona_id].prenom}, {personas[v.persona_id].age} ans"
                if v.persona_id in personas
                else ""
            )
            for v in s.verbatims
        )
        repartition = "\n".join(
            f"| {LIBELLES_OPINIONS[r.opinion]} | {r.nombre} |" for r in livrable.repartition
        )
        return "\n\n".join(
            [
                f"> **{livrable.avertissement}**",
                (
                    f"Base de {len(livrable.personas)} personas synthétiques ; panel "
                    f"représentatif de {len(panel)} personas interrogés."
                ),
                "### Guide d'entretien\n\n"
                + "\n".join(f"{i}. {q}" for i, q in enumerate(livrable.guide, start=1)),
                f"### Ancrage démographique\n\n{livrable.profil_demographique}",
                "### Synthèse",
                "**Attentes majeures**\n\n" + puces(s.attentes_majeures),
                "**Irritants**\n\n" + puces(s.irritants),
                "**Usages émergents**\n\n" + puces(s.usages_emergents),
                "**Enseignements**\n\n" + puces(s.enseignements),
                f"**Répartition des opinions ({sum(r.nombre for r in livrable.repartition)} personas)**\n\n| Opinion | Personas |\n"
                "|---|---|\n" + repartition,
                "### Verbatims représentatifs\n\n" + verbatims,
                "### Entretiens du panel\n\n" + entretiens,
                f"### Profil des {len(livrable.personas)} personas\n\n"
                "| Id | Prénom | Âge | Genre | Situation | CSP | Lieu de vie | Opinion | Panel |\n"
                "|---|---|---|---|---|---|---|---|---|\n" + tableau,
            ]
        )

    def sources(self, livrable: LivrableEntretiens) -> list[Source]:
        return [livrable.source_demographique] if livrable.source_demographique else []


def resumer_profil(profil: dict[str, Any]) -> str:
    lignes = []
    if profil.get("territoire"):
        lignes.append(
            f"Territoire : {profil['territoire']} (échelle {profil.get('echelle', '?')}, "
            f"{profil.get('annee', 's. d.')})"
        )
    if profil.get("population"):
        lignes.append(f"Population : {profil['population']:,}".replace(",", " "))
    if profil.get("tranches_age_pct"):
        lignes.append(
            "Tranches d'âge : "
            + ", ".join(f"{t} ans : {v} %" for t, v in profil["tranches_age_pct"].items())
        )
    for cle, libelle in [
        ("csp_15_ans_et_plus_pct", "CSP des 15 ans et plus"),
        ("activite", "Activité"),
    ]:
        if profil.get(cle):
            lignes.append(f"{libelle} : " + ", ".join(f"{k} {v} %" for k, v in profil[cle].items()))
    if profil.get("revenu"):
        lignes.append("Revenus : " + ", ".join(f"{k} {v}" for k, v in profil["revenu"].items()))
    if profil.get("source"):
        lignes.append(
            f"Source : {profil['source']}" + (f" ({profil['url']})" if profil.get("url") else "")
        )
    return "\n".join(f"- {ligne}" for ligne in lignes) or "- Profil indisponible"
