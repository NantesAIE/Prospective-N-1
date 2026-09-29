"""BOAMP (Opendatasoft) : marchés publics, révélateurs des priorités des collectivités."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.outils import (
    aujourdhui,
    date_iso,
    nombre,
    pertinence,
    phrase,
    rassembler,
    termes,
)
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
SOURCE = "BOAMP (DILA)"
MAX_AVIS = 10
CHAMPS = (
    "idweb,objet,nomacheteur,dateparution,datelimitereponse,nature_libelle,"
    "descripteur_libelle,type_marche,titulaire,url_avis"
)


def _liste(valeur) -> list[str]:
    if isinstance(valeur, list):
        return [str(v) for v in valeur if v]
    return [str(valeur)] if valeur else []


class Boamp(Flux):
    id = "boamp"
    nom = "BOAMP (marchés publics)"
    description = "Avis de marchés publics du département : ce que les collectivités achètent."
    axes: ClassVar[list[Axe]] = [Axe.P]
    niveau = Niveau.PAYS
    pays: ClassVar[list[str] | None] = ["FR"]

    async def _requete(self, client: httpx.AsyncClient, params: dict) -> tuple[dict, str]:
        reponse = await client.get(URL, params=params)
        reponse.raise_for_status()
        return reponse.json(), str(reponse.url)

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        liste = [t.replace('"', "") for t in termes(ctx, requete)]
        loc = ctx.localisation
        depuis = (datetime.now(UTC) - timedelta(days=365)).date().isoformat()
        recherche = " OR ".join(f'search("{t}")' for t in liste)
        filtres = [f"({recherche})", f"dateparution >= date'{depuis}'"]
        if loc.code_departement:
            filtres.append(f'code_departement="{loc.code_departement}"')
        where = " AND ".join(filtres)

        synthese, avis = await rassembler(
            [
                self._requete(
                    client,
                    {"where": where, "group_by": "nature_libelle", "select": "count(*) as n"},
                ),
                self._requete(
                    client,
                    {
                        "where": where,
                        "order_by": "dateparution desc",
                        "limit": 60,
                        "select": CHAMPS,
                    },
                ),
            ]
        )
        if synthese is None and avis is None:
            raise RuntimeError("BOAMP : aucune réponse")

        territoire = loc.departement or "France"
        signaux: list[SignalBrut] = []
        resultats = avis[0]["results"] if avis else []
        if synthese and synthese[0]["results"]:
            comptes = sorted(synthese[0]["results"], key=lambda r: -r["n"])
            total = sum(r["n"] for r in comptes)
            detail = ", ".join(f"{r['nature_libelle'].lower()} : {nombre(r['n'])}" for r in comptes)
            acheteurs = Counter(a.get("nomacheteur") for a in resultats if a.get("nomacheteur"))
            principaux = ", ".join(f"{nom} ({n})" for nom, n in acheteurs.most_common(3))
            resume = (
                f"Depuis le {depuis}, {nombre(total)} avis BOAMP ({territoire}) mentionnent "
                f"{', '.join(liste)} ({detail})"
            )
            if principaux:
                resume += f" ; acheteurs les plus actifs : {principaux}"
            signaux.append(
                self._signal(
                    f"Commande publique liée au thème sur 12 mois ({territoire})",
                    resume + ".",
                    synthese[1],
                    aujourdhui(),
                )
            )

        # Un même marché paraît souvent deux fois (avis puis résultat) : on garde le plus récent
        uniques: dict[tuple, dict] = {}
        for a in resultats:
            uniques.setdefault((a.get("nomacheteur"), a.get("objet")), a)
        notes = [
            (
                pertinence(
                    f"{a.get('objet')} {' '.join(_liste(a.get('descripteur_libelle')))}", liste
                ),
                a,
            )
            for a in uniques.values()
        ]
        notes.sort(key=lambda n: n[0], reverse=True)
        # Le plein texte porte aussi sur le corps de l'avis : on écarte les objets sans rapport,
        # sauf s'il ne resterait presque rien
        pertinents = [a for note, a in notes if note > 0]
        if len(pertinents) < 3:
            pertinents = [a for _, a in notes]
        for a in pertinents[:MAX_AVIS]:
            signaux.append(self._signal_avis(a))
        return signaux

    def _signal_avis(self, avis: dict) -> SignalBrut:
        objet = phrase(avis.get("objet") or "Objet non précisé", 180)
        acheteur = avis.get("nomacheteur") or "acheteur non précisé"
        nature = avis.get("nature_libelle") or "Avis"
        parution = date_iso(avis.get("dateparution"))
        morceaux = [f"{nature} publié au BOAMP le {parution} par {acheteur} : « {objet} »"]
        if categories := _liste(avis.get("descripteur_libelle")):
            morceaux.append(f"catégories {', '.join(categories[:4])}")
        if types := _liste(avis.get("type_marche")):
            morceaux.append(f"marché de {', '.join(types).lower()}")
        if limite := date_iso(avis.get("datelimitereponse")):
            morceaux.append(f"réponse attendue avant le {limite}")
        if titulaire := ", ".join(_liste(avis.get("titulaire"))):
            morceaux.append(f"attribué à {titulaire}")
        return self._signal(
            f"{acheteur} : {objet}",
            " ; ".join(morceaux) + ".",
            avis.get("url_avis") or URL,
            parution,
        )

    def _signal(self, titre: str, resume: str, url: str, date: str) -> SignalBrut:
        return SignalBrut(
            titre=titre,
            resume=resume,
            source=SOURCE,
            url=url,
            date=date,
            axe_presume=Axe.P,
            flux_id=self.id,
            niveau=self.niveau,
        )
