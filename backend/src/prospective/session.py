"""Sessions de prospective : état machine (`etat.json`), chronomètre et verrouillage.

L'état complet vit dans `archives/<dossier>/etat.json` à côté des fichiers `.md` validés,
ce qui permet la reprise de session. La conversation avec l'assistant est stockée à part
(`conversation.json`) pour ne pas entrer en conflit avec une génération en cours.
"""

import asyncio
import json
import secrets
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from slugify import slugify

from prospective.config import parametres
from prospective.modeles import ContexteUtilisateur, SaisieProjet

NB_ETAPES = 9
INACTIVITE_MAX = 600  # au-delà, le temps d'inactivité ne compte pas dans le chronomètre

StatutEtape = Literal["a_faire", "brouillon", "valide"]
Mode = Literal["demo", "complet"]  # démo : parcours complet en 5 minutes, volumes réduits


def maintenant() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Source(BaseModel):
    nom: str
    url: str
    date: str | None = None


class EtatEtape(BaseModel):
    numero: int
    statut: StatutEtape = "a_faire"
    version: int = 0  # nombre de générations successives
    livrable: dict[str, Any] | None = None
    modifie: bool = False  # vrai si l'utilisateur a édité le livrable courant
    archive: bool = False  # vrai si le livrable courant est celui du fichier .md validé
    commentaire: str = ""
    consignes: list[str] = []  # consignes de relance successives
    flux_utilises: list[str] = []
    partiel: dict[str, Any] | None = None  # résultats partiels d'une génération interrompue
    valide_le: str | None = None


class Session(BaseModel):
    id: str
    dossier: str
    cree_le: str
    saisie: SaisieProjet
    contexte: ContexteUtilisateur | None = None
    mode: Mode = "complet"
    modele: str | None = None  # modèle choisi pour tout le parcours (sinon .env)
    etapes: list[EtatEtape] = Field(
        default_factory=lambda: [EtatEtape(numero=n) for n in range(NB_ETAPES)]
    )
    duree_secondes: float = 0.0
    derniere_activite: str = Field(default_factory=maintenant)

    @property
    def chemin(self) -> Path:
        return parametres().dossier_archives / self.dossier

    @property
    def etape_courante(self) -> int:
        """Première étape non validée (ou la dernière si tout est validé)."""
        for e in self.etapes:
            if e.statut != "valide":
                return e.numero
        return NB_ETAPES - 1

    def livrable(self, n: int) -> dict[str, Any]:
        """Livrable d'une étape précédente, qui doit être validée."""
        etape = self.etapes[n]
        if etape.statut != "valide" or etape.livrable is None:
            raise ErreurSession(f"L'étape {n} doit être validée avant de poursuivre.")
        return etape.livrable

    def vue(self) -> dict[str, Any]:
        """Représentation envoyée au front."""
        return {**self.model_dump(), "etape_courante": self.etape_courante}


class ErreurSession(Exception):
    """Erreur métier sur une session, avec un message destiné à l'utilisateur."""


_verrous: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _fichier_etat(dossier: Path) -> Path:
    return dossier / "etat.json"


def _ecrire_json(chemin: Path, donnees: Any) -> None:
    temporaire = chemin.with_suffix(".tmp")
    temporaire.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    temporaire.replace(chemin)


def creer(saisie: SaisieProjet, mode: Mode = "complet", modele: str | None = None) -> Session:
    identifiant = secrets.token_hex(2)
    lieu = saisie.lieu or saisie.pays
    dossier = (
        f"{datetime.now().astimezone():%Y-%m-%d}_{slugify(saisie.thematique)[:30]}-{slugify(lieu)[:20]}"
        f"_{identifiant}"
    )
    session = Session(
        id=identifiant,
        dossier=dossier,
        cree_le=maintenant(),
        saisie=saisie,
        mode=mode,
        modele=modele,
    )
    session.chemin.mkdir(parents=True, exist_ok=True)
    sauver(session)
    return session


def _trouver_dossier(session_id: str) -> Path:
    racine = parametres().dossier_archives
    for dossier in racine.glob(f"*_{session_id}"):
        if _fichier_etat(dossier).exists():
            return dossier
    raise ErreurSession(f"Session introuvable : {session_id}")


def charger(session_id: str) -> Session:
    dossier = _trouver_dossier(session_id)
    return Session.model_validate_json(_fichier_etat(dossier).read_text(encoding="utf-8"))


def sauver(session: Session) -> None:
    _ecrire_json(_fichier_etat(session.chemin), session.model_dump(mode="json"))


def lister() -> list[dict[str, Any]]:
    racine = parametres().dossier_archives
    sessions = []
    for fichier in sorted(racine.glob("*/etat.json"), reverse=True):
        try:
            s = Session.model_validate_json(fichier.read_text(encoding="utf-8"))
        except ValueError:
            continue
        sessions.append(
            {
                "id": s.id,
                "dossier": s.dossier,
                "cree_le": s.cree_le,
                "thematique": s.saisie.thematique,
                "lieu": s.saisie.lieu or s.saisie.pays,
                "description": s.saisie.description[:160],
                "etape_courante": s.etape_courante,
                "nb_validees": sum(e.statut == "valide" for e in s.etapes),
            }
        )
    return sessions


def _compter_temps(session: Session) -> None:
    derniere = datetime.fromisoformat(session.derniere_activite)
    ecart = (datetime.now().astimezone() - derniere).total_seconds()
    session.duree_secondes += max(0.0, min(ecart, INACTIVITE_MAX))
    session.derniere_activite = maintenant()


async def modifier(session_id: str, operation: Callable[[Session], Any]) -> Session:
    """Recharge, modifie et sauvegarde une session sous verrou.

    Les générations longues travaillent sur un instantané puis appliquent leur résultat
    via cette fonction, pour ne jamais écraser une modification concurrente.
    """
    async with _verrous[session_id]:
        session = charger(session_id)
        operation(session)
        _compter_temps(session)
        sauver(session)
        return session


# Conversation avec l'assistant


class MessageChat(BaseModel):
    role: Literal["user", "assistant"]
    contenu: str
    etape: int
    horodatage: str = Field(default_factory=maintenant)
    suggestions: list[dict[str, Any]] = []
    resultats: list[dict[str, Any]] = []  # résultats de sources interrogées


def lire_conversation(session: Session) -> list[MessageChat]:
    chemin = session.chemin / "conversation.json"
    if not chemin.exists():
        return []
    return [MessageChat(**m) for m in json.loads(chemin.read_text(encoding="utf-8"))]


def ajouter_messages(session: Session, messages: list[MessageChat]) -> None:
    chemin = session.chemin / "conversation.json"
    historique = lire_conversation(session) + messages
    _ecrire_json(chemin, [m.model_dump() for m in historique])
