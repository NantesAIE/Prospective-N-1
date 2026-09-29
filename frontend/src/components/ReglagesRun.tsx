import { useEffect, useState } from 'react'
import { api } from '../api'
import type { CatalogueModeles, Mode } from '../types'

/** Libellé court d'un identifiant de modèle de la passerelle. */
function libelleModele(id: string) {
  return id
    .replace(/^(anthropic|openai|amazon|google|mistral)\./, '')
    .replace(/-\d{8}-v\d+:\d+$/, '')
    .replace(/-v\d+:\d+$/, '')
}

/** Interrupteur « Mode démo » et choix du modèle pour tout le parcours. */
export function ReglagesRun({
  mode,
  modele,
  desactive,
  onChange,
}: {
  mode: Mode
  modele: string | null
  desactive?: boolean
  onChange: (reglages: { mode?: Mode; modele?: string | null }) => void
}) {
  const [catalogue, setCatalogue] = useState<CatalogueModeles | null>(null)
  useEffect(() => {
    api.modeles().then(setCatalogue).catch(() => setCatalogue(null))
  }, [])
  const demo = mode === 'demo'

  return (
    <div className="flex items-center gap-3">
      <label
        className="flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-700"
        title="Mode démo : parcours complet en 5 minutes, avec des livrables plus courts"
      >
        <button
          type="button"
          role="switch"
          aria-checked={demo}
          disabled={desactive}
          onClick={() => onChange({ mode: demo ? 'complet' : 'demo' })}
          className={`relative h-5 w-9 shrink-0 rounded-full transition-colors disabled:opacity-50 ${
            demo ? 'bg-amber-500' : 'bg-slate-300'
          }`}
        >
          <span
            className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
              demo ? 'translate-x-4' : ''
            }`}
          />
        </button>
        Mode démo
        <span className="hidden text-slate-400 2xl:inline">{demo ? '(5 min)' : '(complet)'}</span>
      </label>
      <select
        className="max-w-44 rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 disabled:opacity-50"
        value={modele ?? ''}
        disabled={desactive || !catalogue}
        onChange={(e) => onChange({ modele: e.target.value || null })}
        aria-label="Modèle utilisé pour le parcours"
        title="Modèle utilisé pour toutes les étapes et l'assistant"
      >
        <option value="">
          Modèle par défaut{catalogue ? ` (${libelleModele(demo ? catalogue.rapide : catalogue.defaut)})` : ''}
        </option>
        {catalogue?.modeles.map((m) => (
          <option key={m} value={m}>
            {libelleModele(m)}
          </option>
        ))}
      </select>
    </div>
  )
}
