"""Assistant conversationnel : parler du projet, interroger les sources, suggérer.

Trois outils seulement : interroger les flux de données, consulter le dossier, proposer des
suggestions applicables en un clic (relance de l'étape avec une consigne).
"""

import asyncio
from typing import Any

from pydantic import BaseModel

from prospective import llm
from prospective import session as sessions
from prospective.config import parametres
from prospective.etapes import ETAPES
from prospective.flux import CATALOGUE, par_id
from prospective.flux.base import client_http, collecter_avec_repli
from prospective.modeles import LIBELLES_NIVEAUX, SignalBrut
from prospective.prompts import strong_context
from prospective.session import MessageChat, Session

MAX_RESULTATS = 20
HISTORIQUE = 20
LIMITE_DOSSIER = 8_000


class InterrogerSources(BaseModel):
    requete: str
    flux: list[str]


class ConsulterDossier(BaseModel):
    etape: int


class Suggestion(BaseModel):
    titre: str
    explication: str
    etape: int
    consigne: str


class ProposerSuggestions(BaseModel):
    suggestions: list[Suggestion]


SYSTEME = """Tu es l'assistant prospectiviste d'un entrepreneur qui mène une étude de prospective
en 9 étapes jusqu'à l'horizon {horizon}. Tu l'aides à parler de son projet, à interroger les
sources de données et à améliorer chaque étape.

Règles :
- Réponds en français, de façon concise et concrète (Markdown léger autorisé).
- Pour toute question factuelle sur le territoire, le marché, la concurrence, la presse ou la
  recherche, appelle interroger_sources plutôt que de répondre de mémoire.
- Ne cite une source que si elle provient d'un résultat d'outil ou du dossier, au format
  [nom](url). N'invente jamais de source ni d'URL ; signale ce qui relève de ton raisonnement
  par la mention « (hypothèse IA) ».
- Quand l'entrepreneur demande comment améliorer une étape, ou qu'une piste mérite d'être
  intégrée, appelle proposer_suggestions : chaque suggestion porte une consigne rédigée pour
  relancer l'étape concernée. Ne propose pas de suggestion pour une étape non encore générée.
- Utilise consulter_dossier pour lire le détail d'une étape avant d'en parler.

Flux interrogeables (identifiants) : {flux}

## Strong context
{contexte}

## Avancement du parcours
{avancement}

## Étape affichée à l'écran : {etape_courante}
{livrable_courant}"""


def _avancement(session: Session) -> str:
    libelles = {"a_faire": "à faire", "brouillon": "brouillon à valider", "valide": "validée"}
    return "\n".join(
        f"- Étape {e.numero} ({ETAPES[e.numero].titre}) : {libelles[e.statut]}"
        for e in session.etapes
    )


def _markdown_etape(session: Session, n: int) -> str:
    etat = session.etapes[n]
    if etat.livrable is None:
        return "Pas encore générée."
    etape = ETAPES[n]
    return etape.markdown(etape.charger(etat.livrable), session)[:LIMITE_DOSSIER]


def _flux_interrogeables(session: Session) -> list[str]:
    interrogeables = [f.id for f in CATALOGUE if f.interrogeable]
    flux_etape1 = session.etapes[1].livrable
    if flux_etape1:
        actifs = {f["id"] for f in flux_etape1["flux"] if f["actif"]}
        return [i for i in interrogeables if i in actifs] or interrogeables
    return interrogeables


def _format_resultat(r: dict[str, Any]) -> str:
    return (
        f"[{r['id']}] {r['titre']} : {r['resume'][:280]} "
        f"(source : {r['source']}, {r['date']}, url : {r['url']}"
        f"{', données de démonstration' if r['donnees_demo'] else ''})"
    )


async def _interroger(
    session: Session, requete: str, flux: list[str], resultats: list[dict[str, Any]]
) -> str:
    if session.contexte is None:
        return "Les sources seront interrogeables une fois l'étape 0 validée."
    disponibles = _flux_interrogeables(session)
    choisis = [f for f in flux if f in disponibles] or disponibles
    async with client_http() as client:
        reponses = await asyncio.gather(
            *(collecter_avec_repli(par_id(f), session.contexte, client, requete) for f in choisis)
        )
    nouveaux: list[SignalBrut] = [s for signaux, _ in reponses for s in signaux]
    lignes = []
    for s in nouveaux[:MAX_RESULTATS]:
        r = {
            "id": f"r{len(resultats) + 1}",
            **s.model_dump(mode="json"),
            "niveau_libelle": LIBELLES_NIVEAUX[s.niveau],
        }
        resultats.append(r)
        lignes.append(_format_resultat(r))
    if not lignes:
        return f"Aucun résultat pour « {requete} » sur {', '.join(choisis)}."
    return f"Résultats pour « {requete} » ({', '.join(choisis)}) :\n" + "\n".join(lignes)


