# Prospective 2040 : Hack The Vibe

Application de prospective business assistée par IA. Voir [docs/brief-hack-the-vibe-prospective.md](docs/brief-hack-the-vibe-prospective.md) et [CLAUDE.md](CLAUDE.md).

## Stack

- **Back-end** : Python 3.12+, FastAPI, Pydantic, SDK `openai` vers la passerelle Capgemini (`backend/`, géré par `uv`).
- **Front** : React 19, TypeScript, Vite, Tailwind CSS 4, Recharts (`frontend/`).
- Tout tourne en local sur `127.0.0.1` : API sur le port 8000, interface sur le port 5173 (Vite relaie `/api` vers l'API).

## Prérequis

- [uv](https://docs.astral.sh/uv/) et Node.js 20+ (npm).
- Réseau ou VPN d'entreprise pour la passerelle LLM, sauf en mode démo.

## Lancer

```powershell
.\lancer.cmd            # ou double-clic : installe si besoin, démarre, ouvre le navigateur
.\lancer.cmd -Demo      # mode démo, sans passerelle ni réseau
```

Clé de la passerelle : lancez une fois `cd backend; uv run enregistrer-cle`. La clé est chiffrée dans le Gestionnaire d'identification Windows, jamais écrite dans le projet. `AGENT_API_KEY` dans `.env` reste vide, mais reste prioritaire si on la renseigne. Ctrl+C arrête les deux serveurs.

Lancement manuel, dans deux terminaux :

```powershell
cd backend;  uv run serveur
cd frontend; npm run dev
```

## Commandes utiles

| Commande | Effet |
|---|---|
| `uv run verifier-passerelle` (dans `backend/`) | Catalogue des modèles et appel minimal avec outil |
| `uv run pytest` / `uv run ruff check .` (dans `backend/`) | Tests et lint Python |
| `npm run build` / `npm run lint` (dans `frontend/`) | Build et lint du front |

## Arborescence

```
backend/src/prospective/
  config.py               # paramètres (.env)
  llm.py                  # client LLM unique + sortie structurée Pydantic
  main.py                 # application FastAPI
  flux/                   # un connecteur par flux de données
  prompts/                # un prompt par étape
frontend/src/             # interface React
fixtures/                 # jeux de données de secours et mode démo
archives/                 # sessions archivées en .md (non versionnées)
```
