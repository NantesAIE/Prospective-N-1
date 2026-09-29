import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { ETAPES } from '../etapes'
import type { MessageChat, ResultatSource, Session, Suggestion } from '../types'
import { Bouton, Chargement, LienSource, TexteMarkdown } from './ui'

const RACCOURCIS = [
  'Qui sont mes concurrents sur le territoire ?',
  'Que dit la presse récente sur ce sujet ?',
  'Comment améliorer cette étape ?',
  'Quels risques suis-je en train de sous-estimer ?',
]

function CarteResultat({
  resultat,
  onAjouter,
}: {
  resultat: ResultatSource
  onAjouter?: (r: ResultatSource) => void
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-2 text-xs">
      <p className="font-medium text-slate-800">{resultat.titre}</p>
      <p className="mt-0.5 line-clamp-2 text-slate-600">{resultat.resume}</p>
      <div className="mt-1 flex items-center gap-2">
        <LienSource
          source={resultat.source}
          url={resultat.url}
          date={resultat.date}
          niveau={resultat.niveau}
          demo={resultat.donnees_demo}
        />
        {onAjouter && (
          <button
            type="button"
            onClick={() => onAjouter(resultat)}
            className="ml-auto shrink-0 rounded bg-indigo-50 px-1.5 py-0.5 font-medium text-indigo-700 hover:bg-indigo-100"
          >
            + Signaux
          </button>
        )}
      </div>
    </div>
  )
}

function CarteSuggestion({
  suggestion,
  onAppliquer,
}: {
  suggestion: Suggestion
  onAppliquer?: (s: Suggestion) => void
}) {
  return (
    <div className="rounded-lg border border-indigo-200 bg-indigo-50/60 p-2 text-xs">
      <p className="font-semibold text-indigo-900">💡 {suggestion.titre}</p>
      <p className="mt-0.5 text-slate-700">{suggestion.explication}</p>
      {onAppliquer && (
        <Bouton variante="principal" className="mt-1.5 !px-2 !py-1 text-xs" onClick={() => onAppliquer(suggestion)}>
          Relancer l'étape {suggestion.etape} ({ETAPES[suggestion.etape]?.court}) avec cette consigne
        </Bouton>
      )}
    </div>
  )
}

/** Panneau conversationnel : parler du projet, interroger les sources, recevoir des suggestions. */
export function Assistant({
  session,
  etape,
  occupe,
  onAppliquer,
  onAjouterSignal,
  onFermer,
}: {
  session: Session
  etape: number
  occupe: boolean
  onAppliquer: (s: Suggestion) => void
  onAjouterSignal?: (r: ResultatSource) => void
  onFermer: () => void
}) {
  const [messages, setMessages] = useState<MessageChat[]>([])
  const [saisie, setSaisie] = useState('')
  const [attente, setAttente] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const fin = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.conversation(session.id).then(setMessages).catch(() => setMessages([]))
  }, [session.id])

  useEffect(() => {
    fin.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, attente])

  const envoyer = async (texte: string) => {
    if (!texte.trim() || attente) return
    setErreur(null)
    setSaisie('')
    setMessages((m) => [
      ...m,
      { role: 'user', contenu: texte, etape, horodatage: '', suggestions: [], resultats: [] },
    ])
    setAttente(true)
    try {
      setMessages(await api.parler(session.id, texte, etape))
    } catch (e) {
      setErreur((e as Error).message)
    } finally {
      setAttente(false)
    }
  }

  return (
    <aside className="flex w-96 shrink-0 flex-col border-l border-slate-200 bg-slate-50">
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <div>
          <p className="text-sm font-semibold text-slate-800">Assistant prospectiviste</p>
          <p className="text-xs text-slate-500">
            Parlez de votre projet, interrogez les sources, demandez des suggestions.
          </p>
        </div>
        <Bouton variante="discret" className="!px-2" onClick={onFermer} aria-label="Masquer l'assistant">
          ▸
        </Bouton>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        {!messages.length && (
          <div className="space-y-2">
            <p className="text-sm text-slate-600">
              Je connais votre strong context et l'avancement du dossier. Essayez :
            </p>
            {RACCOURCIS.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => envoyer(r)}
                className="block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-700 hover:border-indigo-300"
              >
                {r}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) =>
          m.role === 'user' ? (
            <div key={i} className="ml-8 rounded-2xl rounded-br-sm bg-indigo-600 px-3 py-2 text-sm text-white">
              {m.contenu}
            </div>
          ) : (
            <div key={i} className="mr-4 space-y-2">
              <div className="rounded-2xl rounded-bl-sm bg-white px-3 py-2 shadow-sm">
                <TexteMarkdown>{m.contenu || '_(pas de réponse)_'}</TexteMarkdown>
              </div>
              {m.resultats.length > 0 && (
                <details className="rounded-lg">
                  <summary className="cursor-pointer text-xs font-medium text-slate-600">
                    {m.resultats.length} résultat(s) de sources interrogées
                  </summary>
                  <div className="mt-1 space-y-1.5">
                    {m.resultats.map((r) => (
                      <CarteResultat key={r.id} resultat={r} onAjouter={onAjouterSignal} />
                    ))}
                  </div>
                </details>
              )}
              {m.suggestions.map((s, k) => (
                <CarteSuggestion key={k} suggestion={s} onAppliquer={occupe ? undefined : onAppliquer} />
              ))}
            </div>
          ),
        )}
        {attente && <Chargement texte="L'assistant réfléchit et interroge les sources…" />}
        {erreur && <p className="text-sm text-rose-700">{erreur}</p>}
        <div ref={fin} />
      </div>

      <form
        className="border-t border-slate-200 bg-white p-3"
        onSubmit={(e) => {
          e.preventDefault()
          envoyer(saisie)
        }}
      >
        <textarea
          className="w-full resize-none rounded-lg border border-slate-300 p-2 text-sm"
          rows={2}
          placeholder="Votre question sur le projet ou l'étape en cours…"
          value={saisie}
          onChange={(e) => setSaisie(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              envoyer(saisie)
            }
          }}
        />
        <div className="mt-1 flex items-center justify-between">
          <span className="text-xs text-slate-400">Entrée pour envoyer, Maj+Entrée pour aller à la ligne</span>
          <Bouton type="submit" variante="principal" disabled={attente || !saisie.trim()}>
            Envoyer
          </Bouton>
        </div>
      </form>
    </aside>
  )
}
