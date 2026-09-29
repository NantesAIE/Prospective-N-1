import { useState } from 'react'
import type { EtatEtape } from '../types'
import { Bouton } from './ui'

type Panneau = 'modifier' | 'relancer' | null

/** Barre HITL fixe : Valider, Modifier (édition directe ou commentaire), Relancer (avec consigne). */
export function BarreValidation({
  etat,
  occupe,
  nonEnregistre,
  suivanteValidee,
  onValider,
  onEnregistrer,
  onRelancer,
  onSuivante,
  onModeEdition,
}: {
  etat: EtatEtape
  occupe: boolean
  nonEnregistre: boolean
  suivanteValidee: boolean
  onValider: () => void
  onEnregistrer: (commentaire: string) => void
  onRelancer: (consigne: string) => void
  onSuivante: () => void
  onModeEdition: (actif: boolean) => void
}) {
  const [panneau, setPanneau] = useState<Panneau>(null)
  const [commentaire, setCommentaire] = useState(etat.commentaire)
  const [consigne, setConsigne] = useState('')
  const valide = etat.statut === 'valide'

  const ouvrir = (p: Panneau) => {
    const suivant = panneau === p ? null : p
    setPanneau(suivant)
    onModeEdition(suivant === 'modifier')
  }
  const avertissement =
    valide && suivanteValidee
      ? 'Reprendre une étape validée remet les étapes suivantes à revalider (leurs archives sont conservées).'
      : null

  return (
    <div className="border-t border-slate-200 bg-white/95 px-4 py-3 shadow-[0_-4px_12px_rgba(0,0,0,0.04)] backdrop-blur">
      {panneau === 'modifier' && (
        <div className="mb-3 space-y-2">
          <p className="text-sm text-slate-600">
            Éditez directement le livrable ci-dessus et/ou laissez un commentaire, archivé dans la
            section « Modifications utilisateur ».
          </p>
          <textarea
            className="w-full rounded-lg border border-slate-300 p-2 text-sm"
            rows={2}
            placeholder="Commentaire (facultatif)"
            value={commentaire}
            onChange={(e) => setCommentaire(e.target.value)}
          />
          {avertissement && <p className="text-xs text-amber-700">{avertissement}</p>}
          <Bouton
            variante="principal"
            disabled={occupe}
            onClick={() => {
              onEnregistrer(commentaire)
              setPanneau(null)
              onModeEdition(false)
            }}
          >
            Enregistrer les modifications
          </Bouton>
        </div>
      )}
      {panneau === 'relancer' && (
        <div className="mb-3 space-y-2">
          <textarea
            className="w-full rounded-lg border border-slate-300 p-2 text-sm"
            rows={2}
            placeholder="Consigne pour la nouvelle génération (ex. : insiste davantage sur les aidants familiaux)"
            value={consigne}
            onChange={(e) => setConsigne(e.target.value)}
          />
          {avertissement && <p className="text-xs text-amber-700">{avertissement}</p>}
          <Bouton
            variante="principal"
            disabled={occupe}
            onClick={() => {
              onRelancer(consigne)
              setConsigne('')
              setPanneau(null)
            }}
          >
            Relancer la génération
          </Bouton>
          <span className="ml-2 text-xs text-slate-500">L'ancienne version est conservée en archive.</span>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        {valide ? (
          <>
            <span className="text-sm font-medium text-emerald-700">
              ✓ Étape validée{etat.valide_le ? ` le ${new Date(etat.valide_le).toLocaleString('fr-FR')}` : ''}
            </span>
            <Bouton variante="principal" onClick={onSuivante} className="ml-2">
              Étape suivante →
            </Bouton>
          </>
        ) : (
          <Bouton variante="principal" disabled={occupe || !etat.livrable} onClick={onValider}>
            ✓ Valider
          </Bouton>
        )}
        <Bouton
          disabled={occupe || !etat.livrable}
          variante={panneau === 'modifier' ? 'principal' : 'secondaire'}
          onClick={() => ouvrir('modifier')}
        >
          ✎ Modifier
        </Bouton>
        <Bouton
          disabled={occupe || !etat.livrable}
          variante={panneau === 'relancer' ? 'principal' : 'secondaire'}
          onClick={() => ouvrir('relancer')}
        >
          ↻ Relancer
        </Bouton>
        {nonEnregistre && (
          <span className="text-xs font-medium text-amber-700">
            Modifications non enregistrées : elles seront enregistrées à la validation.
          </span>
        )}
        <span className="ml-auto text-xs text-slate-400">
          Version {etat.version}
          {etat.modifie && ', modifiée'}
        </span>
      </div>
    </div>
  )
}
