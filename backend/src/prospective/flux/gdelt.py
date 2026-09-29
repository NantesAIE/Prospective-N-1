"""GDELT DOC 2.0 : articles de presse récents (3 mois), 65 langues, filtrables par pays."""

from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.outils import Limiteur, date_iso, termes
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://api.gdeltproject.org/api/v2/doc/doc"
MAX_SIGNAUX = 12

# GDELT refuse plus d'une requête toutes les 5 s par adresse IP (réponse 429)
_limiteur = Limiteur(5.5)


def _expression(liste: list[str]) -> str:
    # GDELT exige des guillemets pour les expressions et des parenthèses autour des OR
    morceaux = [f'"{t}"' if " " in t else t for t in (t.replace('"', "") for t in liste)]
    return morceaux[0] if len(morceaux) == 1 else "(" + " OR ".join(morceaux) + ")"


class Gdelt(Flux):
    id = "gdelt"
    nom = "GDELT (presse mondiale)"
    description = "Couverture médiatique récente d'un sujet, 65 langues, filtre par pays source."
    axes: ClassVar[list[Axe]] = [Axe.P]
    niveau = Niveau.MONDE

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        francais = ctx.localisation.code_pays == "FR"
        requete_gdelt = _expression(termes(ctx, requete, anglais=not francais))
        if francais:
            requete_gdelt += " sourcecountry:FR"
        await _limiteur.attendre()
        reponse = await client.get(
            URL,
            params={
                "query": requete_gdelt,
                "mode": "ArtList",
                "format": "json",
                "timespan": "3months",
                "maxrecords": 50,
                "sort": "HybridRel",
            },
        )
        if reponse.status_code == 429:
            raise RuntimeError("GDELT : limite de débit atteinte (429)")
        reponse.raise_for_status()
        if "json" not in reponse.headers.get("content-type", ""):
            # Les erreurs de syntaxe arrivent en texte brut avec un code 200
            raise ValueError(f"GDELT : {reponse.text.strip()[:200]}")

        signaux, titres_vus = [], set()
        for article in reponse.json().get("articles", []):
            titre = (article.get("title") or "").strip()
            if not titre or titre.lower() in titres_vus:
                continue
            titres_vus.add(titre.lower())
            date = date_iso(article.get("seendate"))
            domaine = article.get("domain") or "source inconnue"
            signaux.append(
                SignalBrut(
                    titre=titre,
                    resume=(
                        f"Article de {domaine} ({article.get('sourcecountry') or 'pays inconnu'}, "
                        f"{article.get('language') or 'langue inconnue'}) repéré par GDELT "
                        f"le {date} sur la requête {requete_gdelt}."
                    ),
                    source=f"{domaine} via GDELT",
                    url=article["url"],
                    date=date,
                    axe_presume=Axe.P,
                    flux_id=self.id,
                    niveau=self.niveau,
                )
            )
            if len(signaux) == MAX_SIGNAUX:
                break
        return signaux
