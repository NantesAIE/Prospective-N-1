# BRIEF PRINCIPAL : Application de prospective business assistée par IA

> Document de référence pour le vibecoding dans VS Code.
> Lire ce brief en entier avant de générer du code. En cas de doute, ce document fait foi.

---

## 1. Contexte

**Événement** : Hack The Vibe, hackathon interne de vibecoding.
**Thème imposé** : la prospective.

**Promesse produit** : une étude de prospective menée par un cabinet prend 3 à 6 mois. L'application permet à un entrepreneur d'obtenir en 30 minutes une première lecture prospective structurée, sourcée et validée pas à pas, jusqu'à l'horizon 2040.

**Persona cible** : un entrepreneur qui veut lancer un business. Il n'est pas expert en prospective. Il a une intuition (une thématique, un territoire) et veut savoir où aller, quels futurs anticiper et quoi faire dès maintenant.

**Horizon temporel** : 2040.

---

## 2. Principes directeurs (non négociables)

1. **Strong context** : l'utilisateur décrit son projet en langage naturel au démarrage. Ce texte, enrichi du user context, est injecté dans chaque appel LLM de chaque étape. Il n'est jamais perdu ni résumé à l'excès.
2. **Human in the loop (HITL)** : le parcours est découpé en étapes. Chaque étape se termine par une validation utilisateur explicite. Aucune étape ne démarre sans validation de la précédente.
3. **Archivage local en Markdown** : chaque validation produit un fichier `.md` horodaté, stocké localement. L'ensemble des fichiers constitue le dossier de prospective complet et rejouable.
4. **Traçabilité** : chaque signal affiché est rattaché à une source (nom, URL, date). Le LLM n'invente jamais de source. Un signal sans source est marqué « hypothèse IA ».
5. **Localisation active** : la localisation fait partie du user context dès le départ et détermine les flux de données activés.
6. **Méthode STEEPL** : Social, Technologique, Économique, Environnemental, Politique, Légal.
7. **Langue** : toute l'interface et toutes les sorties sont en français.

---

## 3. Parcours utilisateur segmenté

Le parcours compte 9 étapes. Chaque étape suit le même contrat :

| Élément | Description |
|---|---|
| Entrée | Strong context + sorties validées des étapes précédentes |
| Traitement | Appels aux flux de données et au LLM |
| Sortie | Livrable affiché à l'écran |
| Validation HITL | Trois actions : **Valider**, **Modifier** (édition directe ou commentaire), **Relancer** (nouvelle génération avec consigne) |
| Archive | Fichier `.md` écrit à la validation |

### Étape 0 : Strong context et user context

**But** : poser le socle de toute la session.

**Saisie utilisateur** :
- Description libre du projet en langage naturel (champ texte large, 200 à 2000 caractères).
- Thématique business (exemples : sport, santé, alimentation, mobilité).
- Localisation : pays obligatoire, code postal ou ville optionnel.
- Horizon : 2040 par défaut, modifiable.
- Ambition et contraintes libres (budget, taille visée, valeurs).

**Traitement** : le LLM reformule le projet en une fiche contexte structurée (problème, cible, proposition de valeur pressentie, territoire, hypothèses implicites) et géocode la localisation.

**Validation** : l'utilisateur confirme ou corrige la reformulation.

**Archive** : `00-contexte.md`

### Étape 1 : Activation des flux

**But** : choisir les sources pertinentes selon la localisation et la thématique.

**Traitement** : application de la règle d'activation (section 6). Affichage de la liste des flux activés, groupés par axe STEEPL et par niveau (Monde, Zone, Pays, Local).

**Validation** : l'utilisateur coche ou décoche des flux.

**Archive** : `01-flux-actives.md`

### Étape 2 : Collecte et analyse

**But** : rassembler la matière brute.

**Traitement** : appels parallèles aux flux activés, avec quatre familles de collecte :
- Analyse documentaire et statistique (open data).
- Bench concurrentiel (entreprises existantes sur le territoire et la thématique).
- Presse (GDELT, recherche web).
- Podcasts (Podcast Index, Radio France).

Le LLM extrait de chaque résultat des signaux candidats au format : titre, résumé en une phrase, source, URL, date, axe STEEPL présumé.

