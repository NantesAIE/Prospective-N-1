import { useEffect, useId, useRef, useState } from 'react'
import type { Categorie, Position, Zone } from '../../types'
import { LIBELLES_AXES, LIBELLES_CATEGORIES, LIBELLES_ZONES } from '../../types'

interface Props {
  positions: Position[]
  zones: { zone: Zone; description: string }[]
  anneeDebut: number
  selection?: string | null
  onSelect?: (id: string) => void
}

// Palette des catégories, identique au nuage impact / incertitude
const COULEURS_CATEGORIES: Record<Categorie, { hex: string; pastille: string }> = {
  signal_faible: { hex: '#0369a1', pastille: 'bg-[#0369a1]' },
  tendance_lourde: { hex: '#6d28d9', pastille: 'bg-[#6d28d9]' },
  incertitude: { hex: '#c2410c', pastille: 'bg-[#c2410c]' },
}
const ORDRE_CATEGORIES: Categorie[] = ['signal_faible', 'tendance_lourde', 'incertitude']

// Teintes des cônes : clair en haut, plus sombre en bas, pour suggérer le volume
const STYLE_ZONES: Record<Zone, { clair: string; sombre: string; trait: string; pastille: string; carte: string }> = {
  possible: {
    clair: '#f8fafc',
    sombre: '#cbd5e1',
    trait: '#94a3b8',
    pastille: 'bg-[#e2e8f0] border-[#94a3b8]',
    carte: 'border-slate-200 bg-white',
  },
  plausible: {
    clair: '#e2e8f0',
    sombre: '#94a3b8',
    trait: '#64748b',
    pastille: 'bg-[#cbd5e1] border-[#64748b]',
    carte: 'border-slate-300 bg-white',
  },
  probable: {
    clair: '#cbd5e1',
    sombre: '#64748b',
    trait: '#475569',
    pastille: 'bg-[#94a3b8] border-[#475569]',
    carte: 'border-slate-400 bg-white',
  },
  souhaitable: {
    clair: '#a7f3d0',
    sombre: '#10b981',
    trait: '#047857',
    pastille: 'bg-emerald-100 border-dashed border-emerald-700',
    carte: 'border-emerald-300 bg-emerald-50/60',
  },
}
const ORDRE_ZONES: Zone[] = ['probable', 'plausible', 'possible', 'souhaitable']

// Géométrie (unités du viewBox). Le cône est couché : son axe suit le temps.
const W = 940
const H = 560
const YC = 250 // axe du cône
const X0 = 70 // sommet : aujourd'hui
const X_HORIZON = 720 // abscisse de 2040
const X_FIN = 790 // ouverture du cône, vue en perspective
const R = 205 // rayon de la zone « possible » en 2040
const K = 0.3 // aplatissement des sections : rapport largeur / hauteur des ellipses
const EXPOSANT = 0.72 // évasement légèrement concave, comme un faisceau lumineux
const RATIOS = { probable: 0.3, plausible: 0.62, possible: 1 }
// Cône souhaitable : incliné vers le haut, il chevauche plausible et possible
const SOUHAITABLE = { centre: 0.66, rayon: 0.2 }
const JALONS = [2030, 2035, 2040]
const RAYON_POINT = 10
const PAS_X = 24
const PAS_Y = 23
const LARGEUR_GROUPE_MAX = 150

const ouverture = (x: number) => Math.pow(Math.max(0, (x - X0) / (X_HORIZON - X0)), EXPOSANT)
const rayon = (x: number) => ouverture(x) * R

// Centre vertical et demi-hauteur de la section d'un cône à l'abscisse x
function section(zone: Zone, x: number): { cy: number; ry: number } {
  const r = rayon(x)
  if (zone === 'souhaitable') return { cy: YC - SOUHAITABLE.centre * r, ry: SOUHAITABLE.rayon * r }
  return { cy: YC, ry: RATIOS[zone] * r }
}

