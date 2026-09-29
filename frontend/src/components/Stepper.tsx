import { useEffect, useState } from 'react'
import { ETAPES } from '../etapes'
import type { Session } from '../types'

export function Stepper({
  session,
  affichee,
  onChoisir,
}: {
  session: Session
  affichee: number
  onChoisir: (n: number) => void
}) {
  return (
    <ol className="flex w-full items-center gap-1 overflow-x-auto" aria-label="Étapes du parcours">
      {session.etapes.map((e, i) => {
        const accessible = i <= session.etape_courante || e.livrable !== null
        const style =
          e.statut === 'valide'
            ? 'bg-emerald-600 text-white'
            : e.statut === 'brouillon'
              ? 'bg-amber-400 text-white'
              : i === session.etape_courante
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-200 text-slate-500'
        const statut =
          e.statut === 'valide' ? 'validée' : e.statut === 'brouillon' ? 'en cours' : i === session.etape_courante ? 'en cours' : 'à faire'
        return (
          <li key={i} className="flex min-w-0 flex-1 items-center gap-1">
            <button
              type="button"
              disabled={!accessible}
              onClick={() => onChoisir(i)}
              title={`Étape ${i} : ${ETAPES[i].titre} (${statut})`}
              className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors disabled:cursor-not-allowed ${
                affichee === i ? 'bg-indigo-50 ring-1 ring-indigo-300' : 'hover:bg-slate-50'
              }`}
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${style}`}
              >
                {e.statut === 'valide' ? '✓' : i}
              </span>
              <span className="hidden truncate text-xs font-medium text-slate-700 xl:inline">
                {ETAPES[i].court}
              </span>
            </button>
          </li>
        )
      })}
    </ol>
  )
}

function formater(secondes: number) {
  const s = Math.max(0, Math.floor(secondes))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  const deux = (n: number) => String(n).padStart(2, '0')
  return h ? `${h}:${deux(m)}:${deux(r)}` : `${deux(m)}:${deux(r)}`
}

/** Chronomètre de session : temps de travail effectif (inactivité > 10 min non comptée). */
export function Chrono({ session }: { session: Session }) {
  const [maintenant, setMaintenant] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setMaintenant(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])
  const ecart = (maintenant - new Date(session.derniere_activite).getTime()) / 1000
  const total = session.duree_secondes + Math.min(Math.max(ecart, 0), 600)
  const objectif = session.mode === 'demo' ? 5 * 60 : 30 * 60
  const depasse = total > objectif
  return (
    <div
      className="flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-1.5 font-mono text-sm text-white"
      title={`Temps de travail effectif sur la session. Objectif : ${objectif / 60} minutes (promesse : 30 minutes au lieu de 3 à 6 mois).`}
    >
      <span className={`h-2 w-2 rounded-full ${depasse ? 'bg-amber-400' : 'bg-emerald-400'}`} />
      {formater(total)}
      <span className="text-xs text-slate-400">/ {formater(objectif)}</span>
    </div>
  )
}
