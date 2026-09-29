import type { LivrableScenarios, Quadrant } from '../../types'

interface Props {
  livrable: LivrableScenarios
  onOuvrir?: (q: Quadrant) => void
  onChoisir?: (q: Quadrant, role: 'cible' | 'vigilance') => void
  ouvert?: Quadrant | null
}

// Ordre d'affichage : ligne du haut (Y+) puis ligne du bas (Y-), X- à gauche, X+ à droite
const DISPOSITION: Quadrant[] = ['-+', '++', '--', '+-']

const STYLES: Record<Quadrant, { fond: string; bord: string; accent: string; puce: string }> = {
  '++': {
    fond: 'bg-linear-to-br from-emerald-50 via-emerald-50 to-teal-100',
    bord: 'border-emerald-200',
    accent: 'text-emerald-800',
    puce: 'bg-emerald-600',
  },
  '-+': {
    fond: 'bg-linear-to-bl from-sky-50 via-sky-50 to-indigo-100',
    bord: 'border-sky-200',
    accent: 'text-sky-800',
    puce: 'bg-sky-600',
  },
  '+-': {
    fond: 'bg-linear-to-tr from-amber-50 via-amber-50 to-orange-100',
    bord: 'border-amber-200',
    accent: 'text-amber-800',
    puce: 'bg-amber-600',
  },
  '--': {
    fond: 'bg-linear-to-tl from-rose-50 via-rose-50 to-fuchsia-100',
    bord: 'border-rose-200',
    accent: 'text-rose-800',
    puce: 'bg-rose-600',
  },
}

function IconeCible() {
  return (
    <svg viewBox="0 0 16 16" className="size-3.5" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={1.6}>
      <circle cx={8} cy={8} r={6.2} />
      <circle cx={8} cy={8} r={3.4} />
      <circle cx={8} cy={8} r={0.9} fill="currentColor" />
    </svg>
  )
}

function IconeOeil() {
  return (
    <svg viewBox="0 0 16 16" className="size-3.5" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={1.6}>
      <path d="M1.5 8s2.4-4.5 6.5-4.5S14.5 8 14.5 8 12.1 12.5 8 12.5 1.5 8 1.5 8Z" strokeLinejoin="round" />
      <circle cx={8} cy={8} r={2} />
    </svg>
  )
}

const ROTATION = { haut: '-rotate-90', bas: 'rotate-90', droite: '' } as const

function Fleche({ sens }: { sens: keyof typeof ROTATION }) {
  return (
    <svg
      viewBox="0 0 10 10"
      className={`size-2.5 shrink-0 text-slate-400 ${ROTATION[sens]}`}
      aria-hidden="true"
    >
      <path d="M1 1 L9 5 L1 9 Z" fill="currentColor" />
    </svg>
  )
}

