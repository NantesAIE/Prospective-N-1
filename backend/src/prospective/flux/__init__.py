"""Connecteurs de flux de signaux STEEPL, géocodage et profil démographique."""

from prospective.flux.arxiv import Arxiv
from prospective.flux.base import Flux
from prospective.flux.boamp import Boamp
from prospective.flux.bodacc import Bodacc
from prospective.flux.demographie import profil_demographique
from prospective.flux.eurostat import Eurostat
from prospective.flux.geo import geocoder
from prospective.flux.geo_risques import GeoRisques
from prospective.flux.google_actualites import GoogleActualites
from prospective.flux.hacker_news import HackerNews
from prospective.flux.open_meteo_climat import OpenMeteoClimat
from prospective.flux.openalex import OpenAlex
from prospective.flux.recherche_entreprises import RechercheEntreprises
from prospective.flux.world_bank import WorldBank

# GDELT (gdelt.py) est hors catalogue : derrière le proxy d'entreprise, l'API répond 429
# (IP de sortie partagée) ou met 20 à 90 s pour une liste vide, bien au-delà des 8 s.
# Pour le réactiver hors de ce réseau : importer Gdelt et l'ajouter à la liste.
# Google Actualités le remplace pour la presse.
CATALOGUE: list[Flux] = [
    GoogleActualites(),
    WorldBank(),
    OpenMeteoClimat(),
    HackerNews(),
    OpenAlex(),
    Arxiv(),
    Eurostat(),
    RechercheEntreprises(),
    Bodacc(),
    Boamp(),
    GeoRisques(),
]

_PAR_ID = {f.id: f for f in CATALOGUE}


def par_id(flux_id: str) -> Flux:
    """Connecteur du catalogue par identifiant. Lève KeyError s'il est inconnu."""
    try:
        return _PAR_ID[flux_id]
    except KeyError:
        raise KeyError(f"Flux inconnu : {flux_id}") from None


__all__ = ["CATALOGUE", "Flux", "geocoder", "par_id", "profil_demographique"]
