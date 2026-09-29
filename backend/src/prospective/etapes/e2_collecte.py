"""Étape 2 : collecte et analyse."""

import asyncio

from pydantic import BaseModel

from prospective import llm
from prospective.etapes.base import Etape, Generation, lien_source
from prospective.flux import par_id
from prospective.flux.base import client_http, collecter_avec_repli
from prospective.modeles import LIBELLES_AXES, LIBELLES_NIVEAUX, Axe, Signal, SignalBrut
from prospective.prompts import messages_etape
from prospective.session import ErreurSession, Session, Source

MAX_BRUTS = 160


class SignalExtrait(BaseModel):
    ref: int | None
    titre: str
    resume: str
    axe: Axe
    hypothese_ia: bool


class ExtractionSignaux(BaseModel):
    signaux: list[SignalExtrait]


class LivrableCollecte(BaseModel):
    signaux: list[Signal]
    flux_degrades: list[str] = []
    nb_elements_bruts: int = 0


TACHE = """Les données ci-dessus sont des éléments bruts numérotés [n], issus des flux activés
(open data, bench concurrentiel, presse, recherche, climat...).
Extrais-en {nombre} signaux candidats utiles à la prospective du projet à l'horizon {horizon} :
- ref : le numéro [n] de l'élément brut dont provient le signal (obligatoire si le signal s'appuie sur une donnée) ;
- titre : court et explicite ;
- resume : une phrase factuelle, avec les chiffres clés de la donnée si elle en contient ;
- axe : l'axe STEEPL présumé (S Social, T Technologique, E1 Économique, E2 Environnemental, P Politique, L Légal) ;
- hypothese_ia : false si ref est renseigné, true sinon.
Regroupe les éléments redondants en un seul signal. Écarte ce qui est hors sujet.
Tu peux ajouter au plus 2 signaux sans ref (ref null, hypothese_ia true) pour combler un
angle mort évident ; ne leur attribue aucune source."""


def repartir_par_flux(bruts: list[SignalBrut], nb_groupes: int) -> list[list[int]]:
    """Répartit les indices des éléments bruts en groupes équilibrés, par flux entiers."""
    par_flux: dict[str, list[int]] = {}
    for i, b in enumerate(bruts):
        par_flux.setdefault(b.flux_id, []).append(i)
    groupes: list[list[int]] = [[] for _ in range(nb_groupes)]
    for indices in sorted(par_flux.values(), key=len, reverse=True):
        min(groupes, key=len).extend(indices)
    return [g for g in groupes if g]


