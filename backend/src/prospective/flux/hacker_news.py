"""Hacker News (API Algolia) : signaux tech et startups."""

import time
from typing import ClassVar
from urllib.parse import urlparse

import httpx

from prospective.flux.base import Flux
from prospective.flux.outils import date_iso, entrelacer, rassembler, termes
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://hn.algolia.com/api/v1/search"
URL_ITEM = "https://news.ycombinator.com/item?id={id}"
MAX_SIGNAUX = 12
ANCIENNETE_MAX = 5 * 365 * 86400  # au-delà de 5 ans, les stories ne sont plus des signaux


class HackerNews(Flux):
    id = "hacker_news"
    nom = "Hacker News"
    description = "Discussions tech et startups anglophones (stories), avec leur audience."
    axes: ClassVar[list[Axe]] = [Axe.T]
    niveau = Niveau.MONDE

    async def _chercher(self, client: httpx.AsyncClient, terme: str) -> list[dict]:
        reponse = await client.get(
            URL,
            params={
                "query": terme,
                "tags": "story",
                "hitsPerPage": 8,
                "numericFilters": f"created_at_i>{int(time.time()) - ANCIENNETE_MAX}",
            },
        )
        reponse.raise_for_status()
        return reponse.json().get("hits", [])

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        resultats = await rassembler(
            [self._chercher(client, t) for t in termes(ctx, requete, anglais=True)]
        )
        if all(r is None for r in resultats):
            raise RuntimeError("Hacker News : aucune réponse")

        # Ordre de pertinence Algolia, terme par terme : trier par points favorise le hors-sujet
        stories = {}
        for h in entrelacer([r for r in resultats if r]):
            if h.get("title"):
                stories.setdefault(h["objectID"], h)
        signaux = []
        for h in list(stories.values())[:MAX_SIGNAUX]:
            lien = h.get("url") or URL_ITEM.format(id=h["objectID"])
            domaine = urlparse(lien).netloc.removeprefix("www.")
            date = date_iso(h.get("created_at"))
            signaux.append(
                SignalBrut(
                    titre=h["title"],
                    resume=(
                        f"Story Hacker News du {date} pointant vers {domaine} : "
                        f"{h.get('points') or 0} points et {h.get('num_comments') or 0} commentaires "
                        f"(discussion : {URL_ITEM.format(id=h['objectID'])})."
                    ),
                    source=f"Hacker News ({domaine})",
                    url=lien,
                    date=date,
                    axe_presume=Axe.T,
                    flux_id=self.id,
                    niveau=self.niveau,
                )
            )
        return signaux
