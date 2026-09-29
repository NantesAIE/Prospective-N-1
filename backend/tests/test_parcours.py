"""Parcours complet en mode démo, hors ligne, dans un dossier d'archives temporaire."""

import pytest

from prospective import parcours
from prospective import session as sessions
from prospective.api import SAISIE_DEMO
from prospective.config import parametres
from prospective.etapes import ETAPES
from prospective.session import ErreurSession

OPTIONS_VALIDATION = {6: {"choix": {"cible": "++", "vigilance": "--"}}}


@pytest.fixture
def demo(monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO", "true")
    monkeypatch.setenv("DOSSIER_ARCHIVES", str(tmp_path))
    parametres.cache_clear()
    if not (parametres().dossier_fixtures / "demo" / "etape-8.json").exists():
        pytest.skip("Fixtures de démo absentes : lancer scripts/enregistrer_demo.py")
    yield tmp_path
    parametres.cache_clear()


async def test_ordre_hitl_impose(demo):
    session = parcours.creer_session(SAISIE_DEMO)
    with pytest.raises(ErreurSession, match="doit être validée"):
        await parcours.generer(session.id, 2)


async def test_parcours_complet(demo):
    session = parcours.creer_session(SAISIE_DEMO)
    for etape in ETAPES:
        await parcours.generer(session.id, etape.numero)
        session = await parcours.valider(
            session.id, etape.numero, options=OPTIONS_VALIDATION.get(etape.numero, {})
        )

    assert all(e.statut == "valide" for e in session.etapes)
    assert session.contexte is not None
    fichiers = parcours.fichiers(session)
    for etape in ETAPES:
        assert f"{etape.fichier}.md" in fichiers
    assert "00-SYNTHESE.md" in fichiers and "journal.md" in fichiers

    contenu = (session.chemin / "04-steepl.md").read_text(encoding="utf-8")
    assert contenu.startswith("---\nsession_id: ")
    for section in ["## Rappel du strong context", "## Livrable validé", "## Sources"]:
        assert section in contenu
    entretiens = (session.chemin / "03-entretiens.md").read_text(encoding="utf-8")
    assert "Entretiens simulés par IA, à confirmer par de vrais entretiens terrain." in entretiens


async def test_relance_conserve_les_versions(demo):
    session = parcours.creer_session(SAISIE_DEMO)
    await parcours.generer(session.id, 0)
    await parcours.generer(session.id, 0, consigne="Insiste sur les aidants")
    session = await parcours.valider(session.id, 0)
    await parcours.generer(session.id, 1)
    await parcours.valider(session.id, 1)

    # Reprise de l'étape 0 : l'étape 1 repasse à faire, rien n'est supprimé
    await parcours.modifier(session.id, 0, None, "Cible élargie aux aidants")
    session = await parcours.valider(session.id, 0)
    assert session.etapes[1].statut == "a_faire"
    fichiers = parcours.fichiers(session)
    assert {"00-contexte.md", "00-contexte.v1.md", "00-contexte.v2.md"} <= set(fichiers)
    assert "Insiste sur les aidants" in (session.chemin / "00-contexte.md").read_text(
        encoding="utf-8"
    )
    journal = (session.chemin / "journal.md").read_text(encoding="utf-8")
    assert journal.count("Validation") == 3 and "Relance" in journal


async def test_validation_scenarios_exige_une_cible(demo):
    session = parcours.creer_session(SAISIE_DEMO)
    for n in range(6):
        await parcours.generer(session.id, n)
        await parcours.valider(session.id, n)
    await parcours.generer(session.id, 6)
    with pytest.raises(ErreurSession, match="scénario visé"):
        await parcours.valider(session.id, 6)
    assert sessions.charger(session.id).etapes[6].statut == "brouillon"
