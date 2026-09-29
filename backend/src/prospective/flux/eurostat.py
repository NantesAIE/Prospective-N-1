"""Eurostat (API statistics JSON-stat) : vieillissement, projections et activité physique, pays et UE."""

from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.outils import (
    annee_courante,
    aujourdhui,
    nombre,
    rassembler,
    sans_accents,
    signe,
)
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
SOURCE = "Eurostat"
UE = "EU27_2020"
# Eurostat utilise EL pour la Grèce et UK pour le Royaume-Uni
CODES_EUROSTAT = {"GR": "EL", "GB": "UK"}
MOTS_SANTE = ("sante", "sport", "activite physique", "bien-etre", "senior", "vieillissement")


class Cube:
    """Lecture d'une réponse JSON-stat : valeur par combinaison de codes."""

    def __init__(self, donnees: dict):
        self.dims = donnees["id"]
        self.index = {d: donnees["dimension"][d]["category"]["index"] for d in self.dims}
        self.valeurs = donnees["value"]
        self.libelles = {d: donnees["dimension"][d]["category"].get("label", {}) for d in self.dims}
        self.pas = []
        pas = 1
        for taille in reversed(donnees["size"]):
            self.pas.insert(0, pas)
            pas *= taille

    def valeur(self, **codes: str) -> float | None:
        position = 0
        for dim, pas in zip(self.dims, self.pas, strict=True):
            index = self.index[dim]
            code = codes.get(dim) or next(iter(index))  # dimension à une seule modalité
            if code not in index:
                return None
            position += index[code] * pas
        return self.valeurs.get(str(position))

    def annees(self) -> list[str]:
        return sorted(self.index["time"])


class Eurostat(Flux):
    id = "eurostat"
    nom = "Eurostat (statistiques UE)"
    description = (
        "Vieillissement, projections de population et activité physique : pays et UE à 27."
    )
    axes: ClassVar[list[Axe]] = [Axe.S, Axe.E1]
    niveau = Niveau.ZONE
    zone = "UE"
    interrogeable = False

    async def _cube(self, client: httpx.AsyncClient, jeu: str, params: dict) -> tuple[Cube, str]:
        reponse = await client.get(URL + jeu, params={"lang": "fr", **params})
        reponse.raise_for_status()
        return Cube(reponse.json()), str(reponse.url)

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        loc = ctx.localisation
        geo = CODES_EUROSTAT.get(loc.code_pays, loc.code_pays) or UE
        annee = annee_courante()
        horizon = min(max(ctx.saisie.horizon, annee + 5), 2100)
        contexte = sans_accents(" ".join([ctx.saisie.thematique, *ctx.mots_cles]))
        sante = any(m in contexte for m in MOTS_SANTE)

        taches = [
            self._cube(
                client,
                "demo_pjanind",
                {
                    "geo": [geo, UE],
                    "indic_de": ["PC_Y65_MAX", "PC_Y80_MAX"],
                    "sinceTimePeriod": str(annee - 12),
                },
            ),
            self._cube(
                client,
                "proj_23np",
                {
                    "geo": geo,
                    "projection": "BSL",
                    "sex": "T",
                    "unit": "PER",
                    "age": ["TOTAL", "Y_GE65", "Y_GE80"],
                    "time": [str(annee), str(horizon)],
                },
            ),
        ]
        if sante:
            taches.append(
                self._cube(
                    client,
                    "hlth_ehis_pe9e",
                    {
                        "geo": [geo, UE],
                        "physact": "MV_AERO",
                        "isced11": "TOTAL",
                        "sex": "T",
                        "age": ["Y18-64", "Y65-74", "Y_GE75"],
                        "lastTimePeriod": 1,
                    },
                )
            )
        structure, projection, *activite = await rassembler(taches)
        if structure is None and projection is None:
            raise RuntimeError("Eurostat : aucune réponse")

        pays = loc.pays if geo != UE else "UE"
        signaux: list[SignalBrut] = []

        def ajouter(titre: str, resume: str, url: str, axe: Axe = Axe.S) -> None:
            signaux.append(
                SignalBrut(
                    titre=titre,
                    resume=resume,
                    source=SOURCE,
                    url=url,
                    date=aujourdhui(),
                    axe_presume=axe,
                    flux_id=self.id,
                    niveau=self.niveau,
                )
            )

        if structure:
            cube, url = structure
            for indic, libelle in (
                ("PC_Y65_MAX", "65 ans et plus"),
                ("PC_Y80_MAX", "80 ans et plus"),
            ):
                annees = [a for a in cube.annees() if cube.valeur(indic_de=indic, geo=geo, time=a)]
                if not annees:
                    continue
                recente = annees[-1]
                valeur = cube.valeur(indic_de=indic, geo=geo, time=recente)
                ancienne = str(int(recente) - 10)
                avant = cube.valeur(indic_de=indic, geo=geo, time=ancienne)
                ue = cube.valeur(indic_de=indic, geo=UE, time=recente)
                resume = f"Part des {libelle} ({pays}) : {nombre(valeur, 1)} % en {recente}"
                if avant is not None:
                    resume += f", {signe(valeur - avant)} points depuis {ancienne}"
                if ue is not None and geo != UE:
                    resume += f", contre {nombre(ue, 1)} % pour l'UE à 27"
                ajouter(
                    f"{pays} : {nombre(valeur, 1)} % de {libelle} en {recente}", resume + ".", url
                )

        if projection:
            cube, url = projection
            debut, fin = str(annee), str(horizon)
            v65 = [cube.valeur(age="Y_GE65", time=t) for t in (debut, fin)]
            total = [cube.valeur(age="TOTAL", time=t) for t in (debut, fin)]
            v80 = [cube.valeur(age="Y_GE80", time=t) for t in (debut, fin)]
            if all(v65) and all(total):
                croissance = 100 * (v65[1] - v65[0]) / v65[0]
                resume = (
                    f"Selon les projections de référence Eurostat (EUROPOP2023), les 65 ans et plus "
                    f"({pays}) passeraient de {nombre(v65[0] / 1e6, 1)} à {nombre(v65[1] / 1e6, 1)} "
                    f"millions entre {debut} et {fin} ({signe(croissance)} %), soit "
                    f"{nombre(100 * v65[1] / total[1], 1)} % de la population"
                )
                if all(v80):
                    resume += (
                        f" ; les 80 ans et plus atteindraient {nombre(v80[1] / 1e6, 1)} millions"
                    )
                ajouter(
                    f"{pays} : {signe(croissance, 0)} % de personnes de 65 ans et plus d'ici {fin}",
                    resume + ".",
                    url,
                )

        if activite and activite[0]:
            cube, url = activite[0]
            recente = cube.annees()[-1]
            tranches = {"Y18-64": "18-64 ans", "Y65-74": "65-74 ans", "Y_GE75": "75 ans et plus"}
            morceaux = []
            for code, libelle in tranches.items():
                v, ue = cube.valeur(age=code, geo=geo), cube.valeur(age=code, geo=UE)
                if v is not None:
                    morceaux.append(
                        f"{nombre(v, 1)} % des {libelle}"
                        + (f" (UE : {nombre(ue, 1)} %)" if ue is not None and geo != UE else "")
                    )
            if morceaux:
                ajouter(
                    f"{pays} : pratique d'une activité physique aérobie suffisante par âge ({recente})",
                    f"Selon l'enquête EHIS {recente}, pratiquent une activité physique aérobie "
                    f"suffisante pour avoir un impact positif sur la santé ({pays}) : "
                    + ", ".join(morceaux)
                    + ".",
                    url,
                )
        return signaux
