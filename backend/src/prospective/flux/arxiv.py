"""arXiv : prépublications, signaux scientifiques très précoces.

Source principale : l'API arXiv (flux Atom). Derrière le proxy d'entreprise, arXiv répond
406 à toute requête absente de son cache ; on interroge alors les mêmes prépublications
via OpenAlex, restreint à la source arXiv.
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.openalex import URL as URL_OPENALEX
from prospective.flux.openalex import resume_openalex
from prospective.flux.outils import Limiteur, annee_courante, date_iso, phrase, termes
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

journal = logging.getLogger(__name__)

URL = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
SOURCE_OPENALEX_ARXIV = "S4306400194"  # « arXiv (Cornell University) » dans OpenAlex
MAX_SIGNAUX = 12
ANNEES = 4

# arXiv demande au moins 3 s entre deux requêtes
_limiteur = Limiteur(3.0)


class Arxiv(Flux):
    id = "arxiv"
    nom = "arXiv (prépublications)"
    description = "Prépublications scientifiques récentes, souvent en avance sur les revues."
    axes: ClassVar[list[Axe]] = [Axe.T]
    niveau = Niveau.MONDE

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        liste = [t.replace('"', "") for t in termes(ctx, requete, anglais=True)]
        try:
            return await self._api_arxiv(client, liste)
        except (httpx.HTTPStatusError, ET.ParseError) as exc:
            journal.info("API arXiv indisponible (%s), repli sur OpenAlex", exc)
            return await self._via_openalex(client, liste)

    async def _api_arxiv(self, client: httpx.AsyncClient, liste: list[str]) -> list[SignalBrut]:
        expression = " OR ".join(f'all:"{t}"' if " " in t else f"all:{t}" for t in liste)
        await _limiteur.attendre()
        reponse = await client.get(
            URL,
            params={"search_query": expression, "sortBy": "relevance", "max_results": MAX_SIGNAUX},
        )
        reponse.raise_for_status()
        signaux = []
        for entree in ET.fromstring(reponse.content).findall("a:entry", NS):
            titre = " ".join(entree.findtext("a:title", "", NS).split())
            lien = entree.findtext("a:id", "", NS).strip()
            if not titre or not lien:
                continue
            date = date_iso(entree.findtext("a:published", "", NS))
            auteurs = len(entree.findall("a:author", NS))
            categorie = entree.find("arxiv:primary_category", NS)
            domaine = categorie.get("term") if categorie is not None else "catégorie inconnue"
            extrait = phrase(entree.findtext("a:summary", "", NS), 220)
            signaux.append(
                self._signal(
                    titre,
                    f"Prépublication arXiv du {date} ({domaine}, {auteurs} auteur(s)). {extrait}",
                    lien,
                    date,
                    "arXiv",
                )
            )
        return signaux

    async def _via_openalex(self, client: httpx.AsyncClient, liste: list[str]) -> list[SignalBrut]:
        # Termes entre parenthèses : chaque mot requis, sans exiger l'expression exacte
        expression = " OR ".join(f"({t.replace(',', ' ')})" for t in liste)
        params = {
            "filter": (
                f"primary_location.source.id:{SOURCE_OPENALEX_ARXIV},"
                f"title_and_abstract.search:{expression},"
                f"from_publication_date:{annee_courante() - ANNEES}-01-01"
            ),
            "per_page": 25,
            "select": "id,doi,display_name,publication_date,primary_location,authorships,"
            "primary_topic,abstract_inverted_index",
        }
        if cle := os.environ.get("OPENALEX_API_KEY"):
            params["api_key"] = cle
        reponse = await client.get(URL_OPENALEX, params=params)
        reponse.raise_for_status()

        signaux, titres = [], set()
        for travail in reponse.json().get("results", []):
            titre = travail.get("display_name")
            if not titre or titre.lower() in titres:
                continue  # OpenAlex recense parfois deux versions d'une même prépublication
            titres.add(titre.lower())
            date = date_iso(travail.get("publication_date"))
            theme = (travail.get("primary_topic") or {}).get("display_name") or "thème non précisé"
            auteurs = len(travail.get("authorships") or [])
            extrait = phrase(resume_openalex(travail.get("abstract_inverted_index")), 220)
            lien = (travail.get("primary_location") or {}).get("landing_page_url")
            signaux.append(
                self._signal(
                    titre,
                    f"Prépublication arXiv du {date} ({theme}, {auteurs} auteur(s)). {extrait}",
                    lien or travail.get("doi") or travail["id"],
                    date,
                    "arXiv (via OpenAlex)",
                )
            )
            if len(signaux) == MAX_SIGNAUX:
                break
        return signaux

    def _signal(self, titre: str, resume: str, url: str, date: str, source: str) -> SignalBrut:
        return SignalBrut(
            titre=titre,
            resume=resume.strip(),
            source=source,
            url=url,
            date=date,
            axe_presume=Axe.T,
            flux_id=self.id,
            niveau=self.niveau,
        )
