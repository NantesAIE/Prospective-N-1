"""Open-Meteo Climate API : projections CMIP6 (HighResMIP) jusqu'en 2050, par coordonnées."""

from statistics import mean
from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.geo import pays_par_iso2
from prospective.flux.outils import aujourdhui, nombre, signe
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://climate-api.open-meteo.com/v1/climate"
SOURCE = "Open-Meteo Climate API (modèles CMIP6)"
MODELES = ("EC_Earth3P_HR", "MPI_ESM1_2_XR", "MRI_AGCM3_2_S")
PERIODE_REF = (2015, 2024)
PERIODE_PROJ = (2035, 2044)
SEUIL_CHALEUR = 30.0


def _par_annee(dates: list[str], valeurs: list, debut: int, fin: int) -> dict[int, list[float]]:
    annees: dict[int, list[float]] = {}
    for jour, v in zip(dates, valeurs, strict=True):
        annee = int(jour[:4])
        if debut <= annee <= fin and v is not None:
            annees.setdefault(annee, []).append(v)
    return annees


def _indicateurs(dates: list[str], tmax: list, pluie: list, periode: tuple[int, int]) -> dict:
    t = _par_annee(dates, tmax, *periode)
    p = _par_annee(dates, pluie, *periode)
    ete = _par_annee(
        [d for d in dates if d[5:7] in ("06", "07", "08")],
        [v for d, v in zip(dates, pluie, strict=True) if d[5:7] in ("06", "07", "08")],
        *periode,
    )
    return {
        "tmax": mean(mean(v) for v in t.values()),
        "jours_chauds": mean(sum(1 for x in v if x > SEUIL_CHALEUR) for v in t.values()),
        "pluie": mean(sum(v) for v in p.values()),
        "pluie_ete": mean(sum(v) for v in ete.values()),
    }


class OpenMeteoClimat(Flux):
    id = "open_meteo_climat"
    nom = "Open-Meteo Climat (projections CMIP6)"
    description = "Écarts climatiques projetés entre 2015-2024 et 2035-2044 : chaleur, pluie."
    axes: ClassVar[list[Axe]] = [Axe.E2]
    niveau = Niveau.MONDE
    interrogeable = False

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        loc = ctx.localisation
        if loc.lat is not None and loc.lon is not None:
            lat, lon, lieu, niveau = loc.lat, loc.lon, loc.ville or loc.pays, Niveau.LOCAL
        else:
            # Sans coordonnées, on se place sur la capitale du pays
            pays = pays_par_iso2(loc.code_pays)
            if pays is None:
                raise ValueError("Ni coordonnées ni capitale connue pour ce pays")
            lat, lon, lieu, niveau = (
                pays.lat,
                pays.lon,
                f"{pays.capitale} ({pays.nom})",
                self.niveau,
            )

        reponse = await client.get(
            URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": f"{PERIODE_REF[0]}-01-01",
                "end_date": f"{PERIODE_PROJ[1]}-12-31",
                "models": ",".join(MODELES),
                "daily": "temperature_2m_max,precipitation_sum",
            },
        )
        reponse.raise_for_status()
        quotidien = reponse.json()["daily"]
        dates = quotidien["time"]

        ref, proj = [], []
        for modele in MODELES:
            tmax = quotidien.get(f"temperature_2m_max_{modele}")
            pluie = quotidien.get(f"precipitation_sum_{modele}")
            if not tmax or not pluie:
                continue
            ref.append(_indicateurs(dates, tmax, pluie, PERIODE_REF))
            proj.append(_indicateurs(dates, tmax, pluie, PERIODE_PROJ))
        if not ref:
            raise RuntimeError("Open-Meteo Climat : aucune série exploitable")

        # Moyenne d'ensemble des modèles disponibles
        a = {k: mean(r[k] for r in ref) for k in ref[0]}
        b = {k: mean(p[k] for p in proj) for k in proj[0]}
        periodes = f"entre {PERIODE_REF[0]}-{PERIODE_REF[1]} et {PERIODE_PROJ[0]}-{PERIODE_PROJ[1]}"
        modeles = f"moyenne de {len(ref)} modèles CMIP6"
        url = str(reponse.url)

        def signal(titre: str, resume: str) -> SignalBrut:
            return SignalBrut(
                titre=titre,
                resume=resume,
                source=SOURCE,
                url=url,
                date=aujourdhui(),
                axe_presume=Axe.E2,
                flux_id=self.id,
                niveau=niveau,
            )

        ecart_pluie = 100 * (b["pluie"] - a["pluie"]) / a["pluie"]
        ecart_ete = 100 * (b["pluie_ete"] - a["pluie_ete"]) / a["pluie_ete"]
        return [
            signal(
                f"{lieu} : température maximale moyenne {signe(b['tmax'] - a['tmax'])} °C d'ici 2040",
                f"La température maximale quotidienne moyenne passerait de {nombre(a['tmax'], 1)} °C "
                f"à {nombre(b['tmax'], 1)} °C {periodes} ({modeles}).",
            ),
            signal(
                f"{lieu} : {nombre(b['jours_chauds'], 1)} jours par an au-dessus de 30 °C "
                f"vers 2040",
                f"Le nombre moyen de jours à plus de 30 °C passerait de "
                f"{nombre(a['jours_chauds'], 1)} à {nombre(b['jours_chauds'], 1)} par an "
                f"{periodes} ({modeles}).",
            ),
            signal(
                f"{lieu} : cumul annuel de pluie {signe(ecart_pluie)} % d'ici 2040",
                f"Les précipitations annuelles passeraient de {nombre(a['pluie'])} mm à "
                f"{nombre(b['pluie'])} mm {periodes} ({modeles}).",
            ),
            signal(
                f"{lieu} : pluie estivale {signe(ecart_ete)} % d'ici 2040",
                f"Les précipitations de juin à août passeraient de {nombre(a['pluie_ete'])} mm à "
                f"{nombre(b['pluie_ete'])} mm {periodes} ({modeles}).",
            ),
        ]
