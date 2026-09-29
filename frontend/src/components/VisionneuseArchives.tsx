import { useEffect, useState } from 'react'
import { api } from '../api'
import { Bouton, Chargement, TexteMarkdown } from './ui'

function retirerFrontmatter(texte: string) {
  return texte.replace(/^---\n[\s\S]*?\n---\n/, '')
}

/** Consultation des fichiers `.md` de la session (archives, journal, synthèse). */
export function VisionneuseArchives({
  sessionId,
  initial,
  onFermer,
}: {
  sessionId: string
  initial?: string
  onFermer: () => void
}) {
  const [fichiers, setFichiers] = useState<string[]>([])
  const [choisi, setChoisi] = useState<string | null>(initial ?? null)
  const [contenu, setContenu] = useState<string | null>(null)

  useEffect(() => {
    api.fichiers(sessionId).then((f) => {
      setFichiers(f)
      setChoisi((c) => c ?? f.find((n) => n === '00-SYNTHESE.md') ?? f[0] ?? null)
    })
  }, [sessionId])

  useEffect(() => {
    if (!choisi) return
    setContenu(null)
    api.fichier(sessionId, choisi).then(setContenu)
  }, [sessionId, choisi])

  const telecharger = () => {
    if (!contenu || !choisi) return
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(new Blob([contenu], { type: 'text/markdown' }))
    lien.download = choisi
    lien.click()
    URL.revokeObjectURL(lien.href)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={onFermer}>
      <div
        className="flex h-[85vh] w-full max-w-6xl overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Dossier archivé"
      >
        <nav className="w-60 shrink-0 overflow-y-auto border-r border-slate-200 bg-slate-50 p-3">
          <p className="mb-2 text-xs font-semibold text-slate-500 uppercase">Fichiers de la session</p>
          {fichiers.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setChoisi(f)}
              className={`block w-full truncate rounded px-2 py-1 text-left font-mono text-xs ${
                f === choisi ? 'bg-indigo-100 text-indigo-800' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {f}
            </button>
          ))}
          {!fichiers.length && <p className="text-xs text-slate-500">Aucune étape validée pour l'instant.</p>}
        </nav>
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-2">
            <span className="font-mono text-sm text-slate-700">{choisi}</span>
            <Bouton className="ml-auto" disabled={!contenu} onClick={telecharger}>
              Télécharger
            </Bouton>
            <Bouton variante="discret" onClick={onFermer}>
              Fermer
            </Bouton>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {contenu === null ? (
              choisi && <Chargement texte="Chargement…" />
            ) : (
              <TexteMarkdown>{retirerFrontmatter(contenu)}</TexteMarkdown>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
