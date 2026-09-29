"""Client LLM unique de l'application.

Tout appel au modèle passe par ce module, via la passerelle Capgemini Generative Engine
(protocole OpenAI Chat Completions). Aucun autre module n'instancie de client.

Sortie structurée : chaque étape fournit un modèle Pydantic. Ce modèle génère le JSON Schema
d'un outil dédié (`strict: true`) et valide la réponse, pour que schéma et validation
ne puissent pas diverger.

Tous les appels sont streamés : la passerelle coupe en erreur 500 les réponses non streamées
qui dépassent 180 s. La sortie JSON d'un outil plafonne vers 150 caractères par seconde :
les étapes découpent donc leurs livrables en appels parallèles de taille raisonnable.
"""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
import openai
from pydantic import BaseModel, ValidationError

from prospective.config import parametres

journal = logging.getLogger(__name__)

MAX_TOKENS_PLAFOND = 16_000

# Modèles dont les appels d'outils ont été vérifiés sur la passerelle (sondage du 2026-08-03)
MODELES_OUTILS_VERIFIES = (
    "anthropic.claude-opus-5",
    "anthropic.claude-sonnet-5",
    "anthropic.claude-sonnet-4-6",
    "anthropic.claude-haiku-4-5-20251001-v1:0",
    "openai.gpt-5",
    "openai.gpt-5-mini",
    "openai.gpt-5.4",
    "gemini-3.5-flash",
    "amazon.nova-pro-v1:0",
    "amazon.nova-lite-v1:0",
    "amazon.nova-micro-v1:0",
    "google.gemma-4-31b",
    "mistral.mistral-large-2402-v1:0",
    "mistral.devstral-2-123b",
)


class ErreurLLM(Exception):
    """Erreur d'appel au modèle, avec un message destiné à l'utilisateur."""


@lru_cache
def client() -> openai.AsyncOpenAI:
    p = parametres()
    if p.demo:
        raise ErreurLLM("Mode hors ligne actif : aucun appel à la passerelle n'est autorisé.")
    if not p.agent_api_key:
        raise ErreurLLM(
            "Clé API absente : lancez « uv run enregistrer-cle » ou renseignez AGENT_API_KEY."
        )
    return openai.AsyncOpenAI(
        api_key=p.agent_api_key,
        base_url=p.agent_base_url,
        max_retries=3,
        timeout=httpx.Timeout(connect=20.0, read=900.0, write=60.0, pool=20.0),
    )


# Modèle choisi par l'utilisateur pour toute la session (sinon, configuration .env)
_modele_session: ContextVar[str | None] = ContextVar("modele_session", default=None)


def verifier_modele(nom: str) -> None:
    if nom not in MODELES_OUTILS_VERIFIES:
        raise ErreurLLM(
            f"Le modèle « {nom} » n'est pas vérifié pour les appels d'outils sur la passerelle."
        )


@contextmanager
def utiliser_modele(nom: str | None) -> Iterator[None]:
    """Impose un modèle à tous les appels du bloc, y compris aux tâches lancées dedans."""
    if nom:
        verifier_modele(nom)
    jeton = _modele_session.set(nom)
    try:
        yield
    finally:
        _modele_session.reset(jeton)


def modele(rapide: bool = False) -> str:
    choisi = _modele_session.get()
    if choisi:
        return choisi
    p = parametres()
    return p.agent_model_fast if rapide else p.agent_model


@dataclass
class AppelOutil:
    id: str
    nom: str
    arguments: str


@dataclass
class Reponse:
    finish_reason: str | None
    contenu: str
    appels: list[AppelOutil]

    def message(self) -> dict[str, Any]:
        """Message assistant à réinjecter dans la conversation."""
        message: dict[str, Any] = {"role": "assistant", "content": self.contenu or None}
        if self.appels:
            message["tool_calls"] = [
                {
                    "id": a.id,
                    "type": "function",
                    "function": {"name": a.nom, "arguments": a.arguments},
                }
                for a in self.appels
            ]
        return message