// Bande verticale où placer les éléments d'une zone (projection de sa partie visible)
function bande(zone: Zone, x: number): [number, number] {
  const r = rayon(x)
  switch (zone) {
    case 'probable':
      return [YC - RATIOS.probable * r, YC + RATIOS.probable * r]
    case 'plausible':
      return [YC + RATIOS.probable * r, YC + RATIOS.plausible * r]
    case 'possible':
      return [YC + RATIOS.plausible * r, YC + RATIOS.possible * r]
    case 'souhaitable': {
      const { cy, ry } = section('souhaitable', x)
      return [cy - ry, cy + ry]
    }
  }
}

// Silhouette d'un cône : génératrices haute et basse, fermées par la moitié avant de l'ouverture
function silhouette(zone: Zone): string {
  const n = 50
  const xs = Array.from({ length: n + 1 }, (_, i) => X0 + ((X_FIN - X0) * i) / n)
  const haut = xs.map((x) => {
    const { cy, ry } = section(zone, x)
    return `${x.toFixed(1)},${(cy - ry).toFixed(1)}`
  })
  const bas = xs
    .map((x) => {
      const { cy, ry } = section(zone, x)
      return `${x.toFixed(1)},${(cy + ry).toFixed(1)}`
    })
    .reverse()
  const { ry } = section(zone, X_FIN)
  const rx = K * ry
  // Arc avant de l'ouverture (côté spectateur), du haut vers le bas
  const [xh] = haut[haut.length - 1].split(',')
  const [, yb] = bas[0].split(',')
  return `M${haut.join(' L')} A${rx.toFixed(1)},${ry.toFixed(1)} 0 0 1 ${xh},${yb} L${bas.join(' L')} Z`
}

const CHEMINS: Record<Zone, string> = {
  possible: silhouette('possible'),
  plausible: silhouette('plausible'),
  probable: silhouette('probable'),
  souhaitable: silhouette('souhaitable'),
}

// Demi-ellipse d'une section : moitié arrière (cachée) ou avant (visible)
function demiEllipse(x: number, cy: number, ry: number, cote: 'arriere' | 'avant'): string {
  const rx = K * ry
  const balayage = cote === 'avant' ? 1 : 0
  return `M${x},${cy - ry} A${rx},${ry} 0 0 ${balayage} ${x},${cy + ry}`
}

const comparerIds = (a: string, b: string) => a.localeCompare(b, 'fr', { numeric: true, sensitivity: 'base' })

interface Point {
  pos: Position
  x: number
  y: number
}

/** Petite fenêtre de détail d'un élément, positionnée au-dessus du point cliqué. */
function Popup({ point, onFermer }: { point: Point; onFermer: () => void }) {
  const { pos } = point
  const couleur = COULEURS_CATEGORIES[pos.categorie]?.hex ?? '#475569'
  const aDroite = point.x / W > 0.6
  const enBas = point.y / H < 0.35
  return (
    <div
      role="dialog"
      aria-label={`Détail de ${pos.element_id}`}
      onClick={(e) => e.stopPropagation()}
      className="absolute z-10 w-72 rounded-xl border border-slate-200 bg-white p-3 text-left shadow-xl"
      style={{
        left: `${(point.x / W) * 100}%`,
        top: `${(point.y / H) * 100}%`,
        transform: `translate(${aDroite ? 'calc(-100% - 14px)' : '14px'}, ${enBas ? '8px' : 'calc(-100% - 8px)'})`,
      }}
    >
      <div className="flex items-start gap-2">
        <span
          className="mt-0.5 rounded-full px-2 py-0.5 font-mono text-xs font-bold text-white"
          style={{ backgroundColor: couleur }}
        >
          {pos.element_id}
        </span>
        <p className="flex-1 text-sm leading-snug font-semibold text-slate-900">{pos.titre}</p>
        <button
          type="button"
          onClick={onFermer}
          className="-mt-1 -mr-1 rounded px-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          aria-label="Fermer"
        >
          ×
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
        <span className={`rounded-full border px-2 py-0.5 ${STYLE_ZONES[pos.zone].carte}`}>
          {LIBELLES_ZONES[pos.zone]}
        </span>
        <span className="rounded-full bg-slate-900 px-2 py-0.5 font-semibold text-white">{pos.jalon}</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-700">
          {LIBELLES_CATEGORIES[pos.categorie] ?? pos.categorie}
        </span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-700">{LIBELLES_AXES[pos.axe] ?? pos.axe}</span>
      </div>
      {pos.commentaire && <p className="mt-2 text-xs leading-relaxed text-slate-600">{pos.commentaire}</p>}
    </div>
  )
}

