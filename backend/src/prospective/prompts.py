"""Structure commune des prompts d'étape (brief, section 7).

Rôle, strong context, acquis validés, données, tâche, contraintes, format de sortie.
Le texte de la tâche propre à chaque étape vit dans le module de l'étape.
"""

import json
from typing import Any

from prospective.modeles import LIBELLES_AXES, LIBELLES_NIVEAUX, Signal
from prospective.session import Session

ROLE = "Tu es un prospectiviste expérimenté qui accompagne un entrepreneur."

LIMITE_VERSION_PRECEDENTE = 8_000


def strong_context(session: Session) -> str:
    """Texte intégral de l'étape 0 : saisie de l'utilisateur et fiche contexte validée."""
    s = session.saisie
    lignes = [
        "### Projet décrit par l'entrepreneur",
        s.description,
        "",
        f"- Thématique : {s.thematique}",
        f"- Localisation : {territoire(session)}",
        f"- Horizon : {s.horizon}",
    ]
    if s.ambition:
        lignes.append(f"- Ambition et contraintes : {s.ambition}")
    fiche = (session.etapes[0].livrable or {}).get("fiche")
    if fiche and session.etapes[0].statut == "valide":
        lignes += [
            "",
            "### Fiche contexte validée",
            f"- Problème : {fiche['probleme']}",
            f"- Cible : {fiche['cible']}",
            f"- Proposition de valeur pressentie : {fiche['proposition_valeur']}",
            f"- Territoire : {fiche['territoire']}",
            "- Hypothèses implicites :",
            *[f"  - {h}" for h in fiche["hypotheses_implicites"]],
        ]
    return "\n".join(lignes)


def territoire(session: Session) -> str:
    if session.contexte:
        loc = session.contexte.localisation
        morceaux = [loc.ville, loc.code_postal, loc.departement, loc.region, loc.pays]
        return ", ".join(m for m in morceaux if m)
    s = session.saisie
    return f"{s.lieu}, {s.pays}" if s.lieu else s.pays


def formater_signaux(signaux: list[Signal]) -> str:
    lignes = []
    for sig in signaux:
        if not sig.retenu:
            continue
        origine = (
            "hypothèse IA"
            if sig.hypothese_ia
            else f"{sig.source}, {sig.date or 's. d.'}, {LIBELLES_NIVEAUX.get(sig.niveau, '')}"
        )
        lignes.append(
            f"[{sig.id}] ({LIBELLES_AXES[sig.axe]}) {sig.titre} : {sig.resume} ({origine})"
        )
    return "\n".join(lignes)


def en_json(donnees: Any) -> str:
    return json.dumps(donnees, ensure_ascii=False, separators=(",", ":"))


def messages_etape(
    session: Session,
    *,
    tache: str,
    nom_outil: str,
    acquis: list[tuple[str, str]] | None = None,
    donnees: str = "",
    consigne: str | None = None,
    version_precedente: str | None = None,
) -> list[dict[str, str]]:
    """Construit les messages d'un appel d'étape."""
    horizon = session.saisie.horizon
    systeme = "\n".join(
        [
            ROLE,
            "",
            "Contraintes :",
            "- Réponds en français.",
            (
                "- N'invente jamais de source ni d'URL. Quand le format de sortie comporte un "
                "champ hypothese_ia, mets-le à true pour tout élément qui ne s'appuie pas sur "
                "une donnée fournie. N'écris jamais « hypothese_ia » dans les textes."
            ),
            f"- Reste cohérent avec le territoire ({territoire(session)}) et l'horizon {horizon}.",
            "- Sois concret et spécifique au projet ; évite les généralités.",
            f"- Réponds uniquement en appelant l'outil {nom_outil}, sans texte libre.",
        ]
    )
    parties = ["## Strong context", strong_context(session)]
    if acquis:
        parties.append("## Acquis validés")
        for titre, contenu in acquis:
            parties += [f"### {titre}", contenu]
    if donnees:
        parties += ["## Données", donnees]
    parties += ["## Tâche", tache]
    if version_precedente:
        parties += [
            "## Version précédente (à améliorer, pas à recopier)",
            version_precedente[:LIMITE_VERSION_PRECEDENTE],
        ]
    if consigne:
        parties += ["## Consigne de l'entrepreneur pour cette génération", consigne]
    return [
        {"role": "system", "content": systeme},
        {"role": "user", "content": "\n\n".join(parties)},
    ]
