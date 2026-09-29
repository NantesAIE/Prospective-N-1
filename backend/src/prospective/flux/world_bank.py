"""World Bank Indicators : indicateurs sociaux et économiques du pays, avec tendance sur 10 ans."""

from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.outils import annee_courante, aujourdhui, nombre, signe
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://api.worldbank.org/v2/country/{pays}/indicator/{indicateurs}"
URL_INDICATEUR = (
    "https://api.worldbank.org/v2/country/{pays}/indicator/{code}?format=json&date={debut}:{fin}"
)
SOURCE = "Banque mondiale, World Development Indicators"

# code : (libellé, unité, axe, tendance en écart de niveau ou en moyenne annuelle)
INDICATEURS = {
    "SP.POP.65UP.TO.ZS": ("Part des 65 ans et plus", "%", Axe.S, "ecart"),
    "SP.DYN.LE00.IN": ("Espérance de vie à la naissance", "ans", Axe.S, "ecart"),
    "SH.XPD.CHEX.GD.ZS": ("Dépenses courantes de santé", "% du PIB", Axe.S, "ecart"),
    "SP.URB.TOTL.IN.ZS": ("Taux d'urbanisation", "%", Axe.S, "ecart"),
    "NY.GDP.MKTP.KD.ZG": ("Croissance du PIB réel", "%", Axe.E1, "moyenne"),
    "SL.UEM.TOTL.ZS": ("Taux de chômage (estimation OIT)", "%", Axe.E1, "ecart"),
}


class WorldBank(Flux):
    id = "world_bank"
    nom = "World Bank Indicators"
    description = "Vieillissement, santé, urbanisation, croissance et chômage du pays, sur 10 ans."
    axes: ClassVar[list[Axe]] = [Axe.S, Axe.E1]
    niveau = Niveau.MONDE
    interrogeable = False

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        loc = ctx.localisation
        # L'API accepte aussi l'ISO2, utile pour les pays hors table statique
        code_pays = loc.code_pays_iso3 or loc.code_pays
        if not code_pays:
            raise ValueError("Code pays inconnu")
        fin = annee_courante()
        debut = fin - 13
        reponse = await client.get(
            URL.format(pays=code_pays, indicateurs=";".join(INDICATEURS)),
            params={"format": "json", "source": 2, "date": f"{debut}:{fin}", "per_page": 500},
        )
        reponse.raise_for_status()
        donnees = reponse.json()
        if len(donnees) < 2 or not donnees[1]:
            raise RuntimeError(f"World Bank : aucune donnée pour {code_pays}")

        series: dict[str, dict[int, float]] = {}
        for point in donnees[1]:
            if point["value"] is not None:
                series.setdefault(point["indicator"]["id"], {})[int(point["date"])] = point["value"]

        signaux = []
        for code, (libelle, unite, axe, tendance) in INDICATEURS.items():
            serie = series.get(code)
            if not serie:
                continue
            annee = max(serie)
            valeur = serie[annee]
            base = annee - 10
            if tendance == "moyenne":
                valeurs = [v for a, v in serie.items() if base < a <= annee]
                evolution = (
                    f"moyenne de {nombre(sum(valeurs) / len(valeurs), 1)} % par an "
                    f"sur {annee - base} ans"
                )
            elif base in serie:
                ecart = valeur - serie[base]
                unite_ecart = "points" if "%" in unite else unite
                evolution = (
                    f"{signe(ecart)} {unite_ecart} en 10 ans ({nombre(serie[base], 1)} en {base})"
                )
            else:
                evolution = "tendance sur 10 ans indisponible"
            signaux.append(
                SignalBrut(
                    titre=f"{loc.pays} : {libelle[0].lower()}{libelle[1:]} à {nombre(valeur, 1)} {unite} en {annee}",
                    resume=f"{libelle} ({loc.pays}) : {nombre(valeur, 1)} {unite} en {annee}, {evolution}.",
                    source=SOURCE,
                    url=URL_INDICATEUR.format(pays=code_pays, code=code, debut=debut, fin=fin),
                    date=aujourdhui(),
                    axe_presume=axe,
                    flux_id=self.id,
                    niveau=self.niveau,
                )
            )
        return signaux
