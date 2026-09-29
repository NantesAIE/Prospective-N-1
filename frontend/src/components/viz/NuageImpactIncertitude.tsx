import type { Categorie, ElementQualifie } from '../../types'
import { LIBELLES_AXES, LIBELLES_CATEGORIES } from '../../types'

interface Props {
  elements: ElementQualifie[]
  selection?: string | null
  onSelect?: (id: string) => void
}

// Palette des catégories, partagée visuellement avec le cône des futurs
const COULEURS: Record<Categorie, { hex: string; pastille: string }> = {
  signal_faible: { hex: '#0369a1', pastille: 'bg-[#0369a1]' },
  tendance_lourde: { hex: '#6d28d9', pastille: 'bg-[#6d28d9]' },
  incertitude: { hex: '#c2410c', pastille: 'bg-[#c2410c]' },
}
const ORDRE_CATEGORIES: Categorie[] = ['signal_faible', 'tendance_lourde', 'incertitude']

// Géométrie du graphique (unités du viewBox)
const W = 640
const H = 470
const M = { gauche: 64, droite: 20, haut: 40, bas: 58 }
const PW = W - M.gauche - M.droite
const PH = H - M.haut - M.bas
const CELLULE = Math.min(PW, PH) / 5
const RAYON = 11
const ESPACEMENT = 24
const TICKS = [1, 2, 3, 4, 5]

const sx = (v: number) => M.gauche + ((v - 0.5) / 5) * PW
const sy = (v: number) => M.haut + PH - ((v - 0.5) / 5) * PH
const borne = (v: number) => Math.min(5, Math.max(1, Number.isFinite(v) ? v : 1))

// Réseau hexagonal trié par distance puis par angle : sert à répartir de façon
// déterministe les points qui partagent la même coordonnée.
const RESEAU = (() => {
  const pts: { x: number; y: number; d: number; a: number }[] = []
  for (let j = -4; j <= 4; j++) {
    for (let i = -4; i <= 4; i++) {
      const x = i + j / 2
      const y = (j * Math.sqrt(3)) / 2
      pts.push({
        x,
        y,
        d: Math.round(Math.hypot(x, y) * 1000),
        a: (Math.atan2(y, x) + 2 * Math.PI) % (2 * Math.PI),
      })
    }
  }
  return pts.sort((p, q) => p.d - q.d || p.a - q.a)
})()

function decalages(n: number): { dx: number; dy: number; r: number }[] {
  if (n <= 1) return [{ dx: 0, dy: 0, r: RAYON }]
  const pts = RESEAU.slice(0, Math.min(n, RESEAU.length))
  const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length
  const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length
  const bruts = pts.map((p) => ({ x: p.x - cx, y: p.y - cy }))
  const etendue = Math.max(...bruts.map((p) => Math.hypot(p.x, p.y))) * ESPACEMENT + RAYON
  const limite = CELLULE / 2 - 2
  const echelle = etendue > limite ? limite / etendue : 1
  const pas = ESPACEMENT * echelle
  const r = Math.min(RAYON, pas * 0.47)
  return bruts.map((p) => ({ dx: p.x * pas, dy: p.y * pas, r }))
}

const comparerIds = (a: string, b: string) =>
  a.localeCompare(b, 'fr', { numeric: true, sensitivity: 'base' })

interface Point {
  el: ElementQualifie
  x: number
  y: number
  r: number
}

