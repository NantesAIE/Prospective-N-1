# Se connecter à la passerelle Capgemini Generative Engine (EU)

> Document autonome, à copier dans tout projet d'agent devant appeler des LLM
> via la passerelle Capgemini. Les informations de compatibilité proviennent de
> tests **en conditions réelles** (sondage du 2026-08-03), pas de la
> documentation éditeur.

---

## 1. L'essentiel

| Paramètre | Valeur |
| --- | --- |
| Endpoint | `https://openai.generative-eu.engine.capgemini.com/v1` |
| Protocole | **OpenAI Chat Completions** (`POST /v1/chat/completions`) |
| Authentification | Clé API dans l'en-tête `Authorization: Bearer <clé>` (géré par le SDK `openai`) |
| Catalogue de modèles | `GET /v1/models` |
| Modèle recommandé | `anthropic.claude-opus-5` |
| Réseau | Accessible depuis le réseau / VPN d'entreprise |

La passerelle expose des modèles de plusieurs fournisseurs (Anthropic, OpenAI,
Google, Amazon, Mistral…) derrière **une seule API au format OpenAI**. On
l'appelle donc avec le SDK `openai` standard, quel que soit le modèle ciblé.

## 2. Configuration minimale

Variables d'environnement (fichier `.env` recommandé, jamais commité) :

```bash
AGENT_API_KEY=votre-cle-api
AGENT_BASE_URL=https://openai.generative-eu.engine.capgemini.com/v1
AGENT_MODEL=anthropic.claude-opus-5
```

Client Python :

```python
import httpx
import openai

client = openai.AsyncOpenAI(          # ou openai.OpenAI en synchrone
    api_key=os.environ["AGENT_API_KEY"],
    base_url=os.environ["AGENT_BASE_URL"],
    max_retries=3,                    # 5xx transitoires côté fournisseur amont
    timeout=httpx.Timeout(connect=20.0, read=900.0, write=60.0, pool=20.0),
)

response = await client.chat.completions.create(
    model="anthropic.claude-opus-5",
    max_tokens=16_000,
    messages=[
        {"role": "system", "content": "Tu es un assistant..."},
        {"role": "user", "content": "Bonjour"},
    ],
)
```

> **`read=900` n'est pas une durée totale.** C'est le délai toléré **entre deux
> octets** reçus. La passerelle peut rester muette plusieurs minutes pendant que
> le modèle raisonne avant son premier token — un timeout de lecture trop bas
> coupe une requête qui se déroulait normalement.

## 3. Ce qui fonctionne (vérifié sur la passerelle)

- **Streaming** (`stream=True`), y compris les deltas d'appels d'outils.
- **Appels d'outils (function calling)**, y compris **parallèles**, sur les
  modèles listés compatibles ci-dessous.
- **`strict: true`** sur les définitions de fonctions (sortie structurée
  conforme au JSON Schema). Validez malgré tout côté serveur (Pydantic) : une
  passerelle qui ignorerait silencieusement `strict` ne doit pas pouvoir
  corrompre vos résultats.
- **Vision** : images en `image_url` (data URL base64). Redimensionnez à
  **1568 px de côté long** maximum — la passerelle proxifie vers Bedrock, dont
  les modèles Claude réduisent au-delà de toute façon.
- **`max_tokens`** : la passerelle annonce 16 000 en sortie pour le palier Opus.

## 4. Ce qui NE fonctionne PAS

La passerelle expose l'API *OpenAI Chat Completions*, **pas** l'API Anthropic
Messages. Les fonctions propres à l'API Anthropic sont donc indisponibles, même
sur les modèles Claude :

| Indisponible | Conséquence / contournement |
| --- | --- |
| PDF natif | Extraire le texte soi-même (`pypdf`) ; PDF scanné → OCR ou export en images. |
| `cache_control` (prompt caching) | Le contexte est refacturé en entier à chaque appel : plafonnez le nombre de tours de votre boucle agentique. |
| *Adaptive thinking* / paramètre `effort` | Non exposés. |
| Audio / vidéo | Aucun canal d'entrée. |

## 5. Choix du modèle — compatibilité mesurée

**Piège principal : les échecs silencieux.** Certains modèles ne supportent pas
les appels d'outils mais répondent quand même du texte avec un
`finish_reason: "stop"` parfaitement normal — aucune erreur, zéro résultat. Ne
vous fiez pas à l'absence d'erreur ; fiez-vous à cette liste (sondage du
2026-08-03) ou re-testez avec une requête minimale portant un outil.

**Appels d'outils vérifiés OK :**

