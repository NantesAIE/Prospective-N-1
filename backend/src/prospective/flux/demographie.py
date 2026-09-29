"""Profil démographique du territoire, pour ancrer les 100 personas synthétiques.

France avec code commune : INSEE Mélodi (recensement 2023, Filosofi). Ailleurs, ou si Mélodi
échoue : World Bank Indicators, à l'échelle du pays. Mode démo ou échec : fixture Nantes.
"""

import asyncio
import json
import logging

import httpx

from prospective.config import parametres
from prospective.flux.base import TIMEOUT_FLUX
from prospective.flux.outils import client_tls, rassembler
from prospective.modeles import Localisation

journal = logging.getLogger(__name__)

URL_MELODI = "https://api.insee.fr/melodi/data/"
URL_WORLD_BANK = "https://api.worldbank.org/v2/country/{pays}/indicator/{indicateurs}"

# Tranches du jeu DS_RP_POPULATION_PRINC, qui partitionnent la population totale
TRANCHES_INSEE = {
    "Y_LT15": "0-14",
    "Y15T24": "15-24",
    "Y25T39": "25-39",
    "Y40T54": "40-54",
    "Y55T64": "55-64",
    "Y65T79": "65-79",
    "Y_GE80": "80+",
}

# Groupes socioprofessionnels (PCS) du jeu DS_RP_TD_POPULATION_PCSAGESEX_COMP
PCS = {
    "1": "Agriculteurs exploitants",
    "2": "Artisans, commerçants, chefs d'entreprise",
    "3": "Cadres et professions intellectuelles supérieures",
    "4": "Professions intermédiaires",
    "5": "Employés",
    "6": "Ouvriers",
    "7": "Retraités",
    "9": "Autres personnes sans activité professionnelle",
}

INDICATEURS_WB = {
    "SP.POP.TOTL": "population",
    "SP.POP.0014.TO.ZS": "0-14",
    "SP.POP.1564.TO.ZS": "15-64",
    "SP.POP.65UP.TO.ZS": "65+",
    "NY.GNP.PCAP.CD": "rnb_par_habitant_usd",
    "SL.TLF.CACT.ZS": "taux_activite_15_plus_pct",
    "SL.UEM.TOTL.ZS": "taux_chomage_pct",
}


async def _melodi(client: httpx.AsyncClient, jeu: str, params: dict) -> tuple[list[dict], str]:
    reponse = await client.get(URL_MELODI + jeu, params=params)
    reponse.raise_for_status()
    return reponse.json()["observations"], str(reponse.url)


def _valeur(obs: dict) -> float | None:
    return obs["measures"]["OBS_VALUE_NIVEAU"].get("value")


async def _profil_insee(client: httpx.AsyncClient, loc: Localisation) -> dict:
    geo = f"COM-{loc.code_commune}"
    population, pcs, revenus = await rassembler(
        [
            _melodi(client, "DS_RP_POPULATION_PRINC", {"GEO": geo, "SEX": "_T", "maxResult": 500}),
            _melodi(
                client,
                "DS_RP_TD_POPULATION_PCSAGESEX_COMP",
                {"GEO": geo, "SEX": "_T", "AGE": "Y_GE15"},
            ),
            _melodi(client, "DS_FILOSOFI_CC", {"GEO": geo}),
        ]
    )
    if population is None:
        raise RuntimeError("Mélodi : population indisponible")

    observations, url = population
    annee = max(o["dimensions"]["TIME_PERIOD"] for o in observations)
    par_age = {
        o["dimensions"]["AGE"]: _valeur(o)
        for o in observations
        if o["dimensions"]["TIME_PERIOD"] == annee
    }
    total = par_age.get("_T")
    if not total:
        raise RuntimeError("Mélodi : population totale absente")
    profil = {
        "source": f"INSEE, recensement de la population {annee} (API Mélodi)",
        "url": url,
        "sources": [
            {
                "nom": "INSEE, évolution et structure de la population (DS_RP_POPULATION_PRINC)",
                "url": url,
            }
        ],
        "echelle": "commune",
        "territoire": f"{loc.ville} ({loc.code_commune})",
        "annee": annee,
        "population": round(total),
        "tranches_age_pct": {
            libelle: round(100 * par_age[code] / total, 1)
            for code, libelle in TRANCHES_INSEE.items()
            if par_age.get(code) is not None
        },
    }

    if pcs:
        observations_pcs, url_pcs = pcs
        valeurs = {o["dimensions"]["PCS"]: _valeur(o) for o in observations_pcs}
        total_15 = valeurs.get("_T")
        if total_15:
            profil["csp_15_ans_et_plus_pct"] = {
                libelle: round(100 * valeurs[code] / total_15, 1)
                for code, libelle in PCS.items()
                if valeurs.get(code) is not None
            }
            profil["sources"].append(
                {
                    "nom": "INSEE, population selon l'âge et la PCS (DS_RP_TD_POPULATION_PCSAGESEX_COMP)",
                    "url": url_pcs,
                }
            )

    if revenus:
        observations_rev, url_rev = revenus
        mesures = {o["dimensions"]["FILOSOFI_MEASURE"]: o for o in observations_rev}
        mediane, pauvrete = mesures.get("MED_SL"), mesures.get("PR_MD60")
        revenu = {}
        if mediane and _valeur(mediane) is not None:
            revenu["niveau_vie_median_eur_an"] = round(_valeur(mediane))
            revenu["annee"] = mediane["dimensions"]["TIME_PERIOD"]
        if pauvrete and _valeur(pauvrete) is not None:
            revenu["taux_pauvrete_60_pct"] = _valeur(pauvrete)
        if revenu:
            profil["revenu"] = revenu
            profil["sources"].append(
                {
                    "nom": "INSEE, Filosofi : niveau de vie et pauvreté (DS_FILOSOFI_CC)",
                    "url": url_rev,
                }
            )
    return profil


