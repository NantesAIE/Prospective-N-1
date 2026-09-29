import { useState } from 'react'
import { Matrice2x2 } from '../components/viz/Matrice2x2'
import { Carte, Puces, Titre } from '../components/ui'
import type { ElementQualifie, LivrableScenarios, LivrableSteepl, Quadrant, Session } from '../types'
import type { OptionsEtapeProps, VueEtapeProps } from './commun'

type Choix = LivrableScenarios['choix']

/** Éléments triés par criticité, incertitudes en premier (même règle que le back-end). */
export function incertitudesCritiques(session: Session): ElementQualifie[] {
  const elements = (session.etapes[4].livrable as LivrableSteepl | null)?.elements ?? []
  const cle = (e: ElementQualifie) => [e.categorie === 'incertitude' ? 1 : 0, e.impact * e.incertitude, e.impact]
  return [...elements].sort((a, b) => {
    const [ka, kb] = [cle(a), cle(b)]
    return kb[0] - ka[0] || kb[1] - ka[1] || kb[2] - ka[2]
  })
}

export function optionsInitialesScenarios(session: Session) {
  const livrable = session.etapes[6].livrable as LivrableScenarios | null
  const critiques = incertitudesCritiques(session)
  return {
    incertitudes: livrable
      ? [livrable.axe_x.element_id, livrable.axe_y.element_id]
      : critiques.slice(0, 2).map((e) => e.id),
    choix: livrable?.choix ?? { cible: null, vigilance: null },
  }
}

/** Choix des deux incertitudes critiques qui forment les axes de la matrice. */
export function OptionsScenarios({ session, options, onOptions }: OptionsEtapeProps) {
  const critiques = incertitudesCritiques(session)
  const choisies = (options.incertitudes as string[] | undefined) ?? []
  const changer = (i: number, id: string) => {
    const suivantes = [...choisies]
    suivantes[i] = id
    onOptions({ ...options, incertitudes: suivantes })
  }
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {['Axe X (horizontal)', 'Axe Y (vertical)'].map((libelle, i) => (
        <label key={libelle} className="text-sm">
          <span className="font-medium text-slate-700">{libelle}</span>
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            value={choisies[i] ?? ''}
            onChange={(e) => changer(i, e.target.value)}
          >
            {critiques.map((e) => (
              <option key={e.id} value={e.id} disabled={choisies[1 - i] === e.id}>
                {e.id} {e.titre} (impact {e.impact} × incertitude {e.incertitude})
              </option>
            ))}
          </select>
        </label>
      ))}
      <p className="text-xs text-slate-500 md:col-span-2">
        Proposition par défaut : les deux éléments aux scores d'impact et d'incertitude les plus
        élevés. Changez-les puis relancez pour reconstruire la matrice.
      </p>
    </div>
  )
}

export function Etape6Scenarios(props: VueEtapeProps<LivrableScenarios>) {
  const { livrable, options, onOptions } = props
  const choix = (options.choix as Choix | undefined) ?? livrable.choix
  const [ouvert, setOuvert] = useState<Quadrant | null>(choix.cible ?? '++')
  const scenario = livrable.scenarios.find((s) => s.quadrant === ouvert)
  const peutChoisir = props.session.etapes[6].statut !== 'valide'

  const choisir = (q: Quadrant, role: 'cible' | 'vigilance') => {
    const suivant: Choix = { ...choix, [role]: choix[role] === q ? null : q }
    if (role === 'cible' && suivant.vigilance === q) suivant.vigilance = null
    if (role === 'vigilance' && suivant.cible === q) suivant.cible = null
    onOptions({ ...options, choix: suivant })
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        {peutChoisir
          ? 'Choisissez le futur visé (« où tu veux aller »), et éventuellement un scénario de vigilance, puis validez.'
          : 'Scénarios validés.'}
      </p>
      <Matrice2x2
        livrable={{ ...livrable, choix }}
        ouvert={ouvert}
        onOuvrir={setOuvert}
        onChoisir={peutChoisir ? choisir : undefined}
      />
      {scenario && (
        <Carte>
          <Titre>
            Scénario {scenario.quadrant} : {scenario.titre}
          </Titre>
          <p className="text-sm leading-relaxed whitespace-pre-line text-slate-800">{scenario.recit}</p>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div>
              <p className="mb-1 text-xs font-semibold text-slate-500">Implication pour le projet</p>
              <p className="text-sm text-slate-700">{scenario.implication_projet}</p>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold text-slate-500">Conditions de bascule</p>
              <Puces elements={scenario.conditions_bascule} />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold text-slate-500">Signaux et tendances qui y mènent</p>
              <p className="font-mono text-xs text-slate-600">{scenario.elements_menants.join(', ')}</p>
            </div>
          </div>
        </Carte>
      )}
      {peutChoisir && props.modifiable && (
        <Carte>
          <Titre>Changer les incertitudes critiques</Titre>
          <OptionsScenarios session={props.session} options={options} onOptions={onOptions} />
        </Carte>
      )}
    </div>
  )
}
