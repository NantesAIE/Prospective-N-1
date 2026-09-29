"""Contrat commun des étapes du parcours HITL."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from prospective.session import ErreurSession, Session, Source


@dataclass
class Generation:
    """Contexte d'une génération d'étape."""

    session: Session  # instantané de la session au lancement
    consigne: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    partiel: dict[str, Any] | None = None  # reprise d'une génération interrompue
    version_precedente: str | None = None  # Markdown du livrable précédent, en cas de relance
    sauver_partiel: Callable[[dict[str, Any]], Awaitable[None]] | None = None
    flux_utilises: list[str] = field(default_factory=list)

    @property
    def demo(self) -> bool:
        """Mode démo : volumes réduits pour tenir le parcours complet en 5 minutes."""
        return self.session.mode == "demo"


class Etape(ABC):
    numero: int
    titre: str
    fichier: str  # nom de l'archive sans extension, ex. "04-steepl"
    modele: type[BaseModel]  # livrable validé

    @abstractmethod
    async def generer(self, gen: Generation) -> BaseModel:
        """Produit le livrable de l'étape."""

    @abstractmethod
    def markdown(self, livrable: BaseModel, session: Session) -> str:
        """Rendu Markdown du livrable, pour l'archive."""

    def sources(self, livrable: BaseModel) -> list[Source]:
        return []

    def avant_validation(self, livrable: BaseModel, options: dict[str, Any]) -> BaseModel:
        """Contrôle et applique les choix faits à la validation (ex. scénario visé)."""
        return livrable

    def apres_validation(self, livrable: BaseModel, session: Session) -> None:
        """Effets de bord de la validation sur la session (ex. user context)."""

    def charger(self, livrable: dict[str, Any] | None) -> BaseModel:
        if livrable is None:
            raise ErreurSession(f"L'étape {self.numero} n'a pas encore de livrable.")
        return self.modele.model_validate(livrable)


def puces(elements: list[str]) -> str:
    return "\n".join(f"- {e}" for e in elements) or "- Aucun"


def lien_source(nom: str | None, url: str | None, date: str | None = None) -> str:
    if not nom and not url:
        return "hypothèse IA"
    texte = f"[{nom or url}]({url})" if url else str(nom)
    return f"{texte}, {date}" if date else texte