**Sortie** : liste de 20 à 40 signaux candidats, filtrables par axe et par source.

**Validation** : l'utilisateur écarte les signaux non pertinents et peut en ajouter manuellement.

**Archive** : `02-collecte.md`

### Étape 3 : Entretiens simulés (100 personas)

**But** : confronter la thématique à des points de vue variés.

**Traitement** :
- Génération de 100 personas synthétiques ancrés sur les données démographiques réelles du territoire (INSEE Mélodi en France, World Bank ailleurs) : âge, situation, usages, attentes.
- Chaque persona répond à un guide d'entretien court (5 questions) généré à partir du strong context.
- Synthèse automatique : attentes majeures, irritants, usages émergents, verbatims représentatifs, répartition des opinions.

**Mention obligatoire à l'écran** : « Entretiens simulés par IA, à confirmer par de vrais entretiens terrain. »

**Validation** : l'utilisateur valide la synthèse, peut ajouter des questions et relancer.

**Archive** : `03-entretiens.md` (guide, profil des 100 personas en tableau, synthèse, 10 verbatims)

### Étape 4 : Qualification STEEPL

**But** : transformer la matière en signaux qualifiés.

**Traitement** : le LLM classe chaque élément retenu (étapes 2 et 3) en :
- **Signal faible** : émergent, peu visible, potentiellement structurant.
- **Tendance lourde** : installée, prévisible, forte inertie.
- **Incertitude** : issue ouverte, fort impact possible.

Chaque élément reçoit un axe STEEPL, un score d'impact (1 à 5) et un score d'incertitude (1 à 5).

**Sortie** : tableau STEEPL et nuage de points impact / incertitude.

**Validation** : l'utilisateur ajuste les classements et les scores.

**Archive** : `04-steepl.md`

### Étape 5 : Cône des futurs

**But** : visualiser l'éventail des futurs d'aujourd'hui à 2040.

**Traitement** : le LLM positionne les tendances et signaux dans le cône des futurs : possibles, plausibles, probables, souhaitables.

**Sortie** : visualisation en cône (SVG), avec jalons 2030, 2035, 2040.

**Validation** : l'utilisateur valide ou déplace des éléments.

**Archive** : `05-cone-des-futurs.md`

### Étape 6 : Scénarios 2040, « où tu veux aller »

**But** : construire des futurs contrastés et choisir une cible.

**Traitement** :
- L'application propose les deux incertitudes critiques (impact et incertitude les plus élevés). L'utilisateur peut les changer.
- Génération d'une matrice 2x2, soit 4 scénarios. Pour chacun : titre évocateur, récit court (150 mots), signaux et tendances qui y mènent, conditions de bascule.

**Validation** : l'utilisateur choisit le scénario visé (« où tu veux aller »). Il peut en garder un second comme scénario de vigilance.

**Archive** : `06-scenarios.md`

### Étape 7 : Impact business et roadmap stratégique

**But** : passer du futur visé aux décisions d'aujourd'hui.

**Traitement** :
- **Impact business** : ce que devient le projet dans le scénario choisi (offre, clients, modèle économique, risques, opportunités), et sa robustesse dans les 3 autres scénarios (score de 1 à 5 par scénario).
- **Roadmap par backcasting** : du scénario 2040 vers aujourd'hui, jalons 2040, 2035, 2030, 18 mois, 90 jours.
- **Signaux à surveiller** : 5 indicateurs avancés, avec leur source de suivi.
- **Paris sans regret** : actions valables dans tous les scénarios.

**Validation** : l'utilisateur ajuste la roadmap.

**Archive** : `07-roadmap.md`

### Étape 8 : Restitution, narratif et artefact de design fiction

**But** : rendre le futur tangible et mémorable.

**Traitement** :
- **Narratif** : récit d'une journée type en 2040 dans le scénario choisi, du point de vue d'un client du business.
- **Artefact de design fiction** : un objet venu du futur, au choix de l'utilisateur : une de presse datée de 2040, publicité, fiche produit, avis client, offre d'emploi, notification d'application.

**Validation** : l'utilisateur choisit le format d'artefact et valide.

**Archive** : `08-restitution.md` puis génération de `00-SYNTHESE.md`, qui assemble l'ensemble.

