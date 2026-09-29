"""Archivage local en Markdown : fichiers d'étape, versions, journal et synthèse."""

import re
from pathlib import Path

from pydantic import BaseModel

from prospective.etapes.base import Etape
from prospective.prompts import strong_context
from prospective.session import Session, maintenant

ACTIONS_JOURNAL = {
    "creation": "Création de la session",
    "generation": "Génération",
    "relance": "Relance",
    "modification": "Modification",
    "validation": "Validation",
    "echec": "Échec de génération",
    "reglage": "Réglage",
}


def _frontmatter(session: Session, etape: Etape, statut: str, version: int) -> str:
    flux = ", ".join(session.etapes[etape.numero].flux_utilises)
    return "\n".join(
        [
            "---",
            f"session_id: {session.id}",
            f"etape: {etape.numero}",
            f"titre: {etape.titre}",
            f"statut: {statut}",
            f"version: {version}",
            f"horodatage: {maintenant()}",
            f"flux_utilises: [{flux}]",
            "---",
        ]
    )


def rendre_etape(session: Session, etape: Etape, livrable: BaseModel, statut: str) -> str:
    etat = session.etapes[etape.numero]
    sources = etape.sources(livrable)
    consultation = maintenant()[:10]
    lignes_sources = "\n".join(
        f"- [{s.nom}]({s.url}), consultée le {consultation}" for s in sources
    )
    modifications = etat.commentaire.strip() or (
        "Livrable édité directement par l'utilisateur." if etat.modifie else "Aucune"
    )
    if etat.consignes:
        modifications += "\n\nConsignes de relance :\n" + "\n".join(
            f"- {c}" for c in etat.consignes
        )
    return (
        "\n\n".join(
            [
                _frontmatter(session, etape, statut, etat.version),
                f"# Étape {etape.numero} : {etape.titre}",
                "## Rappel du strong context",
                strong_context(session),
                "## Livrable validé" if statut != "relance" else "## Livrable (version remplacée)",
                etape.markdown(livrable, session),
                "## Modifications utilisateur",
                modifications,
                "## Sources",
                lignes_sources
                or "Aucune source externe (hypothèses IA ou choix de l'utilisateur).",
            ]
        )
        + "\n"
    )


def _version_libre(session: Session, etape: Etape) -> Path:
    k = 1
    while (chemin := session.chemin / f"{etape.fichier}.v{k}.md").exists():
        k += 1
    return chemin


def archiver_version(session: Session, etape: Etape, livrable: BaseModel) -> Path:
    """Conserve un brouillon remplacé par une relance sous `<fichier>.vN.md`."""
    chemin = _version_libre(session, etape)
    chemin.write_text(rendre_etape(session, etape, livrable, "relance"), encoding="utf-8")
    return chemin


def ecrire_etape(session: Session, etape: Etape, livrable: BaseModel, statut: str) -> Path:
    """Écrit `<fichier>.md` ; une version validée antérieure est conservée en `.vN.md`."""
    chemin = session.chemin / f"{etape.fichier}.md"
    if chemin.exists():
        chemin.replace(_version_libre(session, etape))
    chemin.write_text(rendre_etape(session, etape, livrable, statut), encoding="utf-8")
    return chemin


def journaliser(session: Session, action: str, etape: int | None = None, detail: str = "") -> None:
    chemin = session.chemin / "journal.md"
    if not chemin.exists():
        chemin.write_text(
            f"# Journal de la session {session.id}\n\n| Horodatage | Étape | Action | Détail |\n"
            "|---|---|---|---|\n",
            encoding="utf-8",
        )
    detail = re.sub(r"\s+", " ", detail).replace("|", "/")[:300]
    with chemin.open("a", encoding="utf-8") as f:
        f.write(
            f"| {maintenant()} | {'' if etape is None else etape} | "
            f"{ACTIONS_JOURNAL.get(action, action)} | {detail} |\n"
        )


def ecrire_synthese(session: Session, etapes: list[Etape]) -> Path:
    """Assemble le dossier complet dans `00-SYNTHESE.md`."""
    minutes = round(session.duree_secondes / 60)
    blocs = [
        f"# Dossier de prospective : {session.saisie.thematique} ({session.saisie.horizon})",
        (
            f"Session {session.id}, créée le {session.cree_le[:10]}, "
            f"parcours réalisé en {minutes} minutes de travail effectif."
        ),
        "## Strong context",
        strong_context(session),
    ]
    restitution = session.etapes[8].livrable
    if restitution:
        blocs += ["## Synthèse exécutive", restitution["synthese_executive"]]
    toutes_sources: dict[str, str] = {}
    for etape in etapes:
        etat = session.etapes[etape.numero]
        if etat.statut != "valide" or etat.livrable is None:
            continue
        livrable = etape.charger(etat.livrable)
        # Décale les titres d'un niveau pour les imbriquer dans la synthèse
        contenu = re.sub(
            r"^(#{2,5}) ", r"#\1 ", etape.markdown(livrable, session), flags=re.MULTILINE
        )
        blocs += [f"## Étape {etape.numero} : {etape.titre}", contenu]
        for s in etape.sources(livrable):
            toutes_sources.setdefault(s.url, s.nom)
    blocs += [
        "## Sources consolidées",
        "\n".join(f"- [{nom}]({url})" for url, nom in toutes_sources.items()) or "Aucune",
    ]
    chemin = session.chemin / "00-SYNTHESE.md"
    chemin.write_text("\n\n".join(blocs) + "\n", encoding="utf-8")
    return chemin
