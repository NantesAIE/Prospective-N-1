"""Orchestration du parcours HITL : générer, modifier, valider une étape."""

import asyncio
import json
from typing import Any

from prospective import archive, llm
from prospective import session as sessions
from prospective.config import parametres
from prospective.etapes import ETAPES, Generation
from prospective.llm import ErreurLLM
from prospective.modeles import SaisieProjet
from prospective.session import ErreurSession, Mode, Session, maintenant

# Budget de temps par étape, en secondes. En démo, le parcours complet tient en 5 minutes
# de génération ; en mode complet, le plafond ne sert que de garde-fou.
BUDGET_DEMO = {0: 50, 1: 10, 2: 50, 3: 75, 4: 45, 5: 35, 6: 45, 7: 45, 8: 45}
BUDGET_COMPLET = 600


def _verifier_accessible(session: Session, n: int) -> None:
    if not 0 <= n < len(ETAPES):
        raise ErreurSession(f"Étape inconnue : {n}")
    for precedente in session.etapes[:n]:
        if precedente.statut != "valide":
            raise ErreurSession(f"L'étape {precedente.numero} doit être validée avant l'étape {n}.")


def _invalider_suivantes(session: Session, n: int) -> None:
    """Toute reprise d'une étape remet les suivantes à faire (leurs archives restent)."""
    for suivante in session.etapes[n + 1 :]:
        if suivante.statut != "a_faire":
            suivante.statut = "a_faire"


def _fixture_demo(n: int) -> dict[str, Any]:
    chemin = parametres().dossier_fixtures / "demo" / f"etape-{n}.json"
    if not chemin.exists():
        raise ErreurSession(f"Mode hors ligne : aucune donnée préenregistrée pour l'étape {n}.")
    return json.loads(chemin.read_text(encoding="utf-8"))


def creer_session(
    saisie: SaisieProjet, mode: Mode = "complet", modele: str | None = None
) -> Session:
    if modele:
        llm.verifier_modele(modele)
    session = sessions.creer(saisie, mode, modele)
    archive.journaliser(
        session, "creation", detail=f"{saisie.thematique}, {saisie.lieu or saisie.pays}"
    )
    return session


async def generer(
    session_id: str, n: int, consigne: str | None = None, options: dict[str, Any] | None = None
) -> Session:
    session = sessions.charger(session_id)
    _verifier_accessible(session, n)
    etape = ETAPES[n]
    etat = session.etapes[n]
    consigne = (consigne or "").strip() or None

    async def sauver_partiel(partiel: dict[str, Any]) -> None:
        await sessions.modifier(session_id, lambda s: setattr(s.etapes[n], "partiel", partiel))

    gen = Generation(
        session=session,
        consigne=consigne,
        options=options or {},
        partiel=etat.partiel,
        version_precedente=(
            etape.markdown(etape.charger(etat.livrable), session) if etat.livrable else None
        ),
        sauver_partiel=sauver_partiel,
    )
    budget = BUDGET_DEMO[n] if session.mode == "demo" else BUDGET_COMPLET
    try:
        if parametres().demo:
            livrable = etape.modele.model_validate(_fixture_demo(n))
        else:
            with llm.utiliser_modele(session.modele):
                async with asyncio.timeout(budget):
                    livrable = await etape.generer(gen)
    except TimeoutError:
        message = (
            f"L'étape a dépassé son budget de {budget} s. Les résultats partiels sont "
            "conservés : relancez pour poursuivre, ou choisissez un modèle plus rapide."
        )
        archive.journaliser(session, "echec", n, message)
        raise ErreurLLM(message) from None
    except (ErreurLLM, ErreurSession) as exc:
        archive.journaliser(session, "echec", n, str(exc))
        raise

    def appliquer(s: Session) -> None:
        e = s.etapes[n]
        if e.livrable is not None and not e.archive:
            # Brouillon jamais archivé : on le conserve avant de le remplacer
            archive.archiver_version(s, etape, etape.charger(e.livrable))
        e.version += 1
        e.livrable = livrable.model_dump(mode="json")
        e.statut = "brouillon"
        e.modifie = False
        e.archive = False
        e.commentaire = ""
        e.partiel = None
        e.flux_utilises = gen.flux_utilises
        if consigne:
            e.consignes.append(consigne)
        _invalider_suivantes(s, n)
        archive.journaliser(s, "relance" if e.version > 1 else "generation", n, consigne or "")

    return await sessions.modifier(session_id, appliquer)


async def modifier(
    session_id: str, n: int, livrable: dict[str, Any] | None, commentaire: str | None
) -> Session:
    etape = ETAPES[n]

    def appliquer(s: Session) -> None:
        _verifier_accessible(s, n)
        e = s.etapes[n]
        if e.livrable is None:
            raise ErreurSession("Générez d'abord l'étape avant de la modifier.")
        if livrable is not None:
            e.livrable = etape.modele.model_validate(livrable).model_dump(mode="json")
            e.modifie = True
            e.archive = False
        if commentaire is not None:
            e.commentaire = commentaire
        if e.statut == "valide":
            e.statut = "brouillon"
            _invalider_suivantes(s, n)
        archive.journaliser(s, "modification", n, commentaire or "édition du livrable")

    return await sessions.modifier(session_id, appliquer)


async def valider(
    session_id: str, n: int, commentaire: str | None = None, options: dict[str, Any] | None = None
) -> Session:
    etape = ETAPES[n]

    def appliquer(s: Session) -> None:
        _verifier_accessible(s, n)
        e = s.etapes[n]
        livrable = etape.avant_validation(etape.charger(e.livrable), options or {})
        if commentaire:
            e.commentaire = commentaire
        e.livrable = livrable.model_dump(mode="json")
        e.statut = "valide"
        e.valide_le = maintenant()
        etape.apres_validation(livrable, s)
        archive.ecrire_etape(s, etape, livrable, "modifie" if e.modifie else "valide")
        e.archive = True
        archive.journaliser(s, "validation", n, e.commentaire)
        if n == len(ETAPES) - 1:
            archive.ecrire_synthese(s, ETAPES)

    return await sessions.modifier(session_id, appliquer)


def fichiers(session: Session) -> list[str]:
    return sorted(p.name for p in session.chemin.glob("*.md"))


async def regler(session_id: str, mode: Mode | None, modele: str | None) -> Session:
    """Change le mode (démo ou complet) et le modèle de la session."""
    if modele:
        llm.verifier_modele(modele)

    def appliquer(s: Session) -> None:
        if mode is not None:
            s.mode = mode
        if modele is not None:
            s.modele = modele or None
        archive.journaliser(
            s, "reglage", detail=f"mode {s.mode}, modèle {s.modele or 'par défaut'}"
        )

    return await sessions.modifier(session_id, appliquer)
