"""Joue le scénario de démo de bout en bout en conditions réelles et l'enregistre pour DEMO=true.

Chaque étape est générée puis validée automatiquement. Les livrables sont copiés dans
fixtures/demo/etape-N.json. La session reste consultable dans archives/.

Usage (réseau ou VPN d'entreprise requis) :
    uv run python scripts/enregistrer_demo.py [--mode demo|complet] [--modele NOM] [--sans-fixtures]
"""

import argparse
import asyncio
import json
import logging
import time

from prospective import parcours
from prospective import session as sessions
from prospective.api import SAISIE_DEMO
from prospective.config import parametres
from prospective.etapes import ETAPES

OPTIONS_GENERATION = {8: {"format_artefact": "une_de_presse"}}
OPTIONS_VALIDATION = {6: {"choix": {"cible": "++", "vigilance": "--"}}}


async def main(mode: str, modele: str | None, fixtures: bool) -> None:
    p = parametres()
    if p.demo:
        raise SystemExit("Désactivez DEMO pour enregistrer une session réelle.")
    session = parcours.creer_session(SAISIE_DEMO, mode, modele)
    print(
        f"Session {session.id} ({mode}, {modele or 'modèle par défaut'}) : {session.chemin}",
        flush=True,
    )
    debut = time.perf_counter()
    for etape in ETAPES:
        n = etape.numero
        t0 = time.perf_counter()
        await parcours.generer(session.id, n, options=OPTIONS_GENERATION.get(n, {}))
        await parcours.valider(session.id, n, options=OPTIONS_VALIDATION.get(n, {}))
        print(f"Étape {n} ({etape.titre}) : {time.perf_counter() - t0:.0f} s", flush=True)

    print(f"Parcours complet en {(time.perf_counter() - debut) / 60:.1f} min.", flush=True)
    if not fixtures:
        return
    session = sessions.charger(session.id)
    dossier = p.dossier_fixtures / "demo"
    dossier.mkdir(parents=True, exist_ok=True)
    for etat in session.etapes:
        (dossier / f"etape-{etat.numero}.json").write_text(
            json.dumps(etat.livrable, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"Fixtures écrites dans {dossier}")


if __name__ == "__main__":
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--mode", choices=["demo", "complet"], default="complet")
    arguments.add_argument("--modele", default=None)
    arguments.add_argument("--sans-fixtures", action="store_true")
    a = arguments.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s : %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run(main(a.mode, a.modele, not a.sans_fixtures))