export function Matrice2x2({ livrable, onOuvrir, onChoisir, ouvert }: Props) {
  const { axe_x, axe_y, scenarios, choix } = livrable
  const poles = (q: Quadrant) => {
    const x = q[0] === '+' ? axe_x.pole_plus : axe_x.pole_moins
    const y = q[1] === '+' ? axe_y.pole_plus : axe_y.pole_moins
    return `${x} · ${y}`
  }

  return (
    <figure className="w-full" aria-label={`Matrice des scénarios : ${axe_x.intitule} × ${axe_y.intitule}`}>
      <div className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3 sm:grid-cols-[2.25rem_minmax(0,1fr)]">
        {/* Pôle haut de l'axe Y */}
        <div />
        <div className="mb-2 flex justify-center">
          <span className="inline-flex max-w-full items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm">
            <Fleche sens="haut" />
            <span className="line-clamp-2">{axe_y.pole_plus}</span>
          </span>
        </div>

        {/* Axe Y */}
        <div className="flex flex-col items-center py-1" aria-hidden="true">
          <svg viewBox="0 0 10 8" className="size-2.5 text-slate-400">
            <path d="M5 0 L10 8 L0 8 Z" fill="currentColor" />
          </svg>
          <div className="w-px flex-1 bg-slate-300" />
          <span className="rotate-180 py-2 text-[11px] font-semibold tracking-wider text-slate-500 uppercase [writing-mode:vertical-rl]">
            {axe_y.intitule}
          </span>
          <div className="w-px flex-1 bg-slate-300" />
        </div>

        {/* Matrice */}
        <div className="grid grid-cols-2 gap-2.5 sm:gap-4">
          {DISPOSITION.map((q) => {
            const s = scenarios.find((sc) => sc.quadrant === q)
            const style = STYLES[q]
            const estCible = choix.cible === q
            const estVigilance = choix.vigilance === q
            const estOuvert = ouvert === q
            return (
              <article
                key={q}
                onClick={onOuvrir ? () => onOuvrir(q) : undefined}
                className={[
                  'group relative flex min-h-60 flex-col rounded-2xl border p-3 transition sm:p-5',
                  style.fond,
                  style.bord,
                  onOuvrir ? 'cursor-pointer hover:-translate-y-0.5 hover:shadow-lg' : '',
                  estOuvert ? 'shadow-lg ring-2 ring-slate-900/70' : 'shadow-sm',
                  estCible ? 'outline-2 outline-offset-4 outline-slate-900' : '',
                  !estCible && estVigilance ? 'outline-2 outline-offset-4 outline-amber-500 outline-dashed' : '',
                ].join(' ')}
              >
                <header className="mb-2 flex items-start justify-between gap-2">
                  <p className={`flex min-w-0 items-center gap-1.5 text-[11px] font-semibold tracking-wide uppercase ${style.accent}`}>
                    <span className={`inline-block size-2 shrink-0 rounded-full ${style.puce}`} aria-hidden="true" />
                    <span className="line-clamp-2">{poles(q)}</span>
                  </p>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    {estCible && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-slate-900 px-2.5 py-1 text-xs font-semibold text-white shadow-sm">
                        <IconeCible />
                        Scénario visé
                      </span>
                    )}
                    {estVigilance && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900">
                        <IconeOeil />
                        Vigilance
                      </span>
                    )}
                  </div>
                </header>

                {s ? (
                  <>
                    <h3 className="mb-2 font-serif text-xl leading-snug font-semibold text-balance text-slate-900">
                      {onOuvrir ? (
                        <button
                          type="button"
                          aria-expanded={estOuvert}
                          className="text-left underline-offset-4 group-hover:underline focus-visible:underline focus-visible:outline-none"
                        >
                          {s.titre}
                        </button>
                      ) : (
                        s.titre
                      )}
                    </h3>
                    <p className="line-clamp-3 text-sm leading-relaxed text-slate-700">{s.recit}</p>
                  </>
                ) : (
                  <p className="text-sm text-slate-500 italic">Scénario non généré pour ce quadrant.</p>
                )}

                {s && onChoisir && (
                  <div className="mt-auto flex flex-wrap gap-2 pt-4">
                    <button
                      type="button"
                      aria-pressed={estCible}
                      onClick={(ev) => {
                        ev.stopPropagation()
                        onChoisir(q, 'cible')
                      }}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                        estCible
                          ? 'bg-slate-900 text-white'
                          : 'border border-slate-300 bg-white/80 text-slate-800 hover:border-slate-900 hover:bg-white'
                      }`}
                    >
                      <IconeCible />
                      Viser ce futur
                    </button>
                    <button
                      type="button"
                      aria-pressed={estVigilance}
                      onClick={(ev) => {
                        ev.stopPropagation()
                        onChoisir(q, 'vigilance')
                      }}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                        estVigilance
                          ? 'bg-amber-500 text-amber-950'
                          : 'border border-slate-300 bg-white/80 text-slate-800 hover:border-amber-500 hover:bg-white'
                      }`}
                    >
                      <IconeOeil />
                      Garder en vigilance
                    </button>
                  </div>
                )}
              </article>
            )
          })}
        </div>

        {/* Pôle bas de l'axe Y */}
        <div />
        <div className="mt-2 flex justify-center">
          <span className="inline-flex max-w-full items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm">
            <Fleche sens="bas" />
            <span className="sr-only">Bas de l'axe vertical :</span>
            <span className="line-clamp-2">{axe_y.pole_moins}</span>
          </span>
        </div>

        {/* Axe X */}
        <div />
        <div className="mt-4 flex items-center gap-2 text-xs">
          <span className="line-clamp-2 max-w-[40%] shrink-0 rounded-xl border border-slate-200 bg-white px-3 py-1 font-medium text-slate-700 shadow-sm">
            {axe_x.pole_moins}
          </span>
          <div className="relative flex flex-1 items-center" aria-hidden="true">
            <div className="h-px flex-1 bg-slate-300" />
            <Fleche sens="droite" />
          </div>
          <span className="line-clamp-2 max-w-[40%] shrink-0 rounded-xl border border-slate-200 bg-white px-3 py-1 font-medium text-slate-700 shadow-sm">
            {axe_x.pole_plus}
          </span>
        </div>
        <div />
        <p className="mt-1.5 text-center text-[11px] font-semibold tracking-wider text-slate-500 uppercase">
          {axe_x.intitule}
        </p>
      </div>
    </figure>
  )
}