async def _appeler(**kwargs: Any) -> Reponse:
    """Appel streamé à la passerelle, avec traduction des erreurs en messages utilisateur."""
    debut = time.perf_counter()
    contenu: list[str] = []
    appels: dict[int, AppelOutil] = {}
    finish_reason = None
    try:
        flux = await client().chat.completions.create(stream=True, **kwargs)
        async for morceau in flux:
            if not morceau.choices:
                continue
            choix = morceau.choices[0]
            finish_reason = choix.finish_reason or finish_reason
            delta = choix.delta
            if delta.content:
                contenu.append(delta.content)
            for d in delta.tool_calls or []:
                appel = appels.setdefault(d.index, AppelOutil(id="", nom="", arguments=""))
                if d.id:
                    appel.id = d.id
                if d.function and d.function.name:
                    appel.nom = d.function.name
                if d.function and d.function.arguments:
                    appel.arguments += d.function.arguments
    except openai.APIStatusError as exc:
        raise ErreurLLM(f"La passerelle a répondu une erreur {exc.status_code}.") from exc
    except (openai.APITimeoutError, httpx.TimeoutException) as exc:
        raise ErreurLLM("La passerelle ne répond plus (délai dépassé).") from exc
    except (openai.APIConnectionError, httpx.HTTPError) as exc:
        raise ErreurLLM(
            "Passerelle injoignable : vérifiez la connexion au réseau ou au VPN d'entreprise."
        ) from exc
    reponse = Reponse(finish_reason, "".join(contenu), [appels[i] for i in sorted(appels)])
    journal.info(
        "%s : %.0f s, %d caractères, fin %s",
        kwargs.get("model"),
        time.perf_counter() - debut,
        len(reponse.contenu) + sum(len(a.arguments) for a in reponse.appels),
        finish_reason,
    )
    return reponse


def _deballer(donnees: Any, schema: type[BaseModel] | None = None) -> Any:
    """Corrige des écarts de forme observés avant validation.

    - Double encodage : {"signaux": "{\"signaux\": [...]}"} devient {"signaux": [...]}.
    - Liste de textes rendue en une seule chaîne : découpée ligne par ligne.
    """
    if not isinstance(donnees, dict):
        return donnees
    listes_de_textes = {
        nom
        for nom, champ in (schema.model_fields.items() if schema else [])
        if champ.annotation == list[str]
    }
    corrige = {}
    for cle, valeur in donnees.items():
        if isinstance(valeur, str) and valeur.lstrip()[:1] in ("{", "["):
            try:
                valeur = json.loads(valeur)
            except json.JSONDecodeError:
                pass
            else:
                if isinstance(valeur, dict) and cle in valeur:
                    valeur = valeur[cle]
        if cle in listes_de_textes and isinstance(valeur, str):
            valeur = [ligne.strip(" -•*\t") for ligne in valeur.splitlines() if ligne.strip()]
        corrige[cle] = valeur
    return corrige


async def generer_structure[T: BaseModel](
    schema: type[T],
    messages: list[dict[str, Any]],
    *,
    nom_outil: str,
    description: str,
    rapide: bool = False,
    max_tokens: int = 8_000,
    tentatives: int = 2,
    delai: float | None = None,
) -> T:
    """Obtient du modèle une sortie conforme à `schema`, via un outil strict dédié.

    La passerelle renvoie une erreur 500 dès que `tool_choice` impose un outil (nommé ou
    "required") : on laisse donc le choix en "auto" et on exige l'appel dans la consigne.
    La réponse est toujours revalidée par Pydantic. En cas d'échec (pas de `tool_calls`,
    JSON invalide, validation refusée), on relance au plus `tentatives` fois en renvoyant
    l'erreur au modèle, puis on lève `ErreurLLM`. `delai` borne la durée totale, en secondes.
    """
    try:
        async with asyncio.timeout(delai):
            return await _generer_structure(
                schema, messages, nom_outil, description, rapide, max_tokens, tentatives
            )
    except TimeoutError as exc:
        raise ErreurLLM(f"Génération interrompue après {delai:.0f} s (délai dépassé).") from exc


