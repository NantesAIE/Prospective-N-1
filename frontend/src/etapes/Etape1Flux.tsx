import { BadgeAxe, Carte, PastilleNiveau } from '../components/ui'
import { LIBELLES_NIVEAUX, type LivrableFlux, type Niveau } from '../types'
import type { VueEtapeProps } from './commun'

const NIVEAUX: Niveau[] = ['monde', 'zone', 'pays', 'local']

export function Etape1Flux({ livrable, modifiable, onChange }: VueEtapeProps<LivrableFlux>) {
  const basculer = (id: string) =>
    onChange({ flux: livrable.flux.map((f) => (f.id === id ? { ...f, actif: !f.actif } : f)) })
  const nbActifs = livrable.flux.filter((f) => f.actif).length

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        <strong>{nbActifs}</strong> flux activés sur {livrable.flux.length}, selon la règle
        d'activation par niveau (Monde toujours, UE si le pays en fait partie, Pays si un connecteur
        national existe, Local si une localisation fine est fournie).
        {modifiable && ' Cochez ou décochez les flux à interroger.'}
      </p>
      {NIVEAUX.map((niveau) => {
        const flux = livrable.flux.filter((f) => f.niveau === niveau)
        if (!flux.length) return null
        return (
          <Carte key={niveau}>
            <div className="mb-3 flex items-center gap-2">
              <PastilleNiveau niveau={niveau} />
              <span className="text-sm font-semibold text-slate-700">
                Niveau {LIBELLES_NIVEAUX[niveau]}
              </span>
            </div>
            <ul className="divide-y divide-slate-100">
              {flux.map((f) => (
                <li key={f.id} className="flex items-start gap-3 py-2">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 accent-indigo-600"
                    checked={f.actif}
                    disabled={!modifiable}
                    onChange={() => basculer(f.id)}
                    aria-label={`Activer ${f.nom}`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`font-medium ${f.actif ? 'text-slate-900' : 'text-slate-400'}`}>
                        {f.nom}
                      </span>
                      {f.axes.map((a) => (
                        <BadgeAxe key={a} axe={a} />
                      ))}
                      {f.cle_requise && (
                        <span className="rounded bg-slate-100 px-1.5 text-xs text-slate-600">clé requise</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600">{f.description}</p>
                    <p className="text-xs text-slate-400">{f.raison}</p>
                  </div>
                </li>
              ))}
            </ul>
          </Carte>
        )
      })}
    </div>
  )
}
