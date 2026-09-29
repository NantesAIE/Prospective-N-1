import { useEffect, useState } from 'react'
import { ArtefactFiction } from '../components/viz/ArtefactFiction'
import { Bouton, Carte, Titre } from '../components/ui'
import { LIBELLES_FORMATS, type FormatArtefact, type LivrableRestitution } from '../types'
import type { OptionsEtapeProps, VueEtapeProps } from './commun'

const FORMATS = Object.keys(LIBELLES_FORMATS) as FormatArtefact[]

/** Choix du format de l'artefact de design fiction. */
export function OptionsRestitution({ options, onOptions }: OptionsEtapeProps) {
  const choisi = (options.format_artefact as FormatArtefact | undefined) ?? 'une_de_presse'
  return (
    <div>
      <p className="mb-2 text-sm text-slate-600">Quel objet venu du futur voulez-vous obtenir ?</p>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
        {FORMATS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => onOptions({ ...options, format_artefact: f })}
            className={`rounded-lg border px-3 py-2 text-sm font-medium ${
              choisi === f
                ? 'border-indigo-600 bg-indigo-50 text-indigo-800'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {LIBELLES_FORMATS[f]}
          </button>
        ))}
      </div>
    </div>
  )
}

export function Etape8Restitution(props: VueEtapeProps<LivrableRestitution>) {
  const { livrable } = props
  const [pleinEcran, setPleinEcran] = useState(false)

  useEffect(() => {
    if (!pleinEcran) return
    const clavier = (e: KeyboardEvent) => e.key === 'Escape' && setPleinEcran(false)
    document.addEventListener('keydown', clavier)
    return () => document.removeEventListener('keydown', clavier)
  }, [pleinEcran])
  return (
    <div className="space-y-4">
      <Carte>
        <Titre>Synthèse exécutive</Titre>
        <p className="text-sm leading-relaxed text-slate-800">{livrable.synthese_executive}</p>
      </Carte>
      <div>
        <div className="mb-2 flex justify-end">
          <Bouton onClick={() => setPleinEcran(true)}>⤢ Lire en plein écran</Bouton>
        </div>
        <ArtefactFiction artefact={livrable.artefact} />
      </div>
      <Carte>
        <Titre>Une journée en 2040</Titre>
        <h4 className="mb-2 text-lg font-semibold text-slate-900">{livrable.narratif.titre}</h4>
        <p className="max-w-4xl text-sm leading-relaxed whitespace-pre-line text-slate-800">
          {livrable.narratif.texte}
        </p>
      </Carte>
      {pleinEcran && (
        <div
          className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 p-4 md:p-10"
          onClick={() => setPleinEcran(false)}
          role="dialog"
          aria-label="Artefact en plein écran"
        >
          <div className="mx-auto max-w-6xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex justify-end">
              <Bouton onClick={() => setPleinEcran(false)}>✕ Fermer</Bouton>
            </div>
            <ArtefactFiction artefact={livrable.artefact} />
          </div>
        </div>
      )}
      {props.modifiable && (
        <Carte>
          <Titre>Changer de format d'artefact</Titre>
          <OptionsRestitution session={props.session} options={props.options} onOptions={props.onOptions} />
          <p className="mt-2 text-xs text-slate-500">Puis « Relancer » pour générer le nouvel artefact.</p>
        </Carte>
      )}
    </div>
  )
}