export function ConeDesFuturs({ positions, zones, anneeDebut, selection, onSelect }: Props) {
  const [zoneActive, setZoneActive] = useState<Zone | null>(null)
  const [ouvert, setOuvert] = useState<string | null>(null)
  const conteneur = useRef<HTMLDivElement>(null)
  const idBrut = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const idDegrade = (z: Zone) => `cone-${idBrut}-${z}`
  const idFondu = `cone-${idBrut}-fondu`

  // Fermeture de la popup : Échap ou clic hors du cône
  useEffect(() => {
    if (!ouvert) return
    const clavier = (e: KeyboardEvent) => e.key === 'Escape' && setOuvert(null)
    const clic = (e: MouseEvent) => {
      if (conteneur.current && !conteneur.current.contains(e.target as Node)) setOuvert(null)
    }
    document.addEventListener('keydown', clavier)
    document.addEventListener('mousedown', clic)
    return () => {
      document.removeEventListener('keydown', clavier)
      document.removeEventListener('mousedown', clic)
    }
  }, [ouvert])

  const debut = Math.min(anneeDebut, 2039)
  const xAnnee = (annee: number) => {
    const x = X0 + ((annee - debut) / (2040 - debut)) * (X_HORIZON - X0)
    return Math.max(X0 + 40, x)
  }

  // Répartition déterministe : grille centrée sur (jalon, centre de la bande)
  const groupes = new Map<string, Position[]>()
  for (const pos of positions) {
    const cle = `${pos.zone}|${pos.jalon}`
    const g = groupes.get(cle)
    if (g) g.push(pos)
    else groupes.set(cle, [pos])
  }
  const points: Point[] = []
  for (const groupe of groupes.values()) {
    groupe.sort((a, b) => comparerIds(a.element_id, b.element_id))
    const { zone, jalon } = groupe[0]
    const xj = xAnnee(jalon)
    const [y1, y2] = bande(zone, xj)
    const yc = (y1 + y2) / 2
    const n = groupe.length
    const colsMax = Math.max(1, Math.floor(LARGEUR_GROUPE_MAX / PAS_X))
    let lignes = Math.max(1, Math.floor((y2 - y1 + 4) / PAS_Y))
    if (Math.ceil(n / lignes) > colsMax) lignes = Math.ceil(n / colsMax)
    lignes = Math.min(lignes, n)
    const cols = Math.ceil(n / lignes)
    groupe.forEach((pos, k) => {
      const col = Math.floor(k / lignes)
      const ligne = k % lignes
      const dansCol = Math.min(lignes, n - col * lignes)
      const quinconce = lignes > 1 && dansCol === lignes && col % 2 === 1 ? PAS_Y / 4 : 0
      points.push({
        pos,
        x: xj + (col - (cols - 1) / 2) * PAS_X,
        y: yc + (ligne - (dansCol - 1) / 2) * PAS_Y + quinconce,
      })
    })
  }
  const actif = ouvert ?? selection
  points.sort((a, b) => Number(a.pos.element_id === actif) - Number(b.pos.element_id === actif))
  const pointOuvert = points.find((p) => p.pos.element_id === ouvert)

  const ouvrir = (id: string) => {
    setOuvert(ouvert === id ? null : id)
    onSelect?.(id)
  }

  const description = (z: Zone) => zones.find((d) => d.zone === z)?.description ?? ''
  const rFin = rayon(X_FIN)
  const etiquettes: { zone: Zone; y: number }[] = [
    { zone: 'souhaitable', y: YC - SOUHAITABLE.centre * rFin },
    { zone: 'probable', y: YC },
    { zone: 'plausible', y: YC + ((RATIOS.probable + RATIOS.plausible) / 2) * rFin },
    { zone: 'possible', y: YC + ((RATIOS.plausible + RATIOS.possible) / 2) * rFin },
  ]
  const survol = (z: Zone | null) => () => setZoneActive(z)
  const epaisseur = (z: Zone) => (zoneActive === z ? 2.5 : 1.25)

  return (
    <figure className="w-full">
      <div className="mb-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-700">
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5" aria-label="Zones du cône">
          {ORDRE_ZONES.map((z) => (
            <li key={z} className="flex items-center gap-1.5">
              <span className={`inline-block h-3 w-5 rounded-sm border ${STYLE_ZONES[z].pastille}`} aria-hidden="true" />
              {LIBELLES_ZONES[z]}
            </li>
          ))}
        </ul>
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5" aria-label="Catégories">
          {ORDRE_CATEGORIES.map((c) => (
            <li key={c} className="flex items-center gap-1.5">
              <span className={`inline-block size-3 rounded-full ${COULEURS_CATEGORIES[c].pastille}`} aria-hidden="true" />
              {LIBELLES_CATEGORIES[c]}
            </li>
          ))}
        </ul>
        <span className="text-xs text-slate-500">Cliquez sur un élément pour afficher son détail.</span>
      </div>

      <div ref={conteneur} className="relative" onClick={() => setOuvert(null)}>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full select-none"
          role="img"
          aria-label={`Cône des futurs en perspective, d'aujourd'hui (${anneeDebut}) à 2040 : ${positions.length} éléments positionnés dans les zones probable, plausible, possible et souhaitable, aux jalons 2030, 2035 et 2040.`}
          fontFamily="ui-sans-serif, system-ui, sans-serif"
        >
          <defs>
            {ORDRE_ZONES.map((z) => (
              <linearGradient key={z} id={idDegrade(z)} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0" stopColor={STYLE_ZONES[z].clair} />
                <stop offset="0.45" stopColor={STYLE_ZONES[z].clair} />
                <stop offset="1" stopColor={STYLE_ZONES[z].sombre} />
              </linearGradient>
            ))}
            <radialGradient id={`${idFondu}-sol`} cx="0.5" cy="0.5" r="0.5">
              <stop offset="0" stopColor="#0f172a" stopOpacity={0.14} />
              <stop offset="1" stopColor="#0f172a" stopOpacity={0} />
            </radialGradient>
          </defs>

          {/* Ombre portée au sol, pour ancrer le volume */}
          <ellipse cx={(X0 + X_FIN) / 2 + 60} cy={YC + R + 34} rx={360} ry={16} fill={`url(#${idFondu}-sol)`} />

          {/* Moitiés arrière des sections aux jalons (cachées, en pointillés) */}
          {JALONS.map((annee) => {
            const x = xAnnee(annee)
            const { ry } = section('possible', x)
            return (
              <path
                key={`arriere-${annee}`}
                d={demiEllipse(x, YC, ry, 'arriere')}
                fill="none"
                stroke="#94a3b8"
                strokeWidth={1}
                strokeDasharray="3 4"
              />
            )
          })}

          {/* Cônes imbriqués, du plus large au plus étroit */}
          {(['possible', 'plausible', 'probable'] as const).map((z) => (
            <path
              key={z}
              d={CHEMINS[z]}
              fill={`url(#${idDegrade(z)})`}
              fillOpacity={z === 'possible' ? 1 : 0.85}
              stroke={STYLE_ZONES[z].trait}
              strokeWidth={epaisseur(z)}
              strokeLinejoin="round"
              onMouseEnter={survol(z)}
              onMouseLeave={survol(null)}
            >
              <title>{`${LIBELLES_ZONES[z]} : ${description(z)}`}</title>
            </path>
          ))}

          {/* Ouverture du cône en 2040 et au-delà : anneaux vus en perspective */}
          {(['possible', 'plausible', 'probable'] as const).map((z) => {
            const { cy, ry } = section(z, X_FIN)
            return (
              <ellipse
                key={`ouverture-${z}`}
                cx={X_FIN}
                cy={cy}
                rx={K * ry}
                ry={ry}
                fill={z === 'possible' ? '#ffffff' : STYLE_ZONES[z].clair}
                fillOpacity={z === 'possible' ? 0.75 : 0.9}
                stroke={STYLE_ZONES[z].trait}
                strokeWidth={epaisseur(z)}
                pointerEvents="none"
              />
            )
          })}

          {/* Cône souhaitable, incliné vers le haut */}
          <path
            d={CHEMINS.souhaitable}
            fill={`url(#${idDegrade('souhaitable')})`}
            fillOpacity={zoneActive === 'souhaitable' ? 0.55 : 0.4}
            stroke={STYLE_ZONES.souhaitable.trait}
            strokeWidth={zoneActive === 'souhaitable' ? 2.5 : 1.75}
            strokeDasharray="7 5"
            strokeLinejoin="round"
            onMouseEnter={survol('souhaitable')}
            onMouseLeave={survol(null)}
          >
            <title>{`${LIBELLES_ZONES.souhaitable} : ${description('souhaitable')}`}</title>
          </path>
          {(() => {
            const { cy, ry } = section('souhaitable', X_FIN)
            return (
              <ellipse
                cx={X_FIN}
                cy={cy}
                rx={K * ry}
                ry={ry}
                fill="#d1fae5"
                fillOpacity={0.8}
                stroke={STYLE_ZONES.souhaitable.trait}
                strokeWidth={1.5}
                strokeDasharray="5 4"
                pointerEvents="none"
              />
            )
          })()}

          {/* Moitiés avant des sections aux jalons */}
          {JALONS.map((annee) => {
            const x = xAnnee(annee)
            return (['possible', 'plausible', 'probable'] as const).map((z) => {
              const { ry } = section(z, x)
              return (
                <path
                  key={`avant-${annee}-${z}`}
                  d={demiEllipse(x, YC, ry, 'avant')}
                  fill="none"
                  stroke={z === 'possible' ? '#475569' : STYLE_ZONES[z].trait}
                  strokeWidth={z === 'possible' ? 1.5 : 1}
                  strokeOpacity={z === 'possible' ? 0.9 : 0.6}
                  pointerEvents="none"
                />
              )
            })
          })}

          {/* Axe du temps */}
          <line x1={X0} x2={X_FIN + 6} y1={H - 44} y2={H - 44} stroke="#94a3b8" strokeWidth={1} />
          <path d={`M${X_FIN + 6},${H - 48} L${X_FIN + 14},${H - 44} L${X_FIN + 6},${H - 40} Z`} fill="#94a3b8" />

          {/* Jalons */}
          {JALONS.map((annee) => {
            const x = xAnnee(annee)
            return (
              <g key={annee}>
                <line
                  x1={x}
                  x2={x}
                  y1={YC + section('possible', x).ry + 4}
                  y2={H - 44}
                  stroke="#64748b"
                  strokeWidth={1}
                  strokeDasharray="3 4"
                />
                <circle cx={x} cy={H - 44} r={3.5} fill="#475569" />
                <rect x={x - 26} y={H - 34} width={52} height={22} rx={11} fill="#0f172a" />
                <text x={x} y={H - 23} dy="0.35em" textAnchor="middle" fontSize={12} fontWeight={700} fill="#ffffff">
                  {annee}
                </text>
              </g>
            )
          })}

          {/* Aujourd'hui */}
          <line x1={X0} x2={X0} y1={YC} y2={H - 44} stroke="#0f172a" strokeWidth={1} strokeDasharray="2 3" />
          <circle cx={X0} cy={YC} r={7} fill="#0f172a" stroke="#ffffff" strokeWidth={2} />
          <text x={X0} y={YC - 16} textAnchor="middle" fontSize={13} fontWeight={700} fill="#0f172a">
            Aujourd'hui
          </text>
          <text x={X0} y={H - 23} dy="0.35em" textAnchor="middle" fontSize={12} fontWeight={600} fill="#334155">
            {anneeDebut}
          </text>

          {/* Libellés des zones, à droite de l'ouverture */}
          {etiquettes.map(({ zone, y }) => (
            <g key={zone}>
              <line
                x1={X_FIN + K * section(zone, X_FIN).ry * 0.2 + 4}
                x2={X_FIN + 70}
                y1={y}
                y2={y}
                stroke={zone === 'souhaitable' ? STYLE_ZONES.souhaitable.trait : '#64748b'}
                strokeWidth={1}
                strokeDasharray="2 3"
              />
              <text
                x={X_FIN + 74}
                y={y}
                dy="0.35em"
                fontSize={13}
                fontWeight={zoneActive === zone ? 800 : 600}
                fill={zone === 'souhaitable' ? '#047857' : '#334155'}
              >
                {LIBELLES_ZONES[zone]}
              </text>
            </g>
          ))}

          {/* Positions */}
          {points.map(({ pos, x, y }) => {
            const estActif = pos.element_id === actif
            const couleur = COULEURS_CATEGORIES[pos.categorie]?.hex ?? '#475569'
            const taille = Math.max(6.5, Math.min(8.5, 30 / Math.max(pos.element_id.length, 1)))
            return (
              <g
                key={`${pos.element_id}-${pos.zone}-${pos.jalon}`}
                className="cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation()
                  ouvrir(pos.element_id)
                }}
                onKeyDown={(ev) => {
                  if (ev.key === 'Enter' || ev.key === ' ') {
                    ev.preventDefault()
                    ouvrir(pos.element_id)
                  }
                }}
                tabIndex={0}
                role="button"
                aria-label={`${pos.element_id} : ${pos.titre}`}
                opacity={actif && !estActif ? 0.55 : 1}
              >
                {/* Ombre légère sous le point, pour le relief */}
                <ellipse cx={x + 1.5} cy={y + RAYON_POINT - 1} rx={RAYON_POINT * 0.8} ry={3} fill="#0f172a" opacity={0.18} />
                {estActif && (
                  <circle cx={x} cy={y} r={RAYON_POINT + 5.5} fill="#ffffff" stroke="#0f172a" strokeWidth={2.5} />
                )}
                <circle
                  cx={x}
                  cy={y}
                  r={estActif ? RAYON_POINT + 1.5 : RAYON_POINT}
                  fill={couleur}
                  stroke="#ffffff"
                  strokeWidth={1.75}
                />
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
                  {pos.element_id}
                </text>
              </g>
            )
          })}
        </svg>

        {pointOuvert && <Popup point={pointOuvert} onFermer={() => setOuvert(null)} />}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {ORDRE_ZONES.map((z) => {
          const texte = description(z)
          return (
            <section
              key={z}
              onMouseEnter={survol(z)}
              onMouseLeave={survol(null)}
              className={`rounded-xl border p-3.5 transition-shadow ${STYLE_ZONES[z].carte} ${
                zoneActive === z ? 'shadow-md ring-2 ring-slate-900/15' : 'shadow-sm'
              }`}
            >
              <h4
                className={`mb-1.5 flex items-center gap-2 text-sm font-semibold ${
                  z === 'souhaitable' ? 'text-emerald-800' : 'text-slate-800'
                }`}
              >
                <span className={`inline-block h-3 w-5 rounded-sm border ${STYLE_ZONES[z].pastille}`} aria-hidden="true" />
                {LIBELLES_ZONES[z]}
                <span className="ml-auto text-xs font-normal text-slate-500">
                  {positions.filter((p) => p.zone === z).length} élément(s)
                </span>
              </h4>
              <p className="text-sm leading-relaxed text-slate-600">{texte || 'Pas de description.'}</p>
            </section>
          )
        })}
      </div>
    </figure>
  )
}
