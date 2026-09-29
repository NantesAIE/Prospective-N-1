import type { HorizonJalon, LivrableRoadmap } from '../../types'

interface Props {
  jalons: LivrableRoadmap['jalons']
}

type Jalon = LivrableRoadmap['jalons'][number]

// Affichage de gauche à droite : aujourd'hui, puis 90 jours ... jusqu'à 2040.
// La lecture (backcasting) se fait de droite à gauche.
const ORDRE_AFFICHAGE: HorizonJalon[] = ['90 jours', '18 mois', '2030', '2035', '2040']

const SOUS_TITRES: Record<HorizonJalon, string> = {
  '2040': 'Futur visé',
  '2035': 'Étape de maturité',
  '2030': 'Point de bascule',
  '18 mois': 'Premières preuves',
  '90 jours': 'Actions immédiates',
}

const nettoyer = (t: string) => t.replace(/^\s*[-•*]\s*/, '').trim()

function Carte({ jalon }: { jalon: Jalon }) {
  const immediat = jalon.horizon === '90 jours'
  const futur = jalon.horizon === '2040'
  return (
    <article
      className={[
        'flex h-full flex-col rounded-2xl border p-4',
        immediat
          ? 'border-indigo-600 bg-indigo-600 text-white shadow-lg shadow-indigo-600/25'
          : futur
            ? 'border-slate-900 bg-slate-900 text-white shadow-md'
            : 'border-slate-200 bg-white text-slate-800 shadow-sm',
      ].join(' ')}
    >
      {immediat && (
        <span className="mb-2 inline-flex w-fit items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[11px] font-bold tracking-wide text-indigo-700 uppercase">
          <svg viewBox="0 0 12 12" className="size-3" aria-hidden="true">
            <path d="M7 0 L2 7 H6 L5 12 L10 5 H6 Z" fill="currentColor" />
          </svg>
          À lancer maintenant
        </span>
      )}
      <p
        className={`mb-3 text-sm leading-snug font-semibold ${
          immediat || futur ? 'text-white' : 'text-slate-900'
        }`}
      >
        {jalon.objectif}
      </p>
      {jalon.actions.length > 0 && (
        <ul className="mt-auto space-y-1.5">
          {jalon.actions.map((a, i) => (
            <li
              key={i}
              className={`flex gap-2 text-[13px] leading-snug ${
                immediat ? 'text-indigo-50' : futur ? 'text-slate-200' : 'text-slate-600'
              }`}
            >
              <span
                className={`mt-1.5 inline-block size-1.5 shrink-0 rounded-full ${
                  immediat ? 'bg-white' : futur ? 'bg-slate-400' : 'bg-indigo-500'
                }`}
                aria-hidden="true"
              />
              <span>{nettoyer(a)}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}

export function RoadmapBackcasting({ jalons }: Props) {
  const ordonnes = ORDRE_AFFICHAGE.flatMap((h) => jalons.filter((j) => j.horizon === h))

  if (ordonnes.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">
        Aucun jalon de roadmap à afficher.
      </div>
    )
  }

  return (
    <figure className="w-full" aria-label="Roadmap par backcasting, de 2040 vers aujourd'hui">
      <div className="snap-x overflow-x-auto pb-3 [scrollbar-width:thin]">
        <div className="min-w-max px-1">
          {/* Sens de lecture : du futur vers aujourd'hui */}
          <div className="mb-4 flex items-center gap-2 pr-4 pl-2" aria-hidden="true">
            <svg viewBox="0 0 14 14" className="size-3.5 shrink-0 text-indigo-600">
              <path d="M13 1 L1 7 L13 13 Z" fill="currentColor" />
            </svg>
            <div className="h-0.5 flex-1 bg-linear-to-r from-indigo-600 to-slate-300" />
            <span className="shrink-0 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-800">
              Backcasting : du futur visé vers aujourd'hui
            </span>
            <div className="h-0.5 flex-1 bg-linear-to-r from-slate-300 to-slate-900" />
            <span className="shrink-0 text-xs font-bold text-slate-900">2040</span>
          </div>

          <div className="relative">
            {/* Ligne de temps */}
            <div className="pointer-events-none absolute top-[15px] right-0 left-0 h-0.5 bg-slate-200" aria-hidden="true" />
            <ol className="relative flex items-stretch gap-4">
  
              <li className="flex w-32 shrink-0 snap-start flex-col items-center">
                <span className="relative z-10 flex h-8 items-center">
                  <span className="size-4 rounded-full border-4 border-white bg-slate-900 ring-2 ring-slate-900" />
                </span>
                <div className="mt-3 flex h-full w-full flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-3 text-center">
                  <p className="text-sm font-bold text-slate-900">Aujourd'hui</p>
                  <p className="mt-1 text-xs text-slate-500">Point d'arrivée du backcasting, point de départ de l'action</p>
                </div>
              </li>
  
              {ordonnes.map((j, i) => {
                const immediat = j.horizon === '90 jours'
                return (
                  <li
                    key={`${j.horizon}-${i}`}
                    className={`flex shrink-0 snap-start flex-col ${immediat ? 'w-72' : 'w-64'}`}
                  >
                    <div className="relative z-10 flex h-8 items-center gap-2">
                      <span
                        className={`rounded-full px-3 py-1 text-sm font-bold ${
                          immediat
                            ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                            : j.horizon === '2040'
                              ? 'bg-slate-900 text-white'
                              : 'border border-slate-300 bg-white text-slate-800'
                        }`}
                      >
                        {j.horizon}
                      </span>
                      <span
                        className={`bg-white pr-1 text-xs font-medium ${immediat ? 'text-indigo-700' : 'text-slate-500'}`}
                      >
                        {SOUS_TITRES[j.horizon]}
                      </span>
                    </div>
                    <div className="mt-3 flex-1">
                      <Carte jalon={j} />
                    </div>
                  </li>
                )
              })}
            </ol>
          </div>
        </div>
      </div>
    </figure>
  )
}
