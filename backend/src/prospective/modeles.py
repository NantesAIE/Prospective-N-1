"""Modèles de données partagés : contexte utilisateur, localisation, signaux."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Axe(StrEnum):
    """Axes STEEPL. E1 : Économique, E2 : Environnemental."""

    S = "S"
    T = "T"
    E1 = "E1"
    E2 = "E2"
    P = "P"
    L = "L"


LIBELLES_AXES = {
    Axe.S: "Social",
    Axe.T: "Technologique",
    Axe.E1: "Économique",
    Axe.E2: "Environnemental",
    Axe.P: "Politique",
    Axe.L: "Légal",
}


class Niveau(StrEnum):
    MONDE = "monde"
    ZONE = "zone"
    PAYS = "pays"
    LOCAL = "local"


LIBELLES_NIVEAUX = {
    Niveau.MONDE: "Monde",
    Niveau.ZONE: "UE",
    Niveau.PAYS: "Pays",
    Niveau.LOCAL: "Local",
}


class SaisieProjet(BaseModel):
    """Saisie brute de l'étape 0."""

    description: str = Field(min_length=20, max_length=2000)
    thematique: str
    pays: str = "France"
    lieu: str | None = None  # code postal (France) ou ville
    horizon: int = 2040
    ambition: str = ""


class Localisation(BaseModel):
    """Résultat du géocodage."""

    pays: str
    code_pays: str  # ISO 3166-1 alpha-2, ex. "FR"
    code_pays_iso3: str | None = None  # ex. "FRA", utile pour World Bank
    ue: bool = False
    ville: str | None = None
    code_postal: str | None = None
    code_commune: str | None = None  # code INSEE en France
    departement: str | None = None
    code_departement: str | None = None
    region: str | None = None
    lat: float | None = None
    lon: float | None = None
    population: int | None = None


class ContexteUtilisateur(BaseModel):
    """User context transmis aux connecteurs de flux."""

    saisie: SaisieProjet
    localisation: Localisation
    mots_cles: list[str] = []  # termes de recherche, en français
    mots_cles_en: list[str] = []  # traduction anglaise, pour les sources internationales
    codes_naf: list[str] = []  # codes NAF pressentis, ex. "93.13Z"


class SignalBrut(BaseModel):
    """Élément collecté par un connecteur, avant extraction par le LLM."""

    titre: str
    resume: str
    source: str
    url: str
    date: str  # ISO 8601 (AAAA-MM-JJ) si connue
    axe_presume: Axe | None = None
    flux_id: str
    niveau: Niveau
    donnees_demo: bool = False  # vrai si issu d'un jeu de secours


class Signal(BaseModel):
    """Signal candidat retenu dans le dossier. La source vient toujours des données collectées."""

    id: str
    titre: str
    resume: str
    axe: Axe
    source: str | None = None
    url: str | None = None
    date: str | None = None
    niveau: Niveau | None = None
    flux_id: str | None = None
    hypothese_ia: bool = False
    donnees_demo: bool = False
    ajout_manuel: bool = False
    retenu: bool = True
