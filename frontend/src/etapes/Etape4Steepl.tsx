import { useState } from 'react'
import { NuageImpactIncertitude } from '../components/viz/NuageImpactIncertitude'
import { BadgeAxe, Carte, LienSource, Titre } from '../components/ui'
import {
  LIBELLES_AXES,
  LIBELLES_CATEGORIES,
  type Axe,
  type Categorie,
  type ElementQualifie,
  type LivrableSteepl,
} from '../types'
import type { VueEtapeProps } from './commun'

const AXES = Object.keys(LIBELLES_AXES) as Axe[]
const CATEGORIES = Object.keys(LIBELLES_CATEGORIES) as Categorie[]
const selecteur = 'rounded border border-slate-300 bg-white px-1 py-0.5 text-xs'

export function Etape4Steepl({ livrable, modifiable, onChange }: VueEtapeProps<LivrableSteepl>) {
  const [selection, setSelection] = useState<string | null>(null)
  const [filtre, setFiltre] = useState<Categorie | null>(null)

  const maj = (id: string, partiel: Partial<ElementQualifie>) =>
    onChange({ elements: livrable.elements.map((e) => (e.id === id ? { ...e, ...partiel } : e)) })
  const visibles = livrable.elements.filter((e) => !filtre || e.categorie === filtre)
  const choisi = livrable.elements.find((e) => e.id === selection)

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-5">
        <Carte className="lg:col-span-3">
          <Titre>Nuage impact / incertitude</Titre>
          <NuageImpactIncertitude elements={livrable.elements} selection={selection} onSelect={setSelection} />
        </Carte>
        <Carte className="lg:col-span-2">
          <Titre>Élément sélectionné</Titre>
          {choisi ? (
            <div className="space-y-2 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-slate-400">{choisi.id}</span>
                <BadgeAxe axe={choisi.axe} />
                <span className="rounded bg-slate-100 px-1.5 text-xs">{LIBELLES_CATEGORIES[choisi.categorie]}</span>
              </div>
              <p className="font-medium text-slate-900">{choisi.titre}</p>
              <p className="text-slate-700">{choisi.description}</p>
              <p className="text-slate-500">
                Impact {choisi.impact}/5, incertitude {choisi.incertitude}/5 : {choisi.justification}
              </p>
              <LienSource
                source={choisi.source}
                url={choisi.url}
                date={choisi.date}
                hypotheseIa={choisi.hypothese_ia}
              />
            </div>
          ) : (
            <p className="text-sm text-slate-500">Cliquez sur un point du nuage ou une ligne du tableau.</p>
          )}
        </Carte>
      </div>

      <Carte className="overflow-x-auto p-0">
        <div className="flex flex-wrap gap-1 border-b border-slate-100 p-2">
          {[null, ...CATEGORIES].map((c) => (
            <button
              key={c ?? 'tous'}
              type="button"
              onClick={() => setFiltre(c)}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                filtre === c ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'
              }`}
            >
              {c ? LIBELLES_CATEGORIES[c] : 'Tous'} (
              {livrable.elements.filter((e) => !c || e.categorie === c).length})
            </button>
          ))}
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500">
            <tr>
              {['Id', 'Élément', 'Axe', 'Catégorie', 'Impact', 'Incert.', 'Source'].map((h) => (
                <th key={h} className="px-3 py-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibles.map((e) => (
              <tr
                key={e.id}
                onClick={() => setSelection(e.id)}
                className={`cursor-pointer border-t border-slate-100 ${selection === e.id ? 'bg-indigo-50' : 'hover:bg-slate-50'}`}
              >
                <td className="px-3 py-1.5 font-mono text-xs text-slate-400">{e.id}</td>
                <td className="px-3 py-1.5">
                  <p className="font-medium text-slate-800">{e.titre}</p>
                </td>
                <td className="px-3 py-1.5">
                  {modifiable ? (
                    <select className={selecteur} value={e.axe} onChange={(ev) => maj(e.id, { axe: ev.target.value as Axe })}>
                      {AXES.map((a) => (
                        <option key={a} value={a}>
                          {LIBELLES_AXES[a]}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <BadgeAxe axe={e.axe} />
                  )}
                </td>
                <td className="px-3 py-1.5">
                  {modifiable ? (
                    <select
                      className={selecteur}
                      value={e.categorie}
                      onChange={(ev) => maj(e.id, { categorie: ev.target.value as Categorie })}
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>
                          {LIBELLES_CATEGORIES[c]}
                        </option>
                      ))}
                    </select>
                  ) : (
                    LIBELLES_CATEGORIES[e.categorie]
                  )}
                </td>
                {(['impact', 'incertitude'] as const).map((cle) => (
                  <td key={cle} className="px-3 py-1.5">
                    {modifiable ? (
                      <select
                        className={selecteur}
                        value={e[cle]}
                        onChange={(ev) => maj(e.id, { [cle]: Number(ev.target.value) })}
                      >
                        {[1, 2, 3, 4, 5].map((n) => (
                          <option key={n}>{n}</option>
                        ))}
                      </select>
                    ) : (
                      e[cle]
                    )}
                  </td>
                ))}
                <td className="px-3 py-1.5">
                  <LienSource source={e.source} url={e.url} hypotheseIa={e.hypothese_ia} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Carte>
    </div>
  )
}
