import asyncio
import json

import pytest
from pydantic import BaseModel

from prospective import llm
from prospective.llm import AppelOutil, Reponse


class Signal(BaseModel):
    titre: str
    hypothese_ia: bool


def _reponse(finish_reason, arguments=None, contenu=""):
    appels = [AppelOutil(id="c1", nom="emettre", arguments=arguments)] if arguments else []
    return Reponse(finish_reason=finish_reason, contenu=contenu, appels=appels)


@pytest.fixture
def appels_simules(monkeypatch):
    def installer(*reponses, attente=0.0):
        file = list(reponses)

        async def faux_appel(**_):
            await asyncio.sleep(attente)
            return file.pop(0)

        monkeypatch.setattr(llm, "_appeler", faux_appel)

    return installer


async def test_echec_silencieux_puis_succes(appels_simules):
    appels_simules(
        _reponse("stop", contenu="Voici du texte"),
        _reponse("tool_calls", arguments='{"titre": "Sport senior", "hypothese_ia": true}'),
    )
    resultat = await llm.generer_structure(Signal, [], nom_outil="emettre", description="x")
    assert resultat == Signal(titre="Sport senior", hypothese_ia=True)


async def test_validation_echoue_toujours(appels_simules):
    appels_simules(*[_reponse("tool_calls", arguments='{"titre": 3}') for _ in range(3)])
    with pytest.raises(llm.ErreurLLM, match="après 3 essais"):
        await llm.generer_structure(Signal, [], nom_outil="emettre", description="x")


async def test_filtre_de_contenu(appels_simules):
    appels_simules(_reponse("content_filter"))
    with pytest.raises(llm.ErreurLLM, match="filtre de contenu"):
        await llm.generer_structure(Signal, [], nom_outil="emettre", description="x")


async def test_delai_depasse(appels_simules):
    appels_simules(_reponse("tool_calls", arguments="{}"), attente=1.0)
    with pytest.raises(llm.ErreurLLM, match="interrompue"):
        await llm.generer_structure(Signal, [], nom_outil="emettre", description="x", delai=0.05)


def test_modele_de_session():
    with llm.utiliser_modele("anthropic.claude-haiku-4-5-20251001-v1:0"):
        assert llm.modele() == "anthropic.claude-haiku-4-5-20251001-v1:0"
        assert llm.modele(rapide=True) == "anthropic.claude-haiku-4-5-20251001-v1:0"
    with (
        pytest.raises(llm.ErreurLLM, match="pas vérifié"),
        llm.utiliser_modele("google.gemma-3-12b"),
    ):
        pass


async def test_double_encodage_corrige(appels_simules):
    class Liste(BaseModel):
        signaux: list[Signal]

    interne = json.dumps({"signaux": [{"titre": "A", "hypothese_ia": False}]})
    arguments = json.dumps({"signaux": interne})
    appels_simules(Reponse("tool_calls", "", [AppelOutil("c1", "emettre", arguments)]))
    resultat = await llm.generer_structure(Liste, [], nom_outil="emettre", description="x")
    assert resultat.signaux[0].titre == "A"
