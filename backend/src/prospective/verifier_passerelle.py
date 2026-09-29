"""Vérification rapide de la passerelle : catalogue des modèles, puis appel minimal avec outil.

Usage : `uv run verifier-passerelle` (réseau ou VPN d'entreprise requis).
"""

import asyncio
import sys

from pydantic import BaseModel

from prospective import llm


class Ping(BaseModel):
    reponse: str


async def verifier() -> int:
    try:
        catalogue = await llm.client().models.list()
        ids = sorted(m.id for m in catalogue.data)
        print(f"Catalogue : {len(ids)} modèles disponibles.")
        for rapide in (False, True):
            nom = llm.modele(rapide)
            presence = "présent" if nom in ids else "ABSENT du catalogue"
            print(f"  {nom} : {presence}")

        for rapide in (False, True):
            resultat = await llm.generer_structure(
                Ping,
                [{"role": "user", "content": "Réponds « pong » via l'outil."}],
                nom_outil="repondre",
                description="Renvoie la réponse au ping.",
                rapide=rapide,
                max_tokens=100,
                tentatives=0,
            )
            print(f"Appel d'outil OK sur {llm.modele(rapide)} : {resultat.reponse!r}")
    except llm.ErreurLLM as exc:
        print(f"ÉCHEC : {exc}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    sys.exit(asyncio.run(verifier()))
