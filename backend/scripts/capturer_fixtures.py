"""Capture des fixtures de flux à partir de vrais appels, sur le scénario de démo.

Scénario : service de sport santé pour seniors actifs, 44000 Nantes, horizon 2040.
Écrit fixtures/flux/<id>.json, geo.json et demographie.json. Un flux en échec garde sa
fixture précédente.

Usage, depuis backend/ :
    uv run --no-sync python scripts/capturer_fixtures.py [flux_id ...]
"""

import asyncio
import json
import os
import sys
import time

# Les captures exigent le réseau, même si le .env active le mode démo
os.environ["DEMO"] = "false"

from prospective.config import parametres
from prospective.flux import CATALOGUE, outils
from prospective.flux.demographie import _profil_en_ligne
from prospective.flux.geo import _geocoder_en_ligne
from prospective.modeles import ContexteUtilisateur, SaisieProjet

SAISIE = SaisieProjet(
    description=(
        "Je veux créer un service de sport santé pour les seniors actifs, "
        "avec des séances en extérieur et un suivi connecté."
    ),
    thematique="sport, santé",
    pays="France",
    lieu="44000",
    horizon=2040,
)
MOTS_CLES = ["sport santé", "seniors", "activité physique adaptée", "vieillissement actif"]
MOTS_CLES_EN = ["senior fitness", "active ageing", "health sport", "wearables elderly"]
CODES_NAF = ["93.13Z", "93.19Z", "85.51Z", "86.90E"]
TENTATIVES = 3


def ecrire(dossier, nom: str, contenu) -> None:
    chemin = dossier / nom
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  écrit : {chemin}")


async def principal(ids: list[str]) -> None:
    dossier = parametres().dossier_fixtures / "flux"
    dossier.mkdir(parents=True, exist_ok=True)

    loc = await _geocoder_en_ligne(SAISIE)
    print(f"Géocodage : {loc.ville} ({loc.code_commune}), {loc.lat}, {loc.lon}")
    if not ids:
        ecrire(dossier, "geo.json", loc.model_dump(mode="json"))
        profil = await _profil_en_ligne(loc)
        if profil.get("echelle") == "commune":
            ecrire(dossier, "demographie.json", profil)
        else:
            print("  Mélodi indisponible : demographie.json conservé")

    ctx = ContexteUtilisateur(
        saisie=SAISIE,
        localisation=loc,
        mots_cles=MOTS_CLES,
        mots_cles_en=MOTS_CLES_EN,
        codes_naf=CODES_NAF,
    )
    # Hors application, on tolère les API lentes (Géorisques, World Bank)
    outils.DELAI_INTERNE = 45.0
    bilan = {}
    async with outils.client_tls(timeout=60.0) as client:
        for flux in CATALOGUE:
            if ids and flux.id not in ids:
                continue
            signaux, erreur = [], ""
            for tentative in range(1, TENTATIVES + 1):
                debut = time.monotonic()
                try:
                    signaux = await flux.collecter(ctx, client)
                    break
                except Exception as exc:  # noqa: BLE001 : on journalise et on retente
                    erreur = f"{type(exc).__name__} : {exc}"
                    print(f"{flux.id} : tentative {tentative} en échec ({erreur})")
                    await asyncio.sleep(6)
            duree = time.monotonic() - debut
            if signaux:
                print(f"{flux.id} : {len(signaux)} signaux en {duree:.1f} s")
                donnees = [s.model_dump(mode="json", exclude={"donnees_demo"}) for s in signaux]
                ecrire(dossier, f"{flux.id}.json", donnees)
                bilan[flux.id] = len(signaux)
            else:
                print(f"{flux.id} : aucun signal, fixture conservée ({erreur or 'réponse vide'})")
                bilan[flux.id] = 0

    print("\nBilan :")
    for flux_id, nombre in bilan.items():
        print(f"  {flux_id:24} {nombre}")


if __name__ == "__main__":
    asyncio.run(principal(sys.argv[1:]))
