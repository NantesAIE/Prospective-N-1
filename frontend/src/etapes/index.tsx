import type { ComponentType } from 'react'
import type { Session } from '../types'
import type { Options, OptionsEtapeProps, VueEtapeProps } from './commun'
import { Etape0Contexte } from './Etape0Contexte'
import { Etape1Flux } from './Etape1Flux'
import { Etape2Collecte } from './Etape2Collecte'
import { Etape3Entretiens, OptionsEntretiens } from './Etape3Entretiens'
import { Etape4Steepl } from './Etape4Steepl'
import { Etape5Cone } from './Etape5Cone'
import { Etape6Scenarios, OptionsScenarios, optionsInitialesScenarios } from './Etape6Scenarios'
import { Etape7Roadmap } from './Etape7Roadmap'
import { Etape8Restitution, OptionsRestitution } from './Etape8Restitution'

export interface DefinitionEtape {
  titre: string
  court: string
  but: string
  attente: string // message affiché pendant la génération
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Vue: ComponentType<VueEtapeProps<any>>
  Options?: ComponentType<OptionsEtapeProps>
  optionsInitiales?: (session: Session) => Options
}

export const ETAPES: DefinitionEtape[] = [
  {
    titre: 'Strong context et user context',
    court: 'Contexte',
    but: 'Poser le socle de toute la session : reformulation structurée du projet et géocodage.',
    attente: 'Reformulation du projet et géocodage de la localisation…',
    Vue: Etape0Contexte,
  },
  {
    titre: 'Activation des flux',
    court: 'Flux',
    but: 'Choisir les sources pertinentes selon la localisation et la thématique.',
    attente: "Application de la règle d'activation…",
    Vue: Etape1Flux,
  },
  {
    titre: 'Collecte et analyse',
    court: 'Collecte',
    but: 'Rassembler la matière brute : open data, bench concurrentiel, presse, recherche.',
    attente: 'Interrogation des flux en parallèle puis extraction des signaux candidats…',
    Vue: Etape2Collecte,
  },
  {
    titre: 'Entretiens simulés (panel de 100 personas)',
    court: 'Entretiens',
    but: 'Confronter la thématique à une base de 100 personas ancrée sur la démographie réelle du territoire, dont un panel représentatif est interrogé.',
    attente: 'Guide et base de 100 personas en parallèle, puis entretiens du panel et synthèse…',
    Vue: Etape3Entretiens,
    Options: OptionsEntretiens,
    optionsInitiales: () => ({ questions_ajoutees: [] }),
  },
  {
    titre: 'Qualification STEEPL',
    court: 'STEEPL',
    but: 'Transformer la matière en signaux faibles, tendances lourdes et incertitudes, scorés.',
    attente: 'Qualification et scoring des éléments…',
    Vue: Etape4Steepl,
  },
  {
    titre: 'Cône des futurs',
    court: 'Cône',
    but: "Visualiser l'éventail des futurs d'aujourd'hui à 2040 : probables, plausibles, possibles, souhaitables.",
    attente: 'Positionnement des éléments dans le cône…',
    Vue: Etape5Cone,
  },
  {
    titre: 'Scénarios 2040',
    court: 'Scénarios',
    but: 'Construire 4 futurs contrastés à partir de 2 incertitudes critiques et choisir où aller.',
    attente: 'Construction de la matrice et rédaction des 4 scénarios…',
    Vue: Etape6Scenarios,
    Options: OptionsScenarios,
    optionsInitiales: optionsInitialesScenarios,
  },
  {
    titre: 'Impact business et roadmap',
    court: 'Roadmap',
    but: "Passer du futur visé aux décisions d'aujourd'hui, par backcasting.",
    attente: 'Analyse d’impact, robustesse et roadmap par backcasting…',
    Vue: Etape7Roadmap,
  },
  {
    titre: 'Restitution et design fiction',
    court: 'Restitution',
    but: 'Rendre le futur tangible : récit d’une journée en 2040 et objet venu du futur.',
    attente: 'Écriture du narratif et de l’artefact de design fiction…',
    Vue: Etape8Restitution,
    Options: OptionsRestitution,
    optionsInitiales: (session) => ({
      format_artefact:
        (session.etapes[8].livrable as { artefact?: { format: string } } | null)?.artefact?.format ??
        'une_de_presse',
    }),
  },
]
