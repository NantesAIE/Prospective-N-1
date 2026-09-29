import { RoadmapBackcasting } from '../components/viz/RoadmapBackcasting'
import { Carte, ListeEditable, Puces, Titre } from '../components/ui'
import type { LivrableRoadmap } from '../types'
import type { VueEtapeProps } from './commun'

export function Etape7Roadmap({ livrable, modifiable, onChange }: VueEtapeProps<LivrableRoadmap>) {
  const { impact } = livrable
  const majJalon = (i: number, partiel: Partial<LivrableRoadmap['jalons'][number]>) =>
    onChange({ ...livrable, jalons: livrable.jalons.map((j, k) => (k === i ? { ...j, ...partiel } : j)) })

  return (
    <div className="space-y-4">
      <Carte>
        <Titre>Impact business dans le scénario visé</Titre>
        <div className="grid gap-4 md:grid-cols-3">
          {(
            [
              ['Offre', impact.offre],
              ['Clients', impact.clients],
              ['Modèle économique', impact.modele_economique],
            ] as const
          ).map(([titre, texte]) => (
            <div key={titre}>
              <p className="text-xs font-semibold text-slate-500">{titre}</p>
              <p className="text-sm text-slate-800">{texte}</p>
            </div>
          ))}
          <div>
            <p className="mb-1 text-xs font-semibold text-rose-600">Risques</p>
            <Puces elements={impact.risques} />
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold text-emerald-600">Opportunités</p>
            <Puces elements={impact.opportunites} />
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold text-slate-500">Robustesse dans les autres scénarios</p>
            <ul className="space-y-2">
              {livrable.robustesse.map((r) => (
                <li key={r.quadrant} className="text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium text-slate-700">
                      {r.quadrant} {r.titre_scenario}
                    </span>
                    <span className="flex gap-0.5" aria-label={`${r.score} sur 5`}>
                      {[1, 2, 3, 4, 5].map((n) => (
                        <span key={n} className={`h-2.5 w-4 rounded-sm ${n <= r.score ? 'bg-indigo-500' : 'bg-slate-200'}`} />
                      ))}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">{r.commentaire}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Carte>

      <Carte>
        <Titre>Roadmap par backcasting</Titre>
        <RoadmapBackcasting jalons={livrable.jalons} />
        {modifiable && (
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {livrable.jalons.map((j, i) => (
              <div key={j.horizon} className="rounded-lg border border-dashed border-slate-300 p-2">
                <p className="text-xs font-semibold text-slate-500">Ajuster « {j.horizon} »</p>
                <input
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  value={j.objectif}
                  onChange={(e) => majJalon(i, { objectif: e.target.value })}
                />
                <div className="mt-1">
                  <ListeEditable valeurs={j.actions} onChange={(actions) => majJalon(i, { actions })} lignes={3} />
                </div>
              </div>
            ))}
          </div>
        )}
      </Carte>

      <div className="grid gap-4 lg:grid-cols-2">
        <Carte>
          <Titre>Signaux à surveiller</Titre>
          <ul className="space-y-2">
            {livrable.signaux_a_surveiller.map((s, i) => (
              <li key={i} className="text-sm">
                <p className="font-medium text-slate-800">{s.indicateur}</p>
                <p className="text-slate-600">Alerte : {s.ce_qui_alerte}</p>
                <p className="text-xs text-slate-500">
                  Suivi : {s.source_suivi}
                  {s.flux_id && <span className="ml-1 rounded bg-slate-100 px-1">flux {s.flux_id}</span>}
                  {s.hypothese_ia && (
                    <span className="ml-1 rounded bg-orange-100 px-1 text-orange-800">hypothèse IA</span>
                  )}
                </p>
              </li>
            ))}
          </ul>
        </Carte>
        <Carte>
          <Titre>Paris sans regret</Titre>
          <ul className="space-y-2">
            {livrable.paris_sans_regret.map((p, i) => (
              <li key={i} className="text-sm">
                <p className="font-medium text-slate-800">✓ {p.action}</p>
                <p className="text-slate-600">{p.justification}</p>
              </li>
            ))}
          </ul>
        </Carte>
      </div>
    </div>
  )
}