---

## 4. Archivage local des validations

### Arborescence

```
archives/
  2026-09-25_sport-sante-nantes_a1b2/
    00-contexte.md
    01-flux-actives.md
    02-collecte.md
    03-entretiens.md
    04-steepl.md
    05-cone-des-futurs.md
    06-scenarios.md
    07-roadmap.md
    08-restitution.md
    00-SYNTHESE.md
    journal.md
```

- Nom du dossier de session : `AAAA-MM-JJ_<slug-thematique>-<slug-lieu>_<id court>`.
- `journal.md` trace chaque action HITL (validation, modification, relance) avec horodatage.
- Une relance ne supprime rien : l'ancienne version est conservée sous `<fichier>.v1.md`, `<fichier>.v2.md`.

### Gabarit d'un fichier d'étape

```markdown
---
session_id: a1b2
etape: 4
titre: Qualification STEEPL
statut: valide            # valide | modifie | relance
version: 2
horodatage: 2026-09-25T11:42:00+02:00
flux_utilises: [gdelt, recherche-entreprises, insee-melodi]
---

# Étape 4 : Qualification STEEPL

## Rappel du strong context
(texte intégral de l'étape 0)

## Livrable validé
(contenu de l'étape)

## Modifications utilisateur
(diff ou commentaire saisi, sinon « Aucune »)

## Sources
- [Nom de la source](URL), consultée le 2026-09-25
```

### Reprise de session

L'application liste les sessions existantes dans `archives/` et permet de reprendre une session à la dernière étape validée, en relisant les fichiers `.md`.

---

## 5. Architecture technique proposée

Stack par défaut, modifiable par l'équipe.

| Couche | Choix proposé | Raison |
|---|---|---|
| Front | Next.js (App Router), React, TypeScript, Tailwind | Rapide à vibecoder, routes API intégrées |
| Visualisations | SVG maison ou Recharts | Cône, matrice 2x2, nuage impact / incertitude |
| Back | Routes API Next.js (Node) | Accès au système de fichiers pour l'archivage |
| Archivage | Écriture de fichiers `.md` dans `./archives` | Exigence HITL locale |
| LLM | Fournisseur configurable via `.env` | Neutralité, bascule facile |
| Connecteurs | Un module par flux dans `/lib/flux/`, interface commune | Activation dynamique |

### Interface commune des connecteurs

```ts
interface Flux {
  id: string;                 // ex. "gdelt"
  nom: string;
  axes: Axe[];                // ["S","T","E1","E2","P","L"]
  niveau: "monde" | "zone" | "pays" | "local";
  pays?: string[];            // codes ISO si niveau pays ou local
  zone?: "UE";
  cleRequise: boolean;
  collecter(ctx: UserContext): Promise<SignalBrut[]>;
}

interface SignalBrut {
  titre: string;
  resume: string;
  source: string;
  url: string;
  date: string;
  axePresume?: Axe;
  fluxId: string;
}
```

### Robustesse de démo (obligatoire)

- Chaque connecteur a un **timeout de 8 secondes** et un **mode dégradé** : en cas d'échec, il renvoie un jeu de données de secours stocké dans `/fixtures/<flux>.json` et l'interface affiche « données de démonstration ».
- Un **mode démo** complet (`DEMO=true`) rejoue une session préenregistrée sans aucun appel réseau.

### Structure du projet

```
/app
  /(parcours)/etape/[n]/page.tsx
  /api/etape/[n]/route.ts
  /api/archives/route.ts
/components
  StepperHITL.tsx
  BarreValidation.tsx      # Valider / Modifier / Relancer
  TableauSTEEPL.tsx
  NuageImpactIncertitude.tsx
  ConeDesFuturs.tsx
  Matrice2x2.tsx
  RoadmapBackcasting.tsx
  ArtefactFiction.tsx
/lib
  /flux/                   # un fichier par connecteur
  /prompts/                # un fichier par étape
  activation.ts            # règle d'activation des flux
  archive.ts               # écriture et lecture des .md
  llm.ts                   # client LLM unique
/fixtures
/archives
```

---

## 6. Catalogue des flux de signaux (STEEPL)

### Règle d'activation selon la localisation du user context