```
anthropic.claude-opus-5          ← recommandé, validé sur analyse complète
anthropic.claude-sonnet-5
anthropic.claude-sonnet-4-6
anthropic.claude-haiku-4-5-20251001-v1:0
openai.gpt-5
openai.gpt-5-mini
openai.gpt-5.4
gemini-3.5-flash
amazon.nova-pro-v1:0
amazon.nova-lite-v1:0
amazon.nova-micro-v1:0
google.gemma-4-31b
mistral.mistral-large-2402-v1:0
mistral.devstral-2-123b
```

**Vérifiés inutilisables avec des outils :**

| Modèle | Symptôme |
| --- | --- |
| `mistral.mistral-7b-instruct-v0:2` | HTTP 403 explicite : « doesn't support Function (Tools) Calling ». |
| `phi-4-mini-reasoning` | Erreur Azure en amont dès qu'une requête porte des outils. |
| `google.gemma-3-*` | **Échec silencieux** : texte brut, pas d'appel d'outil, pas d'erreur. |

Tout modèle ajouté à la passerelle après cette campagne doit être considéré
comme **non vérifié** jusqu'à test.

Sonnet et Haiku réduisent nettement la latence sur les tâches simples ; Opus
reste le plus fiable pour les tâches agentiques exigeantes.

## 6. Robustesse — comportements observés de la passerelle

- **5xx transitoires** : le fournisseur amont renvoie parfois des erreurs
  passagères. `max_retries=3` sur le client les absorbe.
- **Latence avant premier token** : plusieurs minutes possibles sur les gros
  contextes. D'où `read_timeout` généreux (900 s entre deux octets).
- **Décrochage en cours de stream** : un blocage au milieu d'un stream lève
  l'erreur `httpx` brute (`httpx.TimeoutException`), pas l'exception du SDK —
  celui-ci n'enveloppe que les échecs survenant *avant* le début de la réponse.
  Attrapez les deux :

  ```python
  try:
      async for chunk in stream:
          ...
  except openai.APIStatusError as exc:      # 4xx / 5xx
      ...
  except (openai.APITimeoutError, httpx.TimeoutException):   # stall
      ...
  except (openai.APIConnectionError, httpx.HTTPError):       # réseau / VPN
      ...
  ```

- **Conservez les résultats partiels** : si la passerelle coupe au milieu d'une
  boucle agentique, tout ce qui a déjà été produit doit rester exploitable, et
  la relance doit poursuivre au lieu de repartir de zéro.
- **Filtre de contenu** : `finish_reason: "content_filter"` peut survenir ;
  prévoyez un message utilisateur explicite.

## 7. Boucle agentique de référence

Schéma d'un tour, tel qu'éprouvé sur la passerelle :

```
requête (messages + tools, stream)
  → assembler le message assistant depuis les deltas
  → finish_reason == "tool_calls" ?
        oui : exécuter les outils, ajouter un message {"role": "tool",
              "tool_call_id": ..., "content": ...} PAR appel, reboucler
        non : stop
```

Recommandations issues de l'expérience :

- **Peu d'outils** (2–4) : une surface d'outils large dégrade la qualité de
  sélection du modèle.
- **Un schéma unique** : le même modèle Pydantic génère le JSON Schema envoyé
  au modèle *et* valide ce qui revient — schéma et validation ne peuvent pas
  diverger.
- **Plafond de tours** (garde-fou anti-boucle, p. ex. 12) : sans cache de
  prompt, chaque tour réenvoie tout le contexte et les tokens d'entrée croissent
  vite.
- **Sortie structurée via un outil** dédié (`strict: true`) plutôt qu'un bloc
  JSON final : chaque résultat est validé et exploitable dès son émission.

## 8. Vérification rapide de la connexion

```bash
# Catalogue des modèles
curl -s -H "Authorization: Bearer $AGENT_API_KEY" \
  "https://openai.generative-eu.engine.capgemini.com/v1/models"

# Appel minimal
curl -s -H "Authorization: Bearer $AGENT_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"anthropic.claude-haiku-4-5-20251001-v1:0","max_tokens":50,"messages":[{"role":"user","content":"ping"}]}' \
  "https://openai.generative-eu.engine.capgemini.com/v1/chat/completions"
```

Pour vérifier le support des outils d'un modèle, ajoutez une définition d'outil
triviale et contrôlez que la réponse contient bien `tool_calls` — et non du
texte avec `finish_reason: "stop"` (l'échec silencieux du §5).

## 9. Sécurité

- La clé API est un secret : `.env` hors versionnement (`.gitignore`), jamais
  en dur dans le code. Prévoir des variables de repli est utile
  (`AGENT_API_KEY`, `GENERATIVE_ENGINE_API_KEY`, `OPENAI_API_KEY`).
- Les documents envoyés **transitent par la passerelle** : appliquez la
  politique interne de classification des données au corpus traité.
- N'exposez pas votre application au réseau sans couche d'authentification.

---

*Référence d'implémentation complète : projet `agent-cas-usage-ia`
(`app/config.py`, `app/agent/runner.py`, `app/gateway_models.py`).*