export function NuageImpactIncertitude({ elements, selection, onSelect }: Props) {
  if (elements.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">
        Aucun élément qualifié à afficher.
      </div>
    )
  }

  // Regroupement par coordonnée arrondie, puis répartition déterministe
  const groupes = new Map<string, ElementQualifie[]>()
  for (const el of elements) {
    const cle = `${Math.round(borne(el.incertitude))}|${Math.round(borne(el.impact))}`
    const g = groupes.get(cle)
    if (g) g.push(el)
    else groupes.set(cle, [el])
  }
  const points: Point[] = []
  for (const groupe of groupes.values()) {
    groupe.sort((a, b) => comparerIds(a.id, b.id))
    const decs = decalages(groupe.length)
    groupe.forEach((el, i) => {
      const d = decs[i] ?? { dx: 0, dy: 0, r: RAYON }
      points.push({
        el,
        x: sx(borne(el.incertitude)) + d.dx,
        y: sy(borne(el.impact)) + d.dy,
        r: d.r,
      })
    })
  }
  // Le point sélectionné est dessiné en dernier pour rester au premier plan
  points.sort((a, b) => Number(a.el.id === selection) - Number(b.el.id === selection))

  const critiques = elements.filter((e) => e.impact >= 4 && e.incertitude >= 4).length
  const parCategorie = (c: Categorie) => elements.filter((e) => e.categorie === c).length

  const zx = sx(3.5)
  const zy = sy(5.5)
  const zw = sx(5.5) - zx
  const zh = sy(3.5) - zy

  return (
    <figure className="w-full">
      <ul className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-700">
        {ORDRE_CATEGORIES.map((c) => (
          <li key={c} className="flex items-center gap-2">
            <span className={`inline-block size-3 rounded-full ${COULEURS[c].pastille}`} aria-hidden="true" />
            {LIBELLES_CATEGORIES[c]}
            <span className="text-slate-400">({parCategorie(c)})</span>
          </li>
        ))}
        <li className="flex items-center gap-2">
          <span
            className="inline-block h-3 w-4 rounded-sm border border-dashed border-rose-400 bg-rose-50"
            aria-hidden="true"
          />
          Incertitudes critiques
          <span className="text-slate-400">({critiques})</span>
        </li>
      </ul>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full select-none"
        role="img"
        aria-label={`Nuage de points impact et incertitude : ${elements.length} éléments, dont ${critiques} incertitudes critiques (impact et incertitude supérieurs ou égaux à 4).`}
        fontFamily="ui-sans-serif, system-ui, sans-serif"
      >
        {/* Fond du graphique */}
        <rect x={M.gauche} y={M.haut} width={PW} height={PH} fill="#f8fafc" rx={6} />

        {/* Zone critique */}
        <rect
          x={zx}
          y={zy}
          width={zw}
          height={zh}
          fill="#fff1f2"
          stroke="#fb7185"
          strokeWidth={1.5}
          strokeDasharray="6 4"
          rx={6}
        />
        <text x={zx + zw / 2} y={zy - 10} textAnchor="middle" fontSize={12} fontWeight={700} fill="#be123c">
          Incertitudes critiques
        </text>

        {/* Grille et graduations */}
        {TICKS.map((t) => (
          <g key={t}>
            <line x1={sx(t)} x2={sx(t)} y1={M.haut} y2={M.haut + PH} stroke="#e2e8f0" strokeWidth={1} />
            <line x1={M.gauche} x2={M.gauche + PW} y1={sy(t)} y2={sy(t)} stroke="#e2e8f0" strokeWidth={1} />
            <text x={sx(t)} y={M.haut + PH + 20} textAnchor="middle" fontSize={12} fill="#475569">
              {t}
            </text>
            <text x={M.gauche - 12} y={sy(t) + 4} textAnchor="end" fontSize={12} fill="#475569">
              {t}
            </text>
          </g>
        ))}
        <line x1={M.gauche} x2={M.gauche + PW} y1={M.haut + PH} y2={M.haut + PH} stroke="#94a3b8" />
        <line x1={M.gauche} x2={M.gauche} y1={M.haut} y2={M.haut + PH} stroke="#94a3b8" />

        {/* Titres d'axes */}
        <text x={M.gauche + PW / 2} y={H - 12} textAnchor="middle" fontSize={13} fontWeight={600} fill="#334155">
          Incertitude →
        </text>
        <text
          x={18}
          y={M.haut + PH / 2}
          textAnchor="middle"
          fontSize={13}
          fontWeight={600}
          fill="#334155"
          transform={`rotate(-90 18 ${M.haut + PH / 2})`}
        >
          Impact →
        </text>

        {/* Points */}
        {points.map(({ el, x, y, r }) => {
          const actif = el.id === selection
          const couleur = COULEURS[el.categorie]?.hex ?? '#475569'
          const taille = Math.max(6.5, Math.min(r * 0.82, (r * 3.2) / Math.max(el.id.length, 1)))
          return (
            <g
              key={el.id}
              className={onSelect ? 'cursor-pointer' : undefined}
              onClick={onSelect ? () => onSelect(el.id) : undefined}
              onKeyDown={
                onSelect
                  ? (ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        onSelect(el.id)
                      }
                    }
                  : undefined
              }
              tabIndex={onSelect ? 0 : undefined}
              opacity={selection && !actif ? 0.55 : 1}
            >
              <title>
                {`${el.id} · ${el.titre}\n${LIBELLES_CATEGORIES[el.categorie]} · ${LIBELLES_AXES[el.axe]}\nImpact ${el.impact}/5 · Incertitude ${el.incertitude}/5${el.hypothese_ia ? '\nHypothèse IA (non sourcée)' : ''}`}
              </title>
              {actif && <circle cx={x} cy={y} r={r + 6} fill="none" stroke="#0f172a" strokeWidth={2.5} />}
              {el.hypothese_ia && !actif && (
                <circle
                  cx={x}
                  cy={y}
                  r={r + 3}
                  fill="none"
                  stroke={couleur}
                  strokeWidth={1.25}
                  strokeDasharray="2.5 2"
                />
              )}
              <circle cx={x} cy={y} r={actif ? r + 1.5 : r} fill={couleur} stroke="#ffffff" strokeWidth={1.75} />
              <text
                x={x}
                y={y}
                dy="0.35em"
                textAnchor="middle"
                fontSize={taille}
                fontWeight={700}
                fill="#ffffff"
                pointerEvents="none"
              >
                {el.id}
              </text>
            </g>
          )
        })}
      </svg>
      <figcaption className="mt-2 text-xs text-slate-500">
        Survolez un point pour lire l'élément ; cliquez pour le sélectionner. Un contour pointillé signale
        une hypothèse de l'IA non sourcée.
      </figcaption>
    </figure>
  )
}
