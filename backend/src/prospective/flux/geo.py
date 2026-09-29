"""Géocodage de la saisie : pays, commune, coordonnées.

France avec code postal : API Géo. Ville : API Géo (France) ou Open-Meteo Geocoding.
Pays seul : table statique. Mode démo ou échec : fixture Nantes, sinon table statique.
"""

import asyncio
import json
import logging
import re
from typing import NamedTuple

import httpx

from prospective.config import parametres
from prospective.flux.base import TIMEOUT_FLUX
from prospective.flux.outils import client_tls, sans_accents
from prospective.modeles import Localisation, SaisieProjet

journal = logging.getLogger(__name__)

URL_API_GEO = "https://geo.api.gouv.fr/communes"
URL_OPEN_METEO = "https://geocoding-api.open-meteo.com/v1/search"
CHAMPS_API_GEO = "nom,code,centre,departement,region,population,codesPostaux"


class Pays(NamedTuple):
    nom: str
    iso2: str
    iso3: str
    capitale: str
    lat: float
    lon: float


_PAYS = [
    Pays("Allemagne", "DE", "DEU", "Berlin", 52.52, 13.405),
    Pays("Autriche", "AT", "AUT", "Vienne", 48.208, 16.373),
    Pays("Belgique", "BE", "BEL", "Bruxelles", 50.85, 4.352),
    Pays("Bulgarie", "BG", "BGR", "Sofia", 42.698, 23.322),
    Pays("Chypre", "CY", "CYP", "Nicosie", 35.186, 33.382),
    Pays("Croatie", "HR", "HRV", "Zagreb", 45.815, 15.982),
    Pays("Danemark", "DK", "DNK", "Copenhague", 55.676, 12.568),
    Pays("Espagne", "ES", "ESP", "Madrid", 40.417, -3.704),
    Pays("Estonie", "EE", "EST", "Tallinn", 59.437, 24.754),
    Pays("Finlande", "FI", "FIN", "Helsinki", 60.17, 24.938),
    Pays("France", "FR", "FRA", "Paris", 48.857, 2.352),
    Pays("Grèce", "GR", "GRC", "Athènes", 37.984, 23.728),
    Pays("Hongrie", "HU", "HUN", "Budapest", 47.498, 19.04),
    Pays("Irlande", "IE", "IRL", "Dublin", 53.35, -6.26),
    Pays("Italie", "IT", "ITA", "Rome", 41.903, 12.496),
    Pays("Lettonie", "LV", "LVA", "Riga", 56.95, 24.105),
    Pays("Lituanie", "LT", "LTU", "Vilnius", 54.687, 25.28),
    Pays("Luxembourg", "LU", "LUX", "Luxembourg", 49.611, 6.13),
    Pays("Malte", "MT", "MLT", "La Valette", 35.899, 14.514),
    Pays("Pays-Bas", "NL", "NLD", "Amsterdam", 52.368, 4.904),
    Pays("Pologne", "PL", "POL", "Varsovie", 52.23, 21.012),
    Pays("Portugal", "PT", "PRT", "Lisbonne", 38.722, -9.139),
    Pays("Tchéquie", "CZ", "CZE", "Prague", 50.075, 14.438),
    Pays("Roumanie", "RO", "ROU", "Bucarest", 44.427, 26.103),
    Pays("Slovaquie", "SK", "SVK", "Bratislava", 48.149, 17.107),
    Pays("Slovénie", "SI", "SVN", "Ljubljana", 46.057, 14.506),
    Pays("Suède", "SE", "SWE", "Stockholm", 59.329, 18.069),
    Pays("Royaume-Uni", "GB", "GBR", "Londres", 51.507, -0.128),
    Pays("États-Unis", "US", "USA", "Washington", 38.907, -77.037),
    Pays("Canada", "CA", "CAN", "Ottawa", 45.421, -75.697),
    Pays("Suisse", "CH", "CHE", "Berne", 46.948, 7.447),
    Pays("Maroc", "MA", "MAR", "Rabat", 34.021, -6.841),
]

CODES_UE = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "CY",
        "CZ",
        "DE",
        "DK",
        "EE",
        "ES",
        "FI",
        "FR",
        "GR",
        "HR",
        "HU",
        "IE",
        "IT",
        "LT",
        "LU",
        "LV",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SE",
        "SI",
        "SK",
    }
)

_ALIAS = {
    "republique tcheque": "CZ",
    "etats unis d amerique": "US",
    "usa": "US",
    "uk": "GB",
    "angleterre": "GB",
    "grande bretagne": "GB",
    "hollande": "NL",
}