async def _profil_world_bank(client: httpx.AsyncClient, loc: Localisation) -> dict:
    # L'API accepte aussi l'ISO2, utile pour les pays hors table statique
    code_pays = loc.code_pays_iso3 or loc.code_pays
    if not code_pays:
        raise ValueError("Code pays inconnu")
    url = URL_WORLD_BANK.format(pays=code_pays, indicateurs=";".join(INDICATEURS_WB))
    reponse = await client.get(url, params={"format": "json", "source": 2, "mrnev": 1})
    reponse.raise_for_status()
    donnees = reponse.json()
    if len(donnees) < 2 or not donnees[1]:
        raise RuntimeError(f"World Bank : aucune donnée pour {code_pays}")
    valeurs = {
        INDICATEURS_WB[d["indicator"]["id"]]: (d["value"], d["date"])
        for d in donnees[1]
        if d["value"] is not None
    }
    population, annee = valeurs.get("population", (None, None))
    if population is None:
        raise RuntimeError("World Bank : population absente")
    profil = {
        "source": f"Banque mondiale, World Development Indicators ({annee})",
        "url": str(reponse.url),
        "sources": [
            {"nom": "Banque mondiale, World Development Indicators", "url": str(reponse.url)}
        ],
        "echelle": "pays",
        "territoire": loc.pays,
        "annee": annee,
        "population": round(population),
        "tranches_age_pct": {
            t: round(valeurs[t][0], 1) for t in ("0-14", "15-64", "65+") if t in valeurs
        },
    }
    activite = {
        cle: round(valeurs[cle][0], 1)
        for cle in ("taux_activite_15_plus_pct", "taux_chomage_pct")
        if cle in valeurs
    }
    if activite:
        profil["activite"] = activite
    if "rnb_par_habitant_usd" in valeurs:
        montant, annee_rnb = valeurs["rnb_par_habitant_usd"]
        profil["revenu"] = {"rnb_par_habitant_usd": round(montant), "annee": annee_rnb}
    return profil


def _fixture() -> dict:
    chemin = parametres().dossier_fixtures / "flux" / "demographie.json"
    if not chemin.exists():
        return {}
    return {**json.loads(chemin.read_text(encoding="utf-8")), "donnees_demo": True}


async def _profil_en_ligne(loc: Localisation) -> dict:
    async with client_tls() as client:
        if loc.code_pays == "FR" and loc.code_commune:
            try:
                return await _profil_insee(client, loc)
            except Exception as exc:  # noqa: BLE001 : on tente l'échelle nationale
                journal.warning("Mélodi en échec (%s), repli sur World Bank", exc)
        return await _profil_world_bank(client, loc)


async def profil_demographique(loc: Localisation) -> dict:
    """Profil du territoire : population, tranches d'âge (%), CSP ou activité, revenu.

    Chaque profil cite sa source réelle (`source`, `url`, `sources`). Il porte
    `donnees_demo: True` s'il provient du jeu de secours (Nantes).
    """
    if parametres().demo:
        return _fixture()
    try:
        profil = await asyncio.wait_for(_profil_en_ligne(loc), TIMEOUT_FLUX)
        return {**profil, "donnees_demo": False}
    except Exception as exc:  # noqa: BLE001 : tout échec bascule sur le jeu de secours
        journal.warning("Profil démographique en échec (%s), bascule sur la fixture", exc)
        return _fixture()
