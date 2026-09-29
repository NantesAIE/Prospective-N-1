"""Interface commune des connecteurs de flux, avec timeout et mode dégradé."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod

import httpx

from prospective.config import parametres
from prospective.flux.tls import contexte_tls
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

journal = logging.getLogger(__name__)

TIMEOUT_FLUX = 8.0
UA = "HackTheVibe-Prospective/0.1 (hackathon interne)"


class Flux(ABC):
    id: str
    nom: str
    description: str
    axes: list[Axe]
    niveau: Niveau
    pays: list[str] | None = None  # codes ISO2 si niveau pays ou local
    zone: str | None = None  # "UE"
    cle_requise: bool = False
    # Vrai si `requete` est exploitable (recherche plein texte), pour l'assistant
    interrogeable: bool = True

    @abstractmethod
    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        """Collecte des signaux. `requete` remplace les mots-clés du contexte s'il est fourni."""

    def fiche(self) -> dict:
        return {
            "id": self.id,
            "nom": self.nom,
            "description": self.description,
            "axes": [a.value for a in self.axes],
            "niveau": self.niveau.value,
            "cle_requise": self.cle_requise,
            "interrogeable": self.interrogeable,
        }


def client_http() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=TIMEOUT_FLUX,
        headers={"User-Agent": UA},
        follow_redirects=True,
        verify=contexte_tls(),  # certifi + magasin Windows (proxy d'entreprise)
    )


def charger_fixture(flux_id: str) -> list[SignalBrut]:
    chemin = parametres().dossier_fixtures / "flux" / f"{flux_id}.json"
    if not chemin.exists():
        return []
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    return [SignalBrut(**{**s, "donnees_demo": True}) for s in donnees]


async def collecter_avec_repli(
    flux: Flux,
    ctx: ContexteUtilisateur,
    client: httpx.AsyncClient,
    requete: str | None = None,
) -> tuple[list[SignalBrut], bool]:
    """Collecte avec timeout de 8 s. En cas d'échec ou en mode démo, renvoie la fixture.

    Retourne (signaux, degrade) : `degrade` est vrai si les données viennent du jeu de secours.
    """
    if parametres().demo:
        return charger_fixture(flux.id), True
    try:
        signaux = await asyncio.wait_for(flux.collecter(ctx, client, requete), TIMEOUT_FLUX)
        return signaux, False
    except Exception as exc:  # noqa: BLE001 : tout échec bascule sur le mode dégradé
        journal.warning("Flux %s en échec (%s), bascule sur les données de secours", flux.id, exc)
        return charger_fixture(flux.id), True
