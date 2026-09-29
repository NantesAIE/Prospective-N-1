import type { LivrableContexte, Session } from '../types'
import { Bouton, Titre } from './ui'

/** Rappel permanent du strong context, repliable. */
export function PanneauContexte({
  session,
  ouvert,
  onBasculer,
  onArchives,
}: {
  session: Session
  ouvert: boolean
  onBasculer: () => void
  onArchives: () => void
}) {
  if (!ouvert) {
    return (
      <button
        type="button"
        onClick={onBasculer}
        className="flex w-8 shrink-0 items-start justify-center border-r border-slate-200 bg-white pt-4 text-xs font-medium text-slate-500 hover:bg-slate-50"
        title="Afficher le strong context"
      >
        <span className="[writing-mode:vertical-rl]">Strong context ▸</span>
      </button>
    )
  }
  const s = session.saisie
  const e0 = session.etapes[0]
  const contexte = e0.statut === 'valide' ? (e0.livrable as unknown as LivrableContexte) : null
  return (
    <aside className="w-72 shrink-0 overflow-y-auto border-r border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <Titre>Strong context</Titre>
        <Bouton variante="discret" className="!px-2 !py-0.5" onClick={onBasculer} aria-label="Replier">
          ◂
        </Bouton>
      </div>
      <p className="text-sm whitespace-pre-line text-slate-800">{s.description}</p>
      <dl className="mt-3 space-y-1 text-xs">
        {[
          ['Thématique', s.thematique],
          ['Localisation', [s.lieu, s.pays].filter(Boolean).join(', ')],
          ['Horizon', String(s.horizon)],
          ['Ambition', s.ambition],
        ]
          .filter(([, v]) => v)
          .map(([k, v]) => (
            <div key={k}>
              <dt className="font-semibold text-slate-500">{k}</dt>
              <dd className="text-slate-700">{v}</dd>
            </div>
          ))}
      </dl>
      {contexte && (
        <div className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-xs">
          <p className="font-semibold text-slate-500">Fiche validée</p>
          <p>
            <span className="font-medium">Cible :</span> {contexte.fiche.cible}
          </p>
          <p>
            <span className="font-medium">Proposition de valeur :</span> {contexte.fiche.proposition_valeur}
          </p>
          <p>
            <span className="font-medium">Territoire :</span> {contexte.fiche.territoire}
          </p>
        </div>
      )}
      <Bouton className="mt-4 w-full" onClick={onArchives}>
        Dossier archivé (.md)
      </Bouton>
    </aside>
  )
}
