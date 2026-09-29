"""Configuration de l'application, lue depuis l'environnement et le fichier `.env` racine."""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RACINE_PROJET = Path(__file__).resolve().parents[3]


class Parametres(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(RACINE_PROJET / ".env", RACINE_PROJET / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Passerelle Capgemini Generative Engine
    agent_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AGENT_API_KEY", "GENERATIVE_ENGINE_API_KEY", "OPENAI_API_KEY"
        ),
    )
    agent_base_url: str = "https://openai.generative-eu.engine.capgemini.com/v1"
    agent_model: str = "anthropic.claude-opus-5"
    agent_model_fast: str = "anthropic.claude-sonnet-5"

    # Mode démo : rejoue une session préenregistrée, sans passerelle ni réseau
    demo: bool = False

    # Serveur local, jamais exposé au réseau
    hote: str = Field(default="127.0.0.1", validation_alias="BACKEND_HOST")
    port: int = Field(default=8000, validation_alias="BACKEND_PORT")

    dossier_archives: Path = RACINE_PROJET / "archives"
    dossier_fixtures: Path = RACINE_PROJET / "fixtures"


@lru_cache
def parametres() -> Parametres:
    p = Parametres()
    if not p.agent_api_key:
        # Clé absente de l'environnement : on la lit dans le trousseau chiffré
        from prospective.coffre import lire_cle

        p.agent_api_key = lire_cle()
    return p
