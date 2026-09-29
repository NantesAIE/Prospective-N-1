"""OpenAlex : publications scientifiques récentes et les plus citées sur le sujet."""

import os
from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.outils import annee_courante, date_iso, phrase, termes
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://api.openalex.org/works"
SOURCE = "OpenAlex"
PAR_CRITERE = 6  # 6 plus citées + 6 plus récentes
ANNEES = 5


def resume_openalex(index_inverse: dict | None) -> str:
    """Reconstitue le résumé à partir de l'index inversé d'OpenAlex."""
    if not index_inverse:
        return ""
    positions = {p: mot for mot, liste in index_inverse.items() for p in liste}
    return " ".join(positions[p] for p in sorted(positions))


class OpenAlex(Flux):
    id = "openalex"
    nom = "OpenAlex (publications scientifiques)"
    description = (
        "Articles scientifiques des 5 dernières années : les plus cités et les plus récents."
    )
    axes: ClassVar[list[Axe]] = [Axe.T]
    niveau = Niveau.MONDE
    # Sans clé, quota gratuit quotidien (environ 100 recherches) ; OPENALEX_API_KEY facultative
    cle_requise = False

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        liste = [t.replace(",", " ").replace('"', "") for t in termes(ctx, requete, anglais=True)]
        expression = " OR ".join(f'"{t}"' if " " in t else t for t in liste)
        depuis = f"{annee_courante() - ANNEES}-01-01"
        params = {
            "filter": f"title_and_abstract.search:{expression},from_publication_date:{depuis}",
            "per_page": 50,
            "select": "id,doi,display_name,publication_date,cited_by_count,"
            "primary_location,primary_topic,abstract_inverted_index",
        }
        if cle := os.environ.get("OPENALEX_API_KEY"):
            params["api_key"] = cle
        reponse = await client.get(URL, params=params)
        reponse.raise_for_status()
        travaux = [t for t in reponse.json().get("results", []) if t.get("display_name")]

        cites = sorted(travaux, key=lambda t: t.get("cited_by_count") or 0, reverse=True)
        recents = sorted(travaux, key=lambda t: t.get("publication_date") or "", reverse=True)
        choisis = {t["id"]: t for t in cites[:PAR_CRITERE]}
        for t in recents:
            if len(choisis) >= 2 * PAR_CRITERE:
                break
            choisis.setdefault(t["id"], t)
        return [self._signal(t) for t in choisis.values()]

    def _signal(self, travail: dict) -> SignalBrut:
        emplacement = travail.get("primary_location") or {}
        revue = (emplacement.get("source") or {}).get("display_name") or "revue non précisée"
        theme = (travail.get("primary_topic") or {}).get("display_name")
        date_pub = date_iso(travail.get("publication_date"))
        extrait = phrase(resume_openalex(travail.get("abstract_inverted_index")), 220)
        resume = (
            f"Publié le {date_pub} dans {revue}, cité {travail.get('cited_by_count') or 0} fois"
        )
        if theme:
            resume += f", thème « {theme} »"
        resume += f". {extrait}" if extrait else "."
        return SignalBrut(
            titre=travail["display_name"],
            resume=resume,
            source=f"{SOURCE} ({revue})",
            url=travail.get("doi") or emplacement.get("landing_page_url") or travail["id"],
            date=date_pub,
            axe_presume=Axe.T,
            flux_id=self.id,
            niveau=self.niveau,
        )
