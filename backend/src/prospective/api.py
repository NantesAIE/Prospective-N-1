"""Routes de l'API REST consommée par le front."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ValidationError

from prospective import assistant, parcours
from prospective import session as sessions
from prospective.config import parametres
from prospective.etapes import ETAPES
from prospective.flux import CATALOGUE
from prospective.llm import MODELES_OUTILS_VERIFIES, ErreurLLM
from prospective.modeles import SaisieProjet
from prospective.session import ErreurSession, Mode

routeur = APIRouter(prefix="/api")

SAISIE_DEMO = SaisieProjet(
    description=(
        "Je veux créer un service de sport santé pour les seniors actifs, avec des séances en "
        "extérieur et un suivi connecté."
    ),
    thematique="sport, santé",
    pays="France",
    lieu="44000",
    horizon=2040,
    ambition="",
)


async def gerer_erreur_metier(_: Request, exc: Exception) -> JSONResponse:
    code = 502 if isinstance(exc, ErreurLLM) else 400
    return JSONResponse(status_code=code, content={"detail": str(exc)})


class NouvelleSession(SaisieProjet):
    mode: Mode = "complet"
    modele: str | None = None


class Reglages(BaseModel):
    mode: Mode | None = None
    modele: str | None = None


class DemandeGeneration(BaseModel):
    consigne: str | None = None
    options: dict[str, Any] = {}


class DemandeModification(BaseModel):
    livrable: dict[str, Any] | None = None
    commentaire: str | None = None


class DemandeValidation(BaseModel):
    commentaire: str | None = None
    options: dict[str, Any] = {}


class MessageUtilisateur(BaseModel):
    message: str
    etape: int


@routeur.get("/sante")
def sante() -> dict:
    p = parametres()
    return {
        "statut": "ok",
        "demo": p.demo,
        "cle_api_configuree": bool(p.agent_api_key),
        "modele": p.agent_model,
        "modele_rapide": p.agent_model_fast,
    }


@routeur.get("/etapes")
def etapes() -> list[dict]:
    return [{"numero": e.numero, "titre": e.titre, "fichier": e.fichier} for e in ETAPES]


@routeur.get("/flux")
def flux() -> list[dict]:
    return [f.fiche() for f in CATALOGUE]


@routeur.get("/modeles")
def modeles() -> dict:
    p = parametres()
    return {
        "modeles": list(MODELES_OUTILS_VERIFIES),
        "defaut": p.agent_model,
        "rapide": p.agent_model_fast,
    }


@routeur.get("/demo/saisie")
def saisie_demo() -> SaisieProjet:
    return SAISIE_DEMO


@routeur.get("/sessions")
def lister_sessions() -> list[dict]:
    return sessions.lister()


@routeur.post("/sessions")
def creer_session(demande: NouvelleSession) -> dict:
    saisie = SaisieProjet(**demande.model_dump(exclude={"mode", "modele"}))
    return parcours.creer_session(saisie, demande.mode, demande.modele).vue()


@routeur.patch("/sessions/{session_id}")
async def regler(session_id: str, reglages: Reglages) -> dict:
    return (await parcours.regler(session_id, reglages.mode, reglages.modele)).vue()


@routeur.get("/sessions/{session_id}")
def lire_session(session_id: str) -> dict:
    return sessions.charger(session_id).vue()


@routeur.post("/sessions/{session_id}/etapes/{n}/generer")
async def generer(session_id: str, n: int, demande: DemandeGeneration) -> dict:
    session = await parcours.generer(session_id, n, demande.consigne, demande.options)
    return session.vue()


@routeur.put("/sessions/{session_id}/etapes/{n}")
async def modifier(session_id: str, n: int, demande: DemandeModification) -> dict:
    try:
        session = await parcours.modifier(session_id, n, demande.livrable, demande.commentaire)
    except ValidationError as exc:
        raise HTTPException(422, f"Livrable invalide : {exc.error_count()} erreur(s).") from exc
    return session.vue()


@routeur.post("/sessions/{session_id}/etapes/{n}/valider")
async def valider(session_id: str, n: int, demande: DemandeValidation) -> dict:
    session = await parcours.valider(session_id, n, demande.commentaire, demande.options)
    return session.vue()


@routeur.get("/sessions/{session_id}/conversation")
def conversation(session_id: str) -> list[dict]:
    session = sessions.charger(session_id)
    return [m.model_dump() for m in sessions.lire_conversation(session)]


@routeur.post("/sessions/{session_id}/assistant")
async def parler(session_id: str, demande: MessageUtilisateur) -> list[dict]:
    messages = await assistant.repondre(session_id, demande.message, demande.etape)
    return [m.model_dump() for m in messages]


@routeur.get("/sessions/{session_id}/fichiers")
def fichiers(session_id: str) -> list[str]:
    return parcours.fichiers(sessions.charger(session_id))


@routeur.get("/sessions/{session_id}/fichiers/{nom}", response_class=PlainTextResponse)
def fichier(session_id: str, nom: str) -> str:
    session = sessions.charger(session_id)
    if nom not in parcours.fichiers(session):
        raise ErreurSession(f"Fichier introuvable : {nom}")
    return (session.chemin / nom).read_text(encoding="utf-8")