La localisation est saisie au démarrage (pays obligatoire, code postal ou ville optionnel). L'application géocode l'entrée puis active les niveaux suivants :

- **Niveau 0, Monde** : toujours actif, quel que soit le pays.
- **Niveau 1, Zone** : actif si le pays appartient à l'Union européenne.
- **Niveau 2, Pays** : actif si un connecteur national existe (France, Royaume-Uni, États-Unis). Sinon, fallback sur le niveau 0 filtré par code pays ISO et sur la recherche web du LLM.
- **Niveau 3, Local** : actif si une localisation infra-nationale est fournie (code postal en France, coordonnées lat/lon partout ailleurs).

La liste des flux activés est affichée et validée à l'étape 1. Chaque signal collecté conserve : source, URL, date, niveau, axe STEEPL.

### Socle de géolocalisation

| Flux | Niveau | Usage | Clé |
|---|---|---|---|
| Open-Meteo Geocoding | 0 | Ville vers lat/lon, pays | Non |
| API Géo (Découpage administratif) | 3 FR | Code postal vers commune, département, région | Non |

### S : Social

| Flux | Niveau | Usage | Clé |
|---|---|---|---|
| World Bank Indicators | 0 | Démographie, éducation, santé par pays | Non |
| WHO GHO (OData) | 0 | Indicateurs de santé mondiaux | Non (à tester) |
| ILOSTAT | 0 | Emploi, travail | Non (à tester) |
| Podcast Index | 0 | Sujets émergents dans les podcasts | Oui, gratuite |
| Eurostat | 1 UE | Population, emploi, conditions de vie | Non |
| API Radio France | 2 FR | Émissions et podcasts français | Oui, gratuite |
| INSEE Mélodi | 3 FR | Démographie locale, revenus, CSP, ancrage des 100 personas | Non |

### T : Technologique

| Flux | Niveau | Usage | Clé |
|---|---|---|---|
| OpenAlex | 0 | Publications scientifiques, sujets de recherche émergents | Oui, gratuite |
| arXiv API | 0 | Prépublications, signaux très précoces | Non (à tester) |
| Hacker News API | 0 | Signaux tech et startups | Non (à tester) |
| INPI (RNE) | 2 FR | Données entreprises et propriété industrielle | Oui, gratuite |

### E : Économique

| Flux | Niveau | Usage | Clé |
|---|---|---|---|
| World Bank Indicators | 0 | PIB, inflation, commerce, 200+ pays | Non |
| IMF DataMapper | 0 | Macro et projections par pays | Non |
| Eurostat | 1 UE | Statistiques économiques UE | Non |
| API Recherche d'entreprises | 2/3 FR | Bench concurrentiel local par code postal et code NAF | Non |
| BODACC | 2/3 FR | Créations, cessions, défaillances par secteur | Non |
| API données ouvertes Urssaf | 2 FR | Effectifs et masse salariale par secteur | Non (à tester) |

### E : Environnemental

| Flux | Niveau | Usage | Clé |
|---|---|---|---|
| Open-Meteo Climate API | 0/3 | Projections climatiques CMIP6 jusqu'à 2050 par lat/lon | Non |
| Open-Meteo Air Quality | 0/3 | Qualité de l'air | Non |
| Géorisques | 3 FR | Risques naturels et technologiques locaux | Non |
| DPE logements | 3 FR | Performance énergétique du bâti | Non |
| Données locales de consommation d'énergie | 3 FR | Consommation énergétique locale | Non |
| Impact CO2 | 2 FR | Empreinte carbone des usages | Non |

### P : Politique

| Flux | Niveau | Usage | Clé |
|---|---|---|---|
| GDELT DOC 2.0 | 0 | Vélocité médiatique d'un sujet, 65+ langues, filtre par pays | Non |
| BOAMP | 2 FR | Marchés publics, priorités des collectivités | Non |

### L : Légal

| Flux | Niveau | Usage | Clé |
|---|---|---|---|
| EUR-Lex (CELLAR SPARQL) | 1 UE | Règlements et directives UE | Non |
| Légifrance (PISTE) | 2 FR | Droit français en vigueur | Oui, gratuite |
| legislation.gov.uk | 2 UK | Droit britannique | Non |
| Federal Register | 2 US | Réglementation fédérale américaine | Non (à tester) |