def _cle(texte: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", sans_accents(texte)).strip()


_INDEX = {_cle(p.nom): p for p in _PAYS}
_INDEX |= {p.iso2.lower(): p for p in _PAYS} | {p.iso3.lower(): p for p in _PAYS}
_PAR_ISO2 = {p.iso2: p for p in _PAYS}
_INDEX |= {cle: _PAR_ISO2[iso2] for cle, iso2 in _ALIAS.items()}


def pays_connu(nom_ou_code: str) -> Pays | None:
    """Recherche dans la table statique par nom français, ISO2 ou ISO3."""
    return _INDEX.get(_cle(nom_ou_code))


def pays_par_iso2(iso2: str) -> Pays | None:
    return _PAR_ISO2.get(iso2.upper())


def localisation_statique(saisie: SaisieProjet) -> Localisation:
    """Localisation au niveau pays, à partir de la seule table statique."""
    pays = pays_connu(saisie.pays)
    if pays is None:
        return Localisation(pays=saisie.pays, code_pays="")
    return Localisation(
        pays=pays.nom, code_pays=pays.iso2, code_pays_iso3=pays.iso3, ue=pays.iso2 in CODES_UE
    )


def _fixture_correspond(saisie: SaisieProjet) -> Localisation | None:
    chemin = parametres().dossier_fixtures / "flux" / "geo.json"
    if not chemin.exists():
        return None
    fixture = Localisation(**json.loads(chemin.read_text(encoding="utf-8")))
    lieu = _cle(saisie.lieu or "")
    pays = pays_connu(saisie.pays)
    if (
        pays
        and pays.iso2 == fixture.code_pays
        and lieu
        in {
            _cle(fixture.code_postal or ""),
            _cle(fixture.ville or ""),
        }
    ):
        return fixture
    return None


def _depuis_commune(base: Localisation, commune: dict, code_postal: str | None) -> Localisation:
    lon, lat = (commune.get("centre") or {}).get("coordinates", (None, None))
    departement = commune.get("departement") or {}
    postaux = commune.get("codesPostaux") or []
    return base.model_copy(
        update={
            "ville": commune["nom"],
            "code_postal": code_postal or (postaux[0] if postaux else None),
            "code_commune": commune["code"],
            "departement": departement.get("nom"),
            "code_departement": departement.get("code"),
            "region": (commune.get("region") or {}).get("nom"),
            "lat": lat,
            "lon": lon,
            "population": commune.get("population"),
        }
    )


async def _api_geo(client: httpx.AsyncClient, base: Localisation, lieu: str) -> Localisation | None:
    if re.fullmatch(r"\d{5}", lieu):
        params = {"codePostal": lieu, "fields": CHAMPS_API_GEO}
    else:
        params = {"nom": lieu, "fields": CHAMPS_API_GEO, "boost": "population", "limit": 5}
    reponse = await client.get(URL_API_GEO, params=params)
    reponse.raise_for_status()
    communes = reponse.json()
    if not communes:
        return None
    # Plusieurs communes partagent souvent un code postal : on retient la plus peuplée
    commune = max(communes, key=lambda c: c.get("population") or 0)
    code_postal = lieu if re.fullmatch(r"\d{5}", lieu) else None
    return _depuis_commune(base, commune, code_postal)


async def _open_meteo(
    client: httpx.AsyncClient, base: Localisation, lieu: str
) -> Localisation | None:
    params = {"name": lieu, "language": "fr", "count": 5, "format": "json"}
    if base.code_pays:
        params["countryCode"] = base.code_pays
    reponse = await client.get(URL_OPEN_METEO, params=params)
    reponse.raise_for_status()
    resultats = reponse.json().get("results") or []
    if not resultats:
        return None
    r = resultats[0]
    maj = {
        "ville": r.get("name"),
        "lat": r.get("latitude"),
        "lon": r.get("longitude"),
        "population": r.get("population"),
        "region": r.get("admin1"),
        "departement": r.get("admin2"),
    }
    if not base.code_pays and r.get("country_code"):
        # Pays hors table : on reprend celui renvoyé par Open-Meteo
        maj |= {"code_pays": r["country_code"], "pays": r.get("country") or base.pays}
        maj["ue"] = r["country_code"] in CODES_UE
    return base.model_copy(update=maj)


async def _pays_open_meteo(client: httpx.AsyncClient, base: Localisation) -> Localisation:
    """Pays absent de la table : code ISO2 trouvé via Open-Meteo."""
    params = {"name": base.pays, "language": "fr", "count": 10, "format": "json"}
    reponse = await client.get(URL_OPEN_METEO, params=params)
    reponse.raise_for_status()
    for r in reponse.json().get("results") or []:
        if str(r.get("feature_code", "")).startswith("PCL") and r.get("country_code"):
            code = r["country_code"]
            return base.model_copy(
                update={
                    "pays": r.get("name") or base.pays,
                    "code_pays": code,
                    "ue": code in CODES_UE,
                }
            )
    return base


async def _geocoder_en_ligne(saisie: SaisieProjet) -> Localisation:
    base = localisation_statique(saisie)
    lieu = (saisie.lieu or "").strip()
    async with client_tls() as client:
        if not base.code_pays:
            base = await _pays_open_meteo(client, base)
        if not lieu:
            return base
        if base.code_pays == "FR":
            trouve = await _api_geo(client, base, lieu)
            if trouve:
                return trouve
        trouve = await _open_meteo(client, base, lieu)
        return trouve or base


async def geocoder(saisie: SaisieProjet) -> Localisation:
    """Géocode la saisie. Ne lève jamais : se replie sur la fixture ou la table statique."""
    if parametres().demo:
        return _fixture_correspond(saisie) or localisation_statique(saisie)
    try:
        return await asyncio.wait_for(_geocoder_en_ligne(saisie), TIMEOUT_FLUX)
    except Exception as exc:  # noqa: BLE001 : tout échec bascule sur le repli
        journal.warning("Géocodage en échec (%s), repli sur les données statiques", exc)
        return _fixture_correspond(saisie) or localisation_statique(saisie)
