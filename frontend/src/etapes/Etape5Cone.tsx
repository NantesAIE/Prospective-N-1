import { useState } from 'react'
import { ConeDesFuturs } from '../components/viz/ConeDesFuturs'
import { BadgeAxe, Carte, Titre } from '../components/ui'
import { LIBELLES_ZONES, type LivrableCone, type Position, type Zone } from '../types'
import type { VueEtapeProps } from './commun'

const ZONES = Object.keys(LIBELLES_ZONES) as Zone[]
const JALONS = [2030, 2035, 2040]
const selecteur = 'rounded border border-slate-300 bg-white px-1 py-0.5 text-xs'

export function Etape5Cone({ session, livrable, modifiable, onChange }: VueEtapeProps<LivrableCone>) {
  const [selection, setSelection] = useState<string | null>(null)
  const maj = (id: string, partiel: Partial<Position>) =>
    onChange({
      ...livrable,
      positions: livrable.positions.map((p) => (p.element_id === id ? { ...p, ...partiel } : p)),
    })

  return (
    <div className="space-y-4">
      <Carte>
        <ConeDesFuturs
          positions={livrable.positions}
          zones={livrable.zones}
          anneeDebut={Number(session.cree_le.slice(0, 4))}
          selection={selection}
          onSelect={setSelection}
        />
      </Carte>
      <div className="grid gap-4 lg:grid-cols-2">
        {ZONES.map((zone) => {
          const positions = livrable.positions.filter((p) => p.zone === zone)
          return (
            <Carte key={zone}>
              <Titre>
                Futurs {LIBELLES_ZONES[zone].toLowerCase()}s ({positions.length})
              </Titre>
              <p className="mb-2 text-sm text-slate-600">
                {livrable.zones.find((z) => z.zone === zone)?.description}
              </p>
              <ul className="space-y-1.5">
                {positions
                  .sort((a, b) => a.jalon - b.jalon)
                  .map((p) => (
                    <li
                      key={p.element_id}
                      onClick={() => setSelection(p.element_id)}
                      className={`cursor-pointer rounded-lg p-2 text-sm ${selection === p.element_id ? 'bg-indigo-50' : 'hover:bg-slate-50'}`}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs text-slate-400">{p.element_id}</span>
                        <BadgeAxe axe={p.axe} />
                        <span className="font-medium text-slate-800">{p.titre}</span>
                        {modifiable ? (
                          <span className="ml-auto flex gap-1">
                            <select
                              className={selecteur}
                              value={p.zone}
                              onChange={(e) => maj(p.element_id, { zone: e.target.value as Zone })}
                              aria-label="Zone"
                            >
                              {ZONES.map((z) => (
                                <option key={z} value={z}>
                                  {LIBELLES_ZONES[z]}
                                </option>
                              ))}
                            </select>
                            <select
                              className={selecteur}
                              value={p.jalon}
                              onChange={(e) => maj(p.element_id, { jalon: Number(e.target.value) })}
                              aria-label="Jalon"
                            >
                              {JALONS.map((j) => (
                                <option key={j}>{j}</option>
                              ))}
                            </select>
                          </span>
                        ) : (
                          <span className="ml-auto text-xs text-slate-500">{p.jalon}</span>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500">{p.commentaire}</p>
                    </li>
                  ))}
              </ul>
            </Carte>
          )
        })}
      </div>
    </div>
  )
}