### Veille transverse

| Flux | Niveau | Usage | Clé |
|---|---|---|---|
| Recherche web du LLM | 0 | Complément et fallback pour tout pays sans connecteur | Selon LLM |

### Exclus

- Google Trends : API officielle en alpha sur candidature, pytrends archivé.

### Contraintes

- Prioriser les flux sans clé pour la démo.
- Créer les clés gratuites (Podcast Index, OpenAlex, PISTE, Radio France, INPI) avant le hackathon et les placer dans `.env.local`.
- Respecter les limites de débit (Recherche d'entreprises : 7 requêtes par seconde ; GDELT : 250 articles par requête, index sur environ 3 mois).
- Open-Meteo Climate s'arrête en 2050 : suffisant pour l'horizon 2040.

---

## 7. Consignes pour les prompts LLM

Chaque prompt d'étape (`/lib/prompts/etape-N.ts`) suit la structure suivante :

1. **Rôle** : « Tu es un prospectiviste expérimenté qui accompagne un entrepreneur. »
2. **Strong context** : texte intégral de l'étape 0.
3. **Acquis validés** : sorties validées des étapes précédentes utiles à l'étape.
4. **Données** : signaux et données collectés, avec leurs sources.
5. **Tâche** : consigne précise de l'étape.
6. **Contraintes** :
   - Répondre en français.
   - Ne jamais inventer de source ni d'URL. Tout élément non sourcé est marqué `hypothese_ia: true`.
   - Rester cohérent avec le territoire et l'horizon.
7. **Format de sortie** : JSON strict validé par un schéma (Zod), converti ensuite en Markdown pour l'archive.

---

## 8. Interface et expérience

- **Stepper horizontal** permanent : 9 étapes, statut visible (à faire, en cours, validée).
- **Rappel du strong context** dans un panneau latéral repliable, toujours accessible.
- **Barre de validation HITL** fixe en bas de chaque étape : Valider, Modifier, Relancer (avec champ de consigne).
- **Indicateur de source** sur chaque signal : pastille de niveau (Monde, UE, Pays, Local) et lien cliquable.
- **Écrans clés à soigner pour la démo** : matrice 2x2 des scénarios, cône des futurs, artefact de design fiction.
- **Temps affiché** : chronomètre de session, pour matérialiser la promesse « 30 minutes au lieu de 3 à 6 mois ».

---

## 9. Scénario de démo

- **Projet** : « Je veux créer un service de sport santé pour les seniors actifs, avec des séances en extérieur et un suivi connecté. »
- **Thématique** : sport, santé.
- **Localisation** : France, 44000 (Nantes).
- **Horizon** : 2040.
- **Artefact final** : une de presse locale datée de 2040.

Préparer ce scénario en mode démo (`DEMO=true`) avec fixtures complètes, et le tester en conditions réelles au moins une fois.

---

## 10. Priorités de construction

### P0 : MVP démontrable
- Étape 0 (strong context et user context).
- Étape 1 (activation des flux) avec 5 connecteurs sans clé : GDELT, API Recherche d'entreprises, BODACC, API Géo, Open-Meteo Climate.
- Étapes 2, 4, 6, 7.
- Barre HITL et archivage `.md` complet, avec `journal.md`.
- Mode démo avec fixtures.

### P1 : Différenciation
- Étape 3 (entretiens simulés, 100 personas).
- Étape 5 (cône des futurs).
- Étape 8 (narratif et artefact de design fiction).
- `00-SYNTHESE.md`.

### P2 : Bonus
- Connecteurs à clé (OpenAlex, Podcast Index, Légifrance, Radio France).
- Connecteurs UK et US.
- Reprise de session.
- Export PDF de la synthèse.

---

## 11. Définition de terminé

- Un utilisateur réalise le parcours complet du scénario de démo en moins de 30 minutes.
- Chaque étape validée produit un fichier `.md` conforme au gabarit.
- Chaque signal affiché porte une source ou la mention « hypothèse IA ».
- L'application fonctionne sans réseau en mode démo.
- Aucune clé d'API n'est présente dans le code source (uniquement dans `.env.local`, ignoré par Git).
