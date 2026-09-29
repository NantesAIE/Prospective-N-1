import type { Session } from '../types'

export type Options = Record<string, unknown>

/** Contrat commun des vues d'étape. */
export interface VueEtapeProps<L> {
  session: Session
  livrable: L
  modifiable: boolean
  onChange: (livrable: L) => void
  options: Options
  onOptions: (options: Options) => void
}

/** Réglages proposés avant le lancement ou la relance d'une étape. */
export interface OptionsEtapeProps {
  session: Session
  options: Options
  onOptions: (options: Options) => void
}
