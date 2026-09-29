import type { ButtonHTMLAttributes, ReactNode } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { LIBELLES_AXES, LIBELLES_NIVEAUX, type Axe, type Niveau } from '../types'

type Variante = 'principal' | 'secondaire' | 'discret' | 'danger'

const VARIANTES: Record<Variante, string> = {
  principal: 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300',
  secondaire:
    'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:text-slate-400',
  discret: 'text-slate-600 hover:bg-slate-100 disabled:text-slate-300',
  danger: 'border border-rose-300 bg-white text-rose-700 hover:bg-rose-50',
}

export function Bouton({
  variante = 'secondaire',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: Variante }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed ${VARIANTES[variante]} ${className}`}
      {...props}
    />
  )
}

export function Carte({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}>
      {children}
    </div>
  )
}

export function Titre({ children }: { children: ReactNode }) {
  return <h3 className="mb-2 text-sm font-semibold tracking-wide text-slate-500 uppercase">{children}</h3>
}

export const COULEURS_AXES: Record<Axe, string> = {
  S: 'bg-rose-100 text-rose-800',
  T: 'bg-violet-100 text-violet-800',
  E1: 'bg-amber-100 text-amber-800',
  E2: 'bg-emerald-100 text-emerald-800',
  P: 'bg-sky-100 text-sky-800',
  L: 'bg-slate-200 text-slate-800',
}

export function BadgeAxe({ axe }: { axe: Axe }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${COULEURS_AXES[axe]}`}>
      {LIBELLES_AXES[axe]}
    </span>
  )
}

const COULEURS_NIVEAUX: Record<Niveau, string> = {
  monde: 'bg-sky-600',
  zone: 'bg-indigo-600',
  pays: 'bg-emerald-600',
  local: 'bg-amber-500',
}

export function PastilleNiveau({ niveau }: { niveau: Niveau }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-slate-600">
      <span className={`h-2 w-2 rounded-full ${COULEURS_NIVEAUX[niveau]}`} />
      {LIBELLES_NIVEAUX[niveau]}
    </span>
  )
}

/** Indicateur de source : pastille de niveau et lien, ou mention « hypothèse IA ». */
export function LienSource({
  source,
  url,
  date,
  niveau,
  hypotheseIa,
  demo,
}: {
  source?: string | null
  url?: string | null
  date?: string | null
  niveau?: Niveau | null
  hypotheseIa?: boolean
  demo?: boolean
}) {
  if (hypotheseIa && !url) {
    return (
      <span className="inline-flex items-center gap-2 text-xs">
        <span className="rounded bg-orange-100 px-1.5 py-0.5 font-medium text-orange-800">
          hypothèse IA
        </span>
        {source && <span className="text-slate-500">{source}</span>}
      </span>
    )
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-2 text-xs text-slate-600">
      {niveau && <PastilleNiveau niveau={niveau} />}
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-indigo-700 underline decoration-indigo-200 hover:decoration-indigo-600"
        >
          {source || 'source'}
        </a>
      ) : (
        <span>{source || 'ajout manuel, non sourcé'}</span>
      )}
      {date && <span className="text-slate-400">{date.slice(0, 10)}</span>}
      {demo && (
        <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-yellow-800">
          données de démonstration
        </span>
      )}
    </span>
  )
}

export function Chargement({ texte }: { texte: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-600">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
      {texte}
    </div>
  )
}

export function Alerte({ children, ton = 'erreur' }: { children: ReactNode; ton?: 'erreur' | 'info' | 'avertissement' }) {
  const styles = {
    erreur: 'border-rose-200 bg-rose-50 text-rose-800',
    info: 'border-sky-200 bg-sky-50 text-sky-800',
    avertissement: 'border-amber-200 bg-amber-50 text-amber-900',
  }
  return <div className={`rounded-lg border px-3 py-2 text-sm ${styles[ton]}`}>{children}</div>
}

export function TexteMarkdown({ children }: { children: string }) {
  return (
    <div className="prose-mini text-sm leading-relaxed text-slate-800">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ ...p }) => <a {...p} target="_blank" rel="noreferrer" className="text-indigo-700 underline" />,
          h1: ({ ...p }) => <h1 {...p} className="mt-4 mb-2 text-xl font-bold" />,
          h2: ({ ...p }) => <h2 {...p} className="mt-4 mb-2 text-lg font-bold" />,
          h3: ({ ...p }) => <h3 {...p} className="mt-3 mb-1 font-semibold" />,
          h4: ({ ...p }) => <h4 {...p} className="mt-3 mb-1 font-semibold" />,
          p: ({ ...p }) => <p {...p} className="my-2" />,
          ul: ({ ...p }) => <ul {...p} className="my-2 list-disc pl-5" />,
          ol: ({ ...p }) => <ol {...p} className="my-2 list-decimal pl-5" />,
          blockquote: ({ ...p }) => (
            <blockquote {...p} className="my-2 border-l-4 border-slate-200 pl-3 text-slate-600 italic" />
          ),
          table: ({ ...p }) => (
            <div className="my-2 overflow-x-auto">
              <table {...p} className="w-full border-collapse text-xs" />
            </div>
          ),
          th: ({ ...p }) => <th {...p} className="border border-slate-200 bg-slate-50 px-2 py-1 text-left" />,
          td: ({ ...p }) => <td {...p} className="border border-slate-200 px-2 py-1 align-top" />,
          code: ({ ...p }) => <code {...p} className="rounded bg-slate-100 px-1 text-xs" />,
        }}
      >
        {children}
      </Markdown>
    </div>
  )
}

/** Champ de liste éditable : une valeur par ligne. */
export function ListeEditable({
  valeurs,
  onChange,
  lignes = 4,
}: {
  valeurs: string[]
  onChange: (v: string[]) => void
  lignes?: number
}) {
  return (
    <textarea
      className="w-full rounded-lg border border-slate-300 p-2 text-sm"
      rows={lignes}
      value={valeurs.join('\n')}
      onChange={(e) => onChange(e.target.value.split('\n'))}
    />
  )
}

export function Puces({ elements }: { elements: string[] }) {
  return (
    <ul className="list-disc space-y-1 pl-5 text-sm text-slate-800">
      {elements.filter(Boolean).map((e, i) => (
        <li key={i}>{e}</li>
      ))}
    </ul>
  )
}
