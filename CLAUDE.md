# Consignes projet : Hack The Vibe, prospective business

Documents de référence (à relire en cas de doute, ils font foi) :
- [docs/brief-hack-the-vibe-prospective.md](docs/brief-hack-the-vibe-prospective.md) : produit, parcours HITL en 9 étapes, archivage `.md`, flux STEEPL.
- [docs/connexion-passerelle-generative-engine.md](docs/connexion-passerelle-generative-engine.md) : passerelle LLM Capgemini.

Langue : interface, sorties LLM, archives et commentaires métier en français.

## Stack

Back-end FastAPI (Python, `uv`) dans `backend/`, front Vite + React + TypeScript + Tailwind dans `frontend/`. Lancement : `lancer.cmd`.

## Modes d'exécution

- **Mode démo** (interrupteur de l'en-tête, par session) : parcours complet en 5 minutes de génération, avec des livrables resserrés et un budget de temps par étape (`parcours.BUDGET_DEMO`).
- **Mode complet** : parcours normal ; le budget ne sert que de garde-fou.
- **Hors ligne** (`DEMO=true` dans `.env`) : rejoue `fixtures/demo/` sans aucun appel réseau.
- Le modèle choisi dans l'en-tête s'applique à toutes les étapes et à l'assistant (`llm.utiliser_modele`).

## Appels aux modèles : passerelle Capgemini Generative Engine (obligatoire)

Tout appel LLM passe par la passerelle, via **un client unique** côté Python (`llm.py`). Aucun autre module n'instancie de client.

### Configuration

- Endpoint : `https://openai.generative-eu.engine.capgemini.com/v1`, protocole **OpenAI Chat Completions**. On utilise le SDK `openai` (`AsyncOpenAI`), quel que soit le modèle.
- Accès uniquement depuis le réseau ou le VPN d'entreprise. Le mode `DEMO=true` doit donc fonctionner sans passerelle.
- Variables d'environnement, dans `.env` hors versionnement uniquement :
  - `AGENT_API_KEY` : clé API. Replis acceptés : `GENERATIVE_ENGINE_API_KEY`, puis `OPENAI_API_KEY`.
  - `AGENT_BASE_URL` : endpoint de la passerelle.
  - `AGENT_MODEL` : modèle par défaut, `anthropic.claude-opus-5`.
  - `AGENT_MODEL_FAST` : modèle des tâches simples ou massives (extraction de signaux, 100 personas), par exemple `anthropic.claude-sonnet-5` ou `anthropic.claude-haiku-4-5-20251001-v1:0`.
- Paramètres du client :
  - `max_retries=3`, pour absorber les erreurs 5xx transitoires.
  - `timeout=httpx.Timeout(connect=20.0, read=900.0, write=60.0, pool=20.0)`. `read` est le délai toléré entre deux octets, pas la durée totale. La passerelle peut rester muette plusieurs minutes avant le premier token.
  - `max_tokens` ≤ 16 000.

### Modèles autorisés

Seuls les modèles dont les appels d'outils ont été vérifiés peuvent servir à la sortie structurée :
- `anthropic.claude-opus-5`, `anthropic.claude-sonnet-5`, `anthropic.claude-sonnet-4-6`, `anthropic.claude-haiku-4-5-20251001-v1:0`
- `openai.gpt-5`, `openai.gpt-5-mini`, `openai.gpt-5.4`
- `gemini-3.5-flash`
- `amazon.nova-pro-v1:0`, `amazon.nova-lite-v1:0`, `amazon.nova-micro-v1:0`
- `google.gemma-4-31b`
- `mistral.mistral-large-2402-v1:0`, `mistral.devstral-2-123b`

Interdits avec outils :
- `mistral.mistral-7b-instruct-v0:2` : erreur 403.
- `phi-4-mini-reasoning` : erreur Azure en amont.
- `google.gemma-3-*` : **échec silencieux**. Le modèle renvoie du texte avec `finish_reason: "stop"`, sans erreur et sans résultat.

Tout modèle absent de ces listes est considéré comme non vérifié.

### Sortie structurée

- Le brief demande du JSON strict validé par Zod. Côté Python, on remplace Zod par **Pydantic**.
- Chaque étape définit un modèle Pydantic de sortie. Ce même modèle génère le JSON Schema d'un **outil dédié** (`strict: true`) et valide la réponse. Le schéma et la validation ne peuvent donc pas diverger.
- On valide toujours côté serveur, même avec `strict: true`. Si la validation échoue, on fait une nouvelle tentative bornée, puis on renvoie une erreur explicite à l'utilisateur.
- Ne jamais imposer d'outil via `tool_choice` (fonction nommée ou `"required"`) : la passerelle renvoie une erreur 500 (constaté le 2026-09-25 sur Opus 5). On laisse `auto` et on exige l'appel dans la consigne.
- Toujours streamer (`stream=True`) : la passerelle renvoie une erreur 500 au bout de 180 s pour une réponse non streamée (constaté le 2026-09-25).
- La sortie JSON d'un outil plafonne vers 150 caractères par seconde (Sonnet 5), bien moins que le texte libre. Découper les gros livrables en appels parallèles d'environ 5 000 caractères au plus.
- Le modèle renvoie parfois un champ tableau sous forme de chaîne JSON (double encodage) : `llm._deballer` le corrige avant validation.
- Il faut vérifier que la réponse contient bien des `tool_calls`. Une réponse texte avec `finish_reason: "stop"` compte comme un échec.
- Chaque signal porte `hypothese_ia: bool`. Le modèle n'invente jamais de source ni d'URL.

### Indisponible via la passerelle

- **Recherche web du LLM** : l'API Chat Completions n'a pas d'outil de recherche web intégré. Le fallback « recherche web du LLM » du brief (niveau 0) doit passer par un connecteur explicite ou par GDELT.
- **Prompt caching** (`cache_control`) : le strong context est refacturé à chaque appel. On garde des prompts compacts et on plafonne les boucles à 12 tours maximum.
- **PDF natif, audio, vidéo, thinking adaptatif, paramètre `effort`** : non exposés. Pour un PDF, on extrait le texte avec `pypdf`.

### Robustesse

Il faut attraper les exceptions du SDK **et** celles de `httpx`, car un décrochage en plein stream lève `httpx.TimeoutException` brut :

```python
except openai.APIStatusError: ...                                  # 4xx / 5xx
except (openai.APITimeoutError, httpx.TimeoutException): ...       # blocage
except (openai.APIConnectionError, httpx.HTTPError): ...           # réseau / VPN
```

- `finish_reason: "content_filter"` : afficher un message explicite à l'utilisateur.
- Conserver les résultats partiels. Une relance poursuit le travail et ne repart pas de zéro, ce qui est cohérent avec les versions `.vN.md` du brief.
- Traitements massifs, comme les 100 personas : procéder par lots en parallèle (`asyncio.gather` avec un sémaphore) sur `AGENT_MODEL_FAST`.
- Utiliser 2 à 4 outils au maximum par appel.

### Sécurité

- Aucune clé dans le code. `.env` figure dans `.gitignore`.
- La clé de la passerelle est stockée chiffrée dans le Gestionnaire d'identification Windows (`uv run enregistrer-cle`, module `coffre.py`). `config.py` la lit si `AGENT_API_KEY` est vide.
- Les données envoyées transitent par la passerelle : respecter la politique de classification interne.
- L'application tourne en local et n'est pas exposée au réseau (bind sur `127.0.0.1`).

### Vérification rapide

`GET /v1/models`, puis un appel minimal avec un outil trivial pour confirmer la présence de `tool_calls`. Voir la section 8 de la doc passerelle.
