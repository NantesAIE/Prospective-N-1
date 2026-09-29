"""Tests hors ligne des flux : fixtures, catalogue, mode dégradé et mode démo."""

import json
from typing import ClassVar

import httpx
import pytest

from prospective.config import parametres
from prospective.flux import CATALOGUE, geocoder, par_id, profil_demographique
from prospective.flux.base import Flux, charger_fixture, collecter_avec_repli
from prospective.flux.eurostat import Cube
from prospective.flux.gdelt import _expression
from prospective.flux.geo import localisation_statique
from prospective.flux.outils import date_iso, entrelacer, pertinence, signe
from prospective.modeles import Axe, ContexteUtilisateur, Localisation, Niveau, SaisieProjet

DOSSIER = parametres().dossier_fixtures / "flux"
FIXTURES_SIGNAUX = sorted(p for p in DOSSIER.glob("*.json") if p.stem not in {"geo", "demographie"})
SAISIE = SaisieProjet(
    description="Service de sport santé pour les seniors actifs, en extérieur et connecté.",
    thematique="sport, santé",
    lieu="44000",
)


@pytest.fixture
def sans_demo(monkeypatch):
    monkeypatch.setattr(parametres(), "demo", False)


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(parametres(), "demo", True)


def _contexte() -> ContexteUtilisateur:
    loc = Localisation(**json.loads((DOSSIER / "geo.json").read_text(encoding="utf-8")))
    return ContexteUtilisateur(saisie=SAISIE, localisation=loc, mots_cles=["sport santé"])


def test_fixtures_presentes():
    assert FIXTURES_SIGNAUX, "aucune fixture de signaux dans fixtures/flux"


@pytest.mark.parametrize("chemin", FIXTURES_SIGNAUX, ids=lambda p: p.stem)
def test_fixture_se_charge_en_signaux_valides(chemin):
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    assert all("donnees_demo" not in s for s in brut)
    signaux = charger_fixture(chemin.stem)
    assert 3 <= len(signaux) <= 12
    for s in signaux:
        assert s.flux_id == chemin.stem
        assert s.donnees_demo
        assert s.titre and s.resume and s.source
        assert s.url.startswith(("http://", "https://"))
        assert s.date == "" or date_iso(s.date) == s.date


def test_chaque_fixture_correspond_a_un_flux_du_catalogue():
    ids = {f.id for f in CATALOGUE}
    assert {p.stem for p in FIXTURES_SIGNAUX} <= ids


def test_fixture_geo():
    loc = Localisation(**json.loads((DOSSIER / "geo.json").read_text(encoding="utf-8")))
    assert (loc.code_pays, loc.code_commune, loc.code_postal) == ("FR", "44109", "44000")
    assert loc.ue and loc.lat and loc.lon


def test_fixture_demographie():
    profil = json.loads((DOSSIER / "demographie.json").read_text(encoding="utf-8"))
    assert profil["source"] and profil["url"].startswith("https://")
    assert profil["echelle"] == "commune" and profil["population"] > 0
    assert abs(sum(profil["tranches_age_pct"].values()) - 100) < 1


def test_catalogue_ids_uniques_et_attributs():
    ids = [f.id for f in CATALOGUE]
    assert len(ids) == len(set(ids))
    for f in CATALOGUE:
        assert f.nom and f.description and f.axes
        assert isinstance(f.niveau, Niveau)
        assert all(isinstance(a, Axe) for a in f.axes)
        if f.niveau in (Niveau.PAYS, Niveau.LOCAL):
            assert f.pays
        assert set(f.fiche()) >= {"id", "nom", "axes", "niveau", "interrogeable"}


def test_par_id():
    assert par_id("bodacc").id == "bodacc"
    with pytest.raises(KeyError):
        par_id("inexistant")


class _FluxEnPanne(Flux):
    id = "world_bank"
    nom = "En panne"
    description = "Lève toujours une exception."
    axes: ClassVar[list[Axe]] = [Axe.S]
    niveau = Niveau.MONDE

    def __init__(self):
        self.appels = 0

    async def collecter(self, ctx, client, requete=None):
        self.appels += 1
        raise RuntimeError("API indisponible")


async def test_repli_sur_fixture_quand_collecter_echoue(sans_demo):
    flux = _FluxEnPanne()
    signaux, degrade = await collecter_avec_repli(flux, _contexte(), client=None)
    assert flux.appels == 1
    assert degrade
    assert signaux == charger_fixture("world_bank")
    assert signaux and all(s.donnees_demo for s in signaux)


async def test_mode_demo_sans_appel_reseau(demo):
    flux = _FluxEnPanne()
    signaux, degrade = await collecter_avec_repli(flux, _contexte(), client=None)
    assert flux.appels == 0 and degrade and signaux

    loc = await geocoder(SAISIE)
    assert loc.code_commune == "44109"
    profil = await profil_demographique(loc)
    assert profil["donnees_demo"] and profil["population"] > 0


async def test_mode_demo_hors_scenario_utilise_la_table_statique(demo):
    loc = await geocoder(SAISIE.model_copy(update={"pays": "Allemagne", "lieu": None}))
    assert (loc.code_pays, loc.code_pays_iso3, loc.ue) == ("DE", "DEU", True)
    assert loc.lat is None