class EtapeCollecte(Etape):
    numero = 2
    titre = "Collecte et analyse"
    fichier = "02-collecte"
    modele = LivrableCollecte

    async def _collecter(self, gen: Generation) -> tuple[list[SignalBrut], list[str], list[str]]:
        session = gen.session
        if session.contexte is None:
            raise ErreurSession("Validez d'abord l'étape 0.")
        actifs = [f["id"] for f in session.livrable(1)["flux"] if f["actif"]]
        async with client_http() as client:
            resultats = await asyncio.gather(
                *(collecter_avec_repli(par_id(fid), session.contexte, client) for fid in actifs)
            )
        bruts: list[SignalBrut] = []
        vus: set[tuple[str, str]] = set()
        degrades = []
        for fid, (signaux, degrade) in zip(actifs, resultats, strict=True):
            if degrade:
                degrades.append(fid)
            for s in signaux:
                # Plusieurs signaux statistiques partagent l'URL de requête de leur API
                if (s.url, s.titre) not in vus:
                    vus.add((s.url, s.titre))
                    bruts.append(s)
        return bruts[:MAX_BRUTS], actifs, degrades

    async def generer(self, gen: Generation) -> LivrableCollecte:
        if gen.partiel and "bruts" in gen.partiel and not gen.consigne:
            bruts = [SignalBrut(**b) for b in gen.partiel["bruts"]]
            actifs, degrades = gen.partiel["actifs"], gen.partiel["degrades"]
        else:
            bruts, actifs, degrades = await self._collecter(gen)
            if gen.sauver_partiel:
                await gen.sauver_partiel(
                    {
                        "bruts": [b.model_dump(mode="json") for b in bruts],
                        "actifs": actifs,
                        "degrades": degrades,
                    }
                )
        gen.flux_utilises = actifs
        if not bruts:
            raise ErreurSession("Aucune donnée collectée : vérifiez les flux activés à l'étape 1.")

        # Extractions parallèles sur des groupes de flux distincts : chaque sortie reste
        # courte (la sortie structurée plafonne vers 150 caractères par seconde)
        nombre = "4 à 6" if gen.demo else "10 à 20"
        longueur = 180 if gen.demo else 300

        async def extraire(indices: list[int]) -> list[SignalExtrait]:
            donnees = "\n".join(
                f"[{i}] ({bruts[i].flux_id}, {LIBELLES_NIVEAUX[bruts[i].niveau]}, "
                f"{bruts[i].date}) {bruts[i].titre} : {bruts[i].resume[:longueur]}"
                for i in indices
            )
            messages = messages_etape(
                gen.session,
                tache=TACHE.format(horizon=gen.session.saisie.horizon, nombre=nombre),
                nom_outil="signaux_candidats",
                donnees=donnees,
                consigne=gen.consigne,
            )
            extraction = await llm.generer_structure(
                ExtractionSignaux,
                messages,
                nom_outil="signaux_candidats",
                description="Enregistre la liste des signaux candidats extraits des données.",
                rapide=True,
                max_tokens=8_000,
            )
            return extraction.signaux

        groupes = repartir_par_flux(bruts, 3 if gen.demo else 2)
        extraits = await asyncio.gather(*(extraire(g) for g in groupes))

        signaux = []
        for i, ext in enumerate((e for lot in extraits for e in lot), start=1):
            signal = Signal(id=f"s{i:02d}", titre=ext.titre, resume=ext.resume, axe=ext.axe)
            if ext.ref is not None and 0 <= ext.ref < len(bruts):
                brut = bruts[ext.ref]
                signal.source, signal.url, signal.date = brut.source, brut.url, brut.date
                signal.niveau, signal.flux_id = brut.niveau, brut.flux_id
                signal.donnees_demo = brut.donnees_demo
            else:
                # Référence absente ou invalide : jamais de source inventée
                signal.hypothese_ia = True
            signaux.append(signal)
        return LivrableCollecte(
            signaux=signaux, flux_degrades=degrades, nb_elements_bruts=len(bruts)
        )

    def markdown(self, livrable: LivrableCollecte, session: Session) -> str:
        retenus = [s for s in livrable.signaux if s.retenu]
        blocs = [
            (
                f"{len(retenus)} signaux retenus sur {len(livrable.signaux)} candidats, "
                f"extraits de {livrable.nb_elements_bruts} éléments bruts."
            )
        ]
        if livrable.flux_degrades:
            blocs.append(
                "Données de démonstration utilisées pour : " + ", ".join(livrable.flux_degrades)
            )
        for axe in Axe:
            lignes = [
                f"| {s.id} | {s.titre} | {s.resume} | "
                f"{'ajout manuel' if s.ajout_manuel and not s.url else lien_source(s.source, s.url, s.date)}"
                f" | {LIBELLES_NIVEAUX.get(s.niveau, '') if s.niveau else ''} |"
                for s in retenus
                if s.axe == axe
            ]
            if lignes:
                blocs.append(
                    f"### {LIBELLES_AXES[axe]}\n\n| Id | Signal | Résumé | Source | Niveau |\n"
                    "|---|---|---|---|---|\n" + "\n".join(lignes)
                )
        ecartes = [s for s in livrable.signaux if not s.retenu]
        if ecartes:
            blocs.append(
                "### Signaux écartés par l'utilisateur\n\n"
                + "\n".join(f"- {s.id} : {s.titre}" for s in ecartes)
            )
        return "\n\n".join(blocs)

    def sources(self, livrable: LivrableCollecte) -> list[Source]:
        return sources_des_signaux([s for s in livrable.signaux if s.retenu])


def sources_des_signaux(signaux: list[Signal]) -> list[Source]:
    vues: dict[str, Source] = {}
    for s in signaux:
        if s.url and s.url not in vues:
            vues[s.url] = Source(nom=s.source or s.url, url=s.url, date=s.date)
    return list(vues.values())
