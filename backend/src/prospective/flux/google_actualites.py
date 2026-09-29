"""Google Actualités (flux RSS de recherche) : ce que dit la presse, nationale et locale.

Remplace GDELT, inutilisable derrière le proxy d'entreprise. Les liens sont ceux du flux
(redirections news.google.com vers l'article). Le flux est réservé à un usage personnel
et non commercial selon Google : acceptable pour une démonstration interne.
"""

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.outils import entrelacer, rassembler, sans_accents, termes
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://news.google.com/rss/search"
MAX_SIGNAUX = 12
PAYS_FRANCOPHONES = {"FR", "BE", "CH", "LU", "MA"}

# Un titre ou un média qui évoque l'action publique est présumé Politique ;
# sinon, l'axe reste à qualifier par le LLM
MOTS_POLITIQUES = re.compile(
    r"\b(gouvernement|ministre|ministere|loi|decret|reforme|plan|politique|senat|assemblee|"
    r"depute|elus?|maire|mairie|municipal\w*|metropole|agglo\w*|departement\w*|region\w*|"
    r"collectivit\w*|prefe\w*|subvention\w*|budget|etat|europe\w*|appel a projets|"
    r"conseil|ars|assurance maladie|securite sociale|remboursement\w*|label\w*|dispositif\w*|"
    r"programme\w*|pass|ville|gouv|maisons? sport.sante)\b"
)


def _edition(code_pays: str) -> dict:
    if code_pays in PAYS_FRANCOPHONES:
        return {"hl": "fr", "gl": code_pays, "ceid": f"{code_pays}:fr"}
    return {"hl": "en-US", "gl": "US", "ceid": "US:en"}


def _date(valeur: str | None) -> str:
    try:
        return parsedate_to_datetime(valeur).date().isoformat() if valeur else ""
    except (TypeError, ValueError):
        return ""


class GoogleActualites(Flux):
    id = "google_actualites"
    nom = "Google Actualités (presse)"
    description = "Articles de presse récents sur le sujet, nationaux et locaux, avec leur média."
    axes: ClassVar[list[Axe]] = [Axe.P]
    niveau = Niveau.MONDE

    async def _chercher(self, client: httpx.AsyncClient, q: str, edition: dict) -> list[dict]:
        reponse = await client.get(URL, params={"q": q, **edition})
        reponse.raise_for_status()
        articles = []
        for item in ET.fromstring(reponse.content).findall("./channel/item"):
            source = item.find("source")
            media = (source.text or "").strip() if source is not None else ""
            titre = (item.findtext("title") or "").strip()
            # Google suffixe le titre par « - Média »
            if media and titre.endswith(media):
                titre = titre[: -len(media)].rstrip(" -|–")
            lien = (item.findtext("link") or "").strip()
            if titre and lien:
                articles.append(
                    {
                        "titre": titre,
                        "lien": lien,
                        "media": media,
                        "date": _date(item.findtext("pubDate")),
                        "requete": q,
                    }
                )
        return articles

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        loc = ctx.localisation
        edition = _edition(loc.code_pays)
        francophone = loc.code_pays in PAYS_FRANCOPHONES
        liste = [t.replace('"', "") for t in termes(ctx, requete, anglais=not francophone)]
        expression = " OR ".join(f'"{t}"' if " " in t else t for t in liste)
        recherches = [self._chercher(client, expression, edition)]
        if loc.ville:
            # Presse locale : premier terme et nom de la ville
            recherches.append(self._chercher(client, f"{liste[0]} {loc.ville}", edition))
        resultats = await rassembler(recherches)
        if all(r is None for r in resultats):
            raise RuntimeError("Google Actualités : aucune réponse")

        signaux, vus = [], set()
        for article in entrelacer([r for r in resultats if r]):
            cle = sans_accents(article["titre"])
            if cle in vus:
                continue
            vus.add(cle)
            media = article["media"] or "média non précisé"
            # Le média compte aussi : site d'une ville, d'une ARS, d'un ministère…
            politique = MOTS_POLITIQUES.search(sans_accents(f"{article['titre']} {media}"))
            signaux.append(
                SignalBrut(
                    titre=article["titre"],
                    resume=(
                        f"Article de {media} publié le {article['date'] or 'date inconnue'} "
                        f"et référencé par Google Actualités pour la recherche {article['requete']}."
                    ),
                    source=f"{media} via Google Actualités",
                    url=article["lien"],
                    date=article["date"],
                    axe_presume=Axe.P if politique else None,
                    flux_id=self.id,
                    niveau=self.niveau,
                )
            )
            if len(signaux) == MAX_SIGNAUX:
                break
        return signaux