def _repondre_demo(session: Session, message: str) -> MessageChat:
    """Mode démo : réponse locale, par recherche plein texte dans les signaux collectés."""
    mots = {m for m in message.lower().split() if len(m) > 3}
    signaux = (session.etapes[2].livrable or {}).get("signaux", [])
    trouves = [s for s in signaux if mots & set(f"{s['titre']} {s['resume']}".lower().split())][:5]
    if trouves:
        contenu = "Mode démo : voici les signaux du dossier liés à votre question.\n\n" + "\n".join(
            f"- **{s['titre']}** : {s['resume']}"
            + (f" ([{s['source']}]({s['url']}))" if s.get("url") else " (hypothèse IA)")
            for s in trouves
        )
    else:
        contenu = (
            "Mode démo : l'assistant conversationnel nécessite la passerelle. "
            "Désactivez DEMO pour dialoguer avec le modèle."
        )
    return MessageChat(role="assistant", contenu=contenu, etape=session.etape_courante)


async def repondre(session_id: str, message: str, etape: int) -> list[MessageChat]:
    """Traite un message de l'utilisateur et renvoie la conversation complète."""
    session = sessions.charger(session_id)
    question = MessageChat(role="user", contenu=message, etape=etape)

    if parametres().demo:
        reponse = _repondre_demo(session, message)
    else:
        resultats: list[dict[str, Any]] = []
        suggestions: list[dict[str, Any]] = []

        async def interroger(args: InterrogerSources) -> str:
            return await _interroger(session, args.requete, args.flux, resultats)

        async def consulter(args: ConsulterDossier) -> str:
            if not 0 <= args.etape < len(ETAPES):
                return "Étape inconnue."
            return _markdown_etape(session, args.etape)

        async def proposer(args: ProposerSuggestions) -> str:
            for s in args.suggestions:
                if 0 <= s.etape < len(ETAPES) and session.etapes[s.etape].livrable is not None:
                    suggestions.append(s.model_dump())
            return f"{len(args.suggestions)} suggestion(s) affichée(s) à l'entrepreneur."

        outils = [
            llm.Outil(
                "interroger_sources",
                "Interroge en direct des flux de données (presse, entreprises, recherche...) avec "
                "une requête courte. flux : identifiants à interroger, liste vide pour tous.",
                InterrogerSources,
                interroger,
            ),
            llm.Outil(
                "consulter_dossier",
                "Renvoie le contenu détaillé d'une étape du dossier (0 à 8).",
                ConsulterDossier,
                consulter,
            ),
            llm.Outil(
                "proposer_suggestions",
                "Affiche des suggestions d'amélioration, chacune applicable en relançant "
                "l'étape indiquée avec la consigne fournie.",
                ProposerSuggestions,
                proposer,
            ),
        ]
        systeme = SYSTEME.format(
            horizon=session.saisie.horizon,
            flux=", ".join(_flux_interrogeables(session)),
            contexte=strong_context(session),
            avancement=_avancement(session),
            etape_courante=f"{etape} ({ETAPES[etape].titre})",
            livrable_courant=_markdown_etape(session, etape),
        )
        historique = [
            {"role": m.role, "content": m.contenu}
            for m in sessions.lire_conversation(session)[-HISTORIQUE:]
        ]
        with llm.utiliser_modele(session.modele):
            texte = await llm.boucle_outils(
                [
                    {"role": "system", "content": systeme},
                    *historique,
                    {"role": "user", "content": message},
                ],
                outils,
            )
        reponse = MessageChat(
            role="assistant",
            contenu=texte,
            etape=etape,
            suggestions=suggestions,
            resultats=resultats,
        )

    sessions.ajouter_messages(session, [question, reponse])
    return sessions.lire_conversation(session)