@pytest.mark.parametrize(
    ("pays", "attendu"),
    [
        ("France", ("FR", "FRA", True)),
        ("royaume-uni", ("GB", "GBR", False)),
        ("États-Unis", ("US", "USA", False)),
        ("Maroc", ("MA", "MAR", False)),
        ("Tchéquie", ("CZ", "CZE", True)),
    ],
)
def test_table_statique_des_pays(pays, attendu):
    loc = localisation_statique(SAISIE.model_copy(update={"pays": pays}))
    assert (loc.code_pays, loc.code_pays_iso3, loc.ue) == attendu


def test_outils():
    assert date_iso("20260915T101500Z") == "2026-09-15"
    assert date_iso("03/03/2026") == "2026-03-03"
    assert signe(-0.01) == "+0,0"
    assert entrelacer([[1, 2, 3], ["a"]]) == [1, "a", 2, 3]
    assert pertinence("Maison Sport Santé", ["sport santé"]) > pertinence(
        "Activité de location", ["activité physique adaptée"]
    )


def test_cube_json_stat():
    cube = Cube(
        {
            "id": ["geo", "time"],
            "size": [2, 2],
            "dimension": {
                "geo": {"category": {"index": {"FR": 0, "EU27_2020": 1}}},
                "time": {"category": {"index": {"2024": 0, "2025": 1}}},
            },
            "value": {"0": 1.0, "1": 2.0, "3": 4.0},
        }
    )
    assert cube.valeur(geo="FR", time="2025") == 2.0
    assert cube.valeur(geo="EU27_2020", time="2024") is None
    assert cube.valeur(geo="EU27_2020", time="2025") == 4.0


def test_expression_gdelt():
    assert _expression(["sport santé", "seniors"]) == '("sport santé" OR seniors)'
    assert _expression(["seniors"]) == "seniors"


RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>La mairie lance un plan sport santé - Ouest-France</title>
<link>https://news.google.com/rss/articles/A</link><pubDate>Tue, 22 Sep 2026 07:00:00 GMT</pubDate>
<source url="https://www.ouest-france.fr">Ouest-France</source></item>
<item><title>Marcher à 70 ans - Le Monde</title>
<link>https://news.google.com/rss/articles/B</link><pubDate>Wed, 23 Sep 2026 07:00:00 GMT</pubDate>
<source url="https://www.lemonde.fr">Le Monde</source></item>
</channel></rss>"""


async def test_google_actualites_hors_ligne():
    from prospective.flux.google_actualites import GoogleActualites

    requetes = []

    def repondre(requete: httpx.Request) -> httpx.Response:
        requetes.append(requete)
        return httpx.Response(
            200, content=RSS.encode(), headers={"content-type": "application/xml"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(repondre)) as client:
        signaux = await GoogleActualites().collecter(_contexte(), client)

    assert len(requetes) == 2  # nationale et locale (ville du contexte)
    assert requetes[0].url.params["ceid"] == "FR:fr"
    assert len(signaux) == 2  # dédoublonnage des deux réponses identiques
    premier = signaux[0]
    assert premier.titre == "La mairie lance un plan sport santé"
    assert premier.source == "Ouest-France via Google Actualités"
    assert premier.url == "https://news.google.com/rss/articles/A"
    assert premier.date == "2026-09-22" and premier.axe_presume == Axe.P
    assert signaux[1].axe_presume is None


async def test_boamp_hors_ligne():
    from prospective.flux.boamp import Boamp

    avis = [
        {
            "objet": "Ateliers sport santé",
            "nomacheteur": "Ville A",
            "dateparution": "2026-09-21",
            "nature_libelle": "Résultat de marché",
            "url_avis": "https://www.boamp.fr/pages/avis/?q=idweb:1",
        },
        {
            "objet": "Ateliers sport santé",
            "nomacheteur": "Ville A",
            "dateparution": "2026-08-20",
            "nature_libelle": "Avis de marché",
            "url_avis": "https://www.boamp.fr/pages/avis/?q=idweb:2",
        },
        {
            "objet": "Papeterie",
            "nomacheteur": "Ville B",
            "dateparution": "2026-08-19",
            "nature_libelle": "Avis de marché",
            "url_avis": "https://www.boamp.fr/pages/avis/?q=idweb:3",
        },
    ]

    def repondre(requete: httpx.Request) -> httpx.Response:
        if "group_by" in requete.url.params:
            return httpx.Response(
                200, json={"results": [{"nature_libelle": "Avis de marché", "n": 3}]}
            )
        return httpx.Response(200, json={"results": avis})

    async with httpx.AsyncClient(transport=httpx.MockTransport(repondre)) as client:
        signaux = await Boamp().collecter(_contexte(), client)

    assert "3 avis BOAMP" in signaux[0].resume
    urls = [s.url for s in signaux[1:]]
    # Doublon (avis puis résultat) fusionné ; objet sans rapport conservé faute de mieux
    assert urls[0] == "https://www.boamp.fr/pages/avis/?q=idweb:1"
    assert "https://www.boamp.fr/pages/avis/?q=idweb:2" not in urls