async def _generer_structure[T: BaseModel](
    schema: type[T],
    messages: list[dict[str, Any]],
    nom_outil: str,
    description: str,
    rapide: bool,
    max_tokens: int,
    tentatives: int,
) -> T:
    nom_modele = modele(rapide)
    verifier_modele(nom_modele)
    outil = openai.pydantic_function_tool(schema, name=nom_outil, description=description)
    conversation = list(messages)
    derniere_erreur = "réponse vide"

    for essai in range(1, tentatives + 2):
        reponse = await _appeler(
            model=nom_modele,
            max_tokens=min(max_tokens, MAX_TOKENS_PLAFOND),
            messages=conversation,
            tools=[outil],
        )
        if reponse.finish_reason == "content_filter":
            raise ErreurLLM(
                "La réponse a été bloquée par le filtre de contenu de la passerelle. "
                "Reformulez la demande."
            )
        appel = next((a for a in reponse.appels if a.nom == nom_outil), None)

        if appel is None:
            # Échec silencieux : texte brut avec finish_reason "stop", sans appel d'outil
            derniere_erreur = f"aucun appel d'outil (finish_reason={reponse.finish_reason})"
            conversation += [
                {"role": "assistant", "content": reponse.contenu or ""},
                {
                    "role": "user",
                    "content": f"Tu dois répondre uniquement en appelant l'outil {nom_outil}.",
                },
            ]
        else:
            try:
                return schema.model_validate(_deballer(json.loads(appel.arguments), schema))
            except (json.JSONDecodeError, ValidationError) as exc:
                derniere_erreur = str(exc)
                if reponse.finish_reason == "length":
                    derniere_erreur = "réponse tronquée (max_tokens atteint)"
                conversation += [
                    reponse.message(),
                    {
                        "role": "tool",
                        "tool_call_id": appel.id,
                        "content": (
                            f"Sortie invalide, corrige-la et rappelle l'outil : {derniere_erreur}"
                        ),
                    },
                ]

        journal.warning("Sortie structurée invalide (essai %d) : %s", essai, derniere_erreur)

    raise ErreurLLM(
        f"Le modèle n'a pas produit de résultat exploitable après {tentatives + 1} essais "
        f"({derniere_erreur}). Relancez l'étape."
    )


@dataclass
class Outil:
    """Outil exposé au modèle dans une boucle agentique."""

    nom: str
    description: str
    schema: type[BaseModel]
    executer: Callable[[Any], Awaitable[str]]


async def boucle_outils(
    messages: list[dict[str, Any]],
    outils: list[Outil],
    *,
    rapide: bool = True,
    max_tours: int = 12,
    max_tokens: int = 4_000,
) -> str:
    """Boucle agentique : le modèle appelle des outils jusqu'à produire une réponse texte.

    Plafonnée à `max_tours` tours, car sans cache de prompt chaque tour réenvoie tout le contexte.
    """
    nom_modele = modele(rapide)
    verifier_modele(nom_modele)
    par_nom = {o.nom: o for o in outils}
    definitions = [
        openai.pydantic_function_tool(o.schema, name=o.nom, description=o.description)
        for o in outils
    ]
    conversation = list(messages)

    for _ in range(max_tours):
        reponse = await _appeler(
            model=nom_modele,
            max_tokens=min(max_tokens, MAX_TOKENS_PLAFOND),
            messages=conversation,
            tools=definitions,
        )
        if reponse.finish_reason == "content_filter":
            raise ErreurLLM("La réponse a été bloquée par le filtre de contenu de la passerelle.")
        if not reponse.appels:
            return reponse.contenu

        conversation.append(reponse.message())
        for appel in reponse.appels:
            outil = par_nom.get(appel.nom)
            if outil is None:
                resultat = f"Outil inconnu : {appel.nom}"
            else:
                try:
                    resultat = await outil.executer(
                        outil.schema.model_validate_json(appel.arguments or "{}")
                    )
                except ValidationError as exc:
                    resultat = f"Arguments invalides : {exc}"
            conversation.append({"role": "tool", "tool_call_id": appel.id, "content": resultat})

    conversation.append(
        {"role": "user", "content": "Conclus maintenant ta réponse, sans appeler d'outil."}
    )
    reponse = await _appeler(
        model=nom_modele, max_tokens=max_tokens, messages=conversation, tools=definitions
    )
    return reponse.contenu
