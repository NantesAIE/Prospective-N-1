"""Stockage chiffré de la clé API de la passerelle.

La clé est rangée dans le trousseau du système (Gestionnaire d'identification Windows,
chiffré par DPAPI et lié à la session de l'utilisateur), jamais dans un fichier du projet.

Usage :
    uv run enregistrer-cle              saisie masquée de la clé
    uv run enregistrer-cle --supprimer  retire la clé du trousseau
"""

import argparse
import getpass
import sys

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE = "hack-the-vibe-prospective"
COMPTE = "AGENT_API_KEY"


def lire_cle() -> str | None:
    try:
        return keyring.get_password(SERVICE, COMPTE)
    except KeyringError:
        return None


def enregistrer_cle(cle: str) -> None:
    keyring.set_password(SERVICE, COMPTE, cle)


def supprimer_cle() -> None:
    try:
        keyring.delete_password(SERVICE, COMPTE)
    except PasswordDeleteError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Gère la clé API chiffrée de la passerelle.")
    parser.add_argument("--supprimer", action="store_true", help="retire la clé du trousseau")
    args = parser.parse_args()

    if args.supprimer:
        supprimer_cle()
        print("Clé retirée du trousseau.")
        return

    # Saisie masquée en terminal, ou lecture sur l'entrée standard si elle est redirigée
    cle = (getpass.getpass("Clé API : ") if sys.stdin.isatty() else sys.stdin.read()).strip()
    if not cle:
        sys.exit("Aucune clé saisie.")
    enregistrer_cle(cle)
    print(f"Clé enregistrée dans le trousseau ({keyring.get_keyring().name}).")
