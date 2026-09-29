"""BODACC (Opendatasoft) : créations, cessions et procédures collectives du département."""

import json
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

URL = (
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "annonces-commerciales/records"
)
SOURCE = "BODACC (DILA)"
FAMILLES = {
    "creation": "Création",
    "vente": "Vente ou cession",
    "collective": "Procédure collective",
}
MAX_ANNONCES = 10


def _json(champ: str | None) -> dict:
    try:
        return json.loads(champ) if champ else {}
    except json.JSONDecodeError:
        return {}


def _activite(annonce: dict) -> str:
    etab = _json(annonce.get("listeetablissements")).get("etablissement") or {}
    if isinstance(etab, list):
        etab = etab[0] if etab else {}
    personne = _json(annonce.get("listepersonnes")).get("personne") or {}
    if isinstance(personne, list):
        personne = personne[0] if personne else {}
    return etab.get("activite") or personne.get("activite") or ""


def _detail(annonce: dict) -> str:
    """Nature du jugement (procédure collective) ou origine du fonds (cession)."""
    if annonce.get("familleavis") == "collective":
        return _json(annonce.get("jugement")).get("nature", "")
    etab = _json(annonce.get("listeetablissements")).get("etablissement") or {}
    if isinstance(etab, dict) and annonce.get("familleavis") == "vente":
        return etab.get("origineFonds", "")
    return ""


class Bodacc(Flux):
    id = "bodacc"
    nom = "BODACC (vie des entreprises)"
    description = "Créations, ventes et procédures collectives publiées au BODACC, par département."
    axes: ClassVar[list[Axe]] = [Axe.E1]
    niveau = Niveau.PAYS
    pays: ClassVar[list[str] | None] = ["FR"]

    async def _requete(self, client: httpx.AsyncClient, params: dict) -> tuple[dict, str]:
        reponse = await client.get(URL, params=params)
        reponse.raise_for_status()
        return reponse.json(), str(reponse.url)

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        liste = termes(ctx, requete)
        loc = ctx.localisation
        depuis = (datetime.now(UTC) - timedelta(days=365)).date().isoformat()
        recherche = " OR ".join(f'search("{t.replace(chr(34), "")}")' for t in liste)
        filtres = [f"({recherche})", f"dateparution >= date'{depuis}'"]
        if loc.code_departement:
            filtres.append(f'numerodepartement="{loc.code_departement}"')
        where = " AND ".join(filtres)
        familles = ", ".join(f'"{f}"' for f in FAMILLES)

        synthese, annonces = await rassembler(
            [
                self._requete(
                    client,
                    {"where": where, "group_by": "familleavis_lib", "select": "count(*) as n"},
                ),
                self._requete(
                    client,
                    {
                        "where": f"{where} AND familleavis in ({familles})",
                        "order_by": "dateparution desc",
                        "limit": 60,
                    },
                ),
            ]
        )
        if synthese is None and annonces is None:
            raise RuntimeError("BODACC : aucune réponse")

        territoire = loc.departement or "France"
        signaux = []
        if synthese:
            donnees, url = synthese
            comptes = sorted(donnees["results"], key=lambda r: -r["n"])
            if comptes:
                detail = ", ".join(
                    f"{r['familleavis_lib'].lower()} : {nombre(r['n'])}" for r in comptes
                )
                signaux.append(
                    SignalBrut(
                        titre=f"Vie des entreprises du secteur sur 12 mois ({territoire})",
                        resume=(
                            f"Depuis le {depuis}, les annonces BODACC ({territoire}) liées à "
                            f"{', '.join(liste)} comptent : {detail}."
                        ),
                        source=SOURCE,
                        url=url,
                        date=aujourdhui(),
                        axe_presume=Axe.E1,
                        flux_id=self.id,
                        niveau=self.niveau,
                    )
                )
        if annonces:
            resultats = annonces[0]["results"]
            # Le plein texte d'Opendatasoft est large : on privilégie les annonces pertinentes
            resultats.sort(
                key=lambda a: pertinence(f"{a.get('commercant')} {_activite(a)}", liste),
                reverse=True,
            )
            for annonce in resultats[:MAX_ANNONCES]:
                signaux.append(self._signal(annonce))
        return signaux

    def _signal(self, annonce: dict) -> SignalBrut:
        famille = FAMILLES.get(
            annonce.get("familleavis"), annonce.get("familleavis_lib") or "Annonce"
        )
        nom = annonce.get("commercant") or "Entreprise non nommée"
        ville = annonce.get("ville") or "?"
        parution = date_iso(annonce.get("dateparution"))
        activite = phrase(_activite(annonce), 160)
        detail = phrase(_detail(annonce), 120)
        morceaux = [f"{famille} publiée au BODACC le {parution} : {nom} à {ville}"]
        if detail:
            morceaux.append(detail.rstrip("."))
        if activite:
            morceaux.append(f"activité « {activite.rstrip('.')} »")
        return SignalBrut(
            titre=f"{famille} : {nom} ({ville})",
            resume=", ".join(morceaux) + ".",
            source=SOURCE,
            url=annonce.get("url_complete") or URL,
            date=parution,
            axe_presume=Axe.E1,
            flux_id=self.id,
            niveau=self.niveau,
        )
