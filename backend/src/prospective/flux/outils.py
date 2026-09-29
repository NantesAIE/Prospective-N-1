"""Outils communs aux connecteurs : client TLS, débit, requêtes parallèles, mise en forme."""

import asyncio
import re
import time
import unicodedata
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Any

import httpx

from prospective.flux.base import TIMEOUT_FLUX, UA
from prospective.flux.tls import contexte_tls
from prospective.modeles import ContexteUtilisateur

# Échéance interne des connecteurs à requêtes multiples, sous le plafond de 8 s de base.py.
# Le script de capture l'augmente pour les API lentes.
DELAI_INTERNE = 7.0


def client_tls(timeout: float = TIMEOUT_FLUX) -> httpx.AsyncClient:
    """Équivalent de base.client_http(), avec le contexte TLS du proxy d'entreprise."""
    return httpx.AsyncClient(
        timeout=timeout, headers={"User-Agent": UA}, follow_redirects=True, verify=contexte_tls()
    )


class Limiteur:
    """Espace les requêtes vers une même API d'au moins `intervalle` secondes."""

    def __init__(self, intervalle: float):
        self.intervalle = intervalle
        self._verrou: asyncio.Lock | None = None
        self._dernier = 0.0

    async def attendre(self) -> None:
        # Le verrou est créé à la demande, dans la boucle d'événements courante
        if self._verrou is None:
            self._verrou = asyncio.Lock()
        async with self._verrou:
            attente = self._dernier + self.intervalle - time.monotonic()
            if attente > 0:
                await asyncio.sleep(attente)
            self._dernier = time.monotonic()


async def rassembler(taches: list[Awaitable[Any]], delai: float | None = None) -> list[Any]:
    """Lance les tâches en parallèle et conserve les résultats obtenus avant l'échéance.

    Une tâche en échec ou hors délai vaut None : les résultats partiels restent exploitables.
    """
    futures = [asyncio.ensure_future(t) for t in taches]
    termines, en_cours = await asyncio.wait(futures, timeout=delai or DELAI_INTERNE)
    for f in en_cours:
        f.cancel()
    return [f.result() if f in termines and not f.exception() else None for f in futures]


def termes(
    ctx: ContexteUtilisateur, requete: str | None, anglais: bool = False, maximum: int = 4
) -> list[str]:
    """Termes de recherche : la requête explicite, sinon les mots-clés du contexte."""
    if requete and requete.strip():
        return [requete.strip()]
    principaux, secours = (ctx.mots_cles_en, ctx.mots_cles) if anglais else (ctx.mots_cles, [])
    liste = [t.strip() for t in (principaux or secours) if t.strip()]
    return liste[:maximum] or [ctx.saisie.thematique]


def sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in decompose if not unicodedata.combining(c)).lower()


def pertinence(texte: str, liste: list[str]) -> float:
    """Somme, sur les termes, de la part de leurs mots (4 lettres et plus) présents dans le texte.

    Un terme entièrement présent vaut 1 : « sport santé » pèse plus qu'un « activité » isolé.
    """
    cible = sans_accents(texte)
    score = 0.0
    for terme in liste:
        mots = re.findall(r"\w{4,}", sans_accents(terme))
        if mots:
            score += sum(1 for m in mots if m in cible) / len(mots)
    return score


def date_iso(valeur: str | None) -> str:
    """Normalise une date (ISO, AAAAMMJJThhmmssZ, JJ/MM/AAAA) en AAAA-MM-JJ."""
    if not valeur:
        return ""
    valeur = valeur.strip()
    if m := re.match(r"^(\d{4})-(\d{2})-(\d{2})", valeur):
        return "-".join(m.groups())
    if m := re.match(r"^(\d{4})(\d{2})(\d{2})T", valeur):
        return "-".join(m.groups())
    if m := re.match(r"^(\d{2})/(\d{2})/(\d{4})$", valeur):
        return f"{m[3]}-{m[2]}-{m[1]}"
    return valeur


def aujourdhui() -> str:
    return datetime.now(UTC).date().isoformat()


def annee_courante() -> int:
    return datetime.now(UTC).year


def nombre(valeur: float, decimales: int = 0) -> str:
    """Format français : espace pour les milliers, virgule décimale."""
    return f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")


def signe(valeur: float, decimales: int = 1) -> str:
    arrondi = round(valeur, decimales)  # évite « -0,0 »
    return ("+" if arrondi >= 0 else "-") + nombre(abs(arrondi), decimales)


def entrelacer(listes: list[list]) -> list:
    """Alterne les éléments de plusieurs listes, pour que chaque requête soit représentée."""
    resultat = []
    for rang in range(max((len(liste) for liste in listes), default=0)):
        resultat.extend(liste[rang] for liste in listes if rang < len(liste))
    return resultat


def phrase(texte: str, maximum: int = 240) -> str:
    """Première phrase d'un texte, nettoyée et tronquée."""
    texte = re.sub(r"\s+", " ", texte or "").strip()
    fin = re.search(r"(?<=[.!?])\s", texte)
    if fin and fin.start() <= maximum:
        return texte[: fin.start()]
    return texte if len(texte) <= maximum else texte[: maximum - 1].rstrip() + "…"
