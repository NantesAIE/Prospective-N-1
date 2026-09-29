import type { ReactNode } from 'react'
import photoUne from '../../assets/une-2040-seance-sport-sante.jpeg'
import type { Artefact, TypeBloc } from '../../types'

interface Props {
  artefact: Artefact
}

type Bloc = Artefact['blocs'][number]

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------

/** Une ligne par élément, sans les puces « - », « • » ou « * ». */
const lignesListe = (texte: string) =>
  texte
    .split(/\r?\n/)
    .map((l) => l.replace(/^\s*[-•–*]\s*/, '').trim())
    .filter(Boolean)

/** Retire les guillemets éventuels autour d'une citation. */
const sansGuillemets = (texte: string) => texte.trim().replace(/^[«"“„]\s*/, '').replace(/\s*[»"”]$/, '')

/** Empreinte déterministe d'une chaîne (djb2), pour les détails « fictifs » stables. */
function empreinte(s: string): number {
  let h = 5381
  for (let i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0
  return h
}

const annee = (date: string) => date.match(/\b(2\d{3})\b/)?.[1] ?? null

const initiales = (nom: string) =>
  nom
    .split(/[\s'’-]+/)
    .filter((m) => m.length > 0 && /[A-Za-zÀ-ÿ0-9]/.test(m[0]))
    .slice(0, 2)
    .map((m) => m[0].toUpperCase())
    .join('') || '•'

const de = (blocs: Bloc[], ...types: TypeBloc[]) => blocs.filter((b) => types.includes(b.type))

function IconeCoche({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={`size-4 shrink-0 ${className}`} aria-hidden="true">
      <circle cx={8} cy={8} r={8} fill="currentColor" opacity={0.15} />
      <path d="M4.5 8.3 L7 10.6 L11.5 5.6" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Une de presse locale
// ---------------------------------------------------------------------------

function CodeBarres({ graine }: { graine: number }) {
  const barres: { x: number; w: number }[] = []
  let x = 0
  let h = graine || 1
  for (let i = 0; i < 34; i++) {
    h = (Math.imul(h, 1103515245) + 12345) >>> 0
    const w = 1 + ((h >>> 16) % 3)
    barres.push({ x, w })
    x += w + 1 + ((h >>> 20) % 2)
  }
  return (
    <svg viewBox={`0 0 ${x} 24`} className="h-6 w-20" aria-hidden="true" preserveAspectRatio="none">
      {barres.map((b, i) => (
        <rect key={i} x={b.x} y={0} width={b.w} height={24} fill="#1c1917" />
      ))}
    </svg>
  )
}

function BlocPresse({ bloc, lettrine }: { bloc: Bloc; lettrine: boolean }) {
  switch (bloc.type) {
    case 'titre':
      return <h3 className="mt-4 mb-1.5 break-after-avoid text-lg leading-tight font-bold text-stone-900">{bloc.texte}</h3>
    case 'chapo':
      return <p className="mb-3 font-semibold text-stone-800">{bloc.texte}</p>
    case 'citation':
      return (
        <blockquote className="my-4 break-inside-avoid border-y-2 border-stone-800 py-3 text-center text-xl leading-snug text-stone-900 italic">
          « {sansGuillemets(bloc.texte)} »
        </blockquote>
      )
    case 'liste':
      return (
        <ul className="mb-3 space-y-1">
          {lignesListe(bloc.texte).map((l, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-2 inline-block size-1.5 shrink-0 bg-red-700" aria-hidden="true" />
              <span>{l}</span>
            </li>
          ))}
        </ul>
      )
    default:
      return (
        <p
          className={`mb-3 ${
            lettrine
              ? 'first-letter:float-left first-letter:mt-1 first-letter:mr-2 first-letter:text-6xl first-letter:leading-[0.8] first-letter:font-black first-letter:text-stone-900'
              : ''
          }`}
        >
          {bloc.texte}
        </p>
      )
  }
}

function EncadrePresse({ bloc }: { bloc: Bloc }) {
  if (bloc.type === 'liste') {
    return (
      <div className="break-inside-avoid border-t-4 border-stone-900 bg-white/70 p-4">
        <p className="mb-2 font-sans text-[11px] font-bold tracking-[0.2em] text-stone-700 uppercase">Repères</p>
        <ul className="space-y-2 text-sm leading-snug">
          {lignesListe(bloc.texte).map((l, i) => (
            <li key={i} className="flex gap-2 border-b border-stone-300 pb-2 last:border-0 last:pb-0">
              <span className="font-sans text-xs font-bold text-red-700">{String(i + 1).padStart(2, '0')}</span>
              <span>{l}</span>
            </li>
          ))}
        </ul>
      </div>
    )
  }
  const lignes = bloc.texte.split(/\r?\n/).filter((l) => l.trim())
  const [tete, ...reste] = lignes
  return (
    <div className="break-inside-avoid border-t-4 border-red-700 bg-stone-200/70 p-4 font-sans text-sm leading-relaxed text-stone-800">
      {reste.length > 0 ? (
        <>
          <p className="mb-1.5 font-bold text-stone-900">{tete}</p>
          {reste.map((l, i) => (
            <p key={i} className="mb-1 last:mb-0">
              {l}
            </p>
          ))}
        </>
      ) : (
        <p>{bloc.texte}</p>
      )}
    </div>
  )
}

function UneDePresse({ a }: { a: Artefact }) {
  const surtitres = de(a.blocs, 'surtitre')
  const chapos = de(a.blocs, 'chapo')
  const chapo = chapos[0]
  const corps = a.blocs.filter(
    (b) => b.type === 'paragraphe' || b.type === 'titre' || b.type === 'citation' || (b.type === 'chapo' && b !== chapo),
  )
  const lateral = de(a.blocs, 'encadre', 'liste')
  const mentions = de(a.blocs, 'mention')
  const prix = de(a.blocs, 'prix')[0]
  const graine = empreinte(`${a.media}|${a.date_fictive}|${a.titre}`)
  const numero = (10000 + (graine % 89999)).toLocaleString('fr-FR')
  const premierParagraphe = corps.findIndex((b) => b.type === 'paragraphe')

  return (
    <article lang="fr" className="mx-auto max-w-5xl bg-[#faf7f0] px-5 py-5 font-serif text-stone-900 shadow-2xl ring-1 ring-stone-300 sm:px-10 sm:py-8">
      {/* Bandeau supérieur */}
      <div className="flex items-center justify-between gap-3 border-b border-stone-400 pb-2 font-sans text-[11px] tracking-[0.18em] text-stone-600 uppercase">
        <span>N° {numero}</span>
        <span className="hidden text-center sm:inline">{a.date_fictive}</span>
        <span className="flex items-center gap-3">
          {prix && <span className="font-bold text-stone-800">{prix.texte}</span>}
          <CodeBarres graine={graine} />
        </span>
      </div>

      {/* Titre du journal */}
      <header className="border-b-4 border-double border-stone-900 py-3 text-center sm:py-5">
        <h1 className="text-5xl leading-none font-black tracking-tight text-balance sm:text-7xl">{a.media}</h1>
      </header>
      <div className="flex items-center justify-between border-b border-stone-900 py-1.5 font-sans text-[11px] tracking-[0.18em] text-stone-700 uppercase">
        <span>{a.date_fictive}</span>
        <span className="hidden sm:inline">Édition locale</span>
        <span>À la une</span>
      </div>

      {/* Article principal */}
      <section className="pt-5">
        {surtitres.map((s, i) => (
          <p key={i} className="font-sans text-xs font-bold tracking-[0.25em] text-red-700 uppercase">
            {s.texte}
          </p>
        ))}
        <h2 className="mt-2 text-4xl leading-[0.95] font-black tracking-tight text-balance sm:text-6xl">{a.titre}</h2>
        {chapo && (
          <p className="mt-4 border-b border-stone-300 pb-4 text-lg leading-snug font-semibold text-stone-800 sm:text-xl">
            {chapo.texte}
          </p>
        )}
        <figure className="mt-5">
          <img
            src={photoUne}
            alt="Séance collective de sport santé dans une salle en bois lumineuse ouverte sur la ville, avec des participants de tous âges assis en cercle autour d'une éducatrice."
            className="w-full border border-stone-300 object-cover grayscale-[15%] sepia-[10%]"
            loading="lazy"
          />
          <figcaption className="mt-1.5 flex flex-wrap justify-between gap-2 border-b border-stone-300 pb-2 font-sans text-[11px] text-stone-600">
            <span>Séance collective de sport santé, un jeudi de novembre 2040.</span>
            <span className="italic">Illustration générée par IA (Gemini)</span>
          </figcaption>
        </figure>
      </section>

      <div className={`mt-5 grid gap-6 ${lateral.length > 0 ? 'lg:grid-cols-[minmax(0,1fr)_17rem]' : ''}`}>
        <div
          className={`gap-7 text-justify text-[15px] leading-relaxed hyphens-auto [column-rule:1px_solid_#d6d3d1] ${
            lateral.length > 0 ? 'columns-1 sm:columns-2' : 'columns-1 sm:columns-2 lg:columns-3'
          }`}
        >
          {corps.map((b, i) => (
            <BlocPresse key={i} bloc={b} lettrine={i === premierParagraphe} />
          ))}
        </div>
        {lateral.length > 0 && (
          <aside className="space-y-4 lg:border-l lg:border-stone-300 lg:pl-6">
            {lateral.map((b, i) => (
              <EncadrePresse key={i} bloc={b} />
            ))}
          </aside>
        )}
      </div>

      {mentions.length > 0 && (
        <footer className="mt-6 space-y-1 border-t border-stone-900 pt-2 font-sans text-[11px] text-stone-600">
          {mentions.map((m, i) => (
            <p key={i}>{m.texte}</p>
          ))}
        </footer>
      )}
    </article>
  )
}

// ---------------------------------------------------------------------------
// Publicité
// ---------------------------------------------------------------------------

function Publicite({ a }: { a: Artefact }) {
  const prix = de(a.blocs, 'prix')
  const mentions = de(a.blocs, 'mention')
  const contenu = a.blocs.filter((b) => b.type !== 'prix' && b.type !== 'mention')

  return (
    <article className="relative mx-auto max-w-2xl overflow-hidden rounded-3xl bg-linear-to-br from-rose-600 via-fuchsia-700 to-indigo-800 p-7 font-sans text-white shadow-2xl sm:p-10">
      <svg viewBox="0 0 400 400" className="pointer-events-none absolute -top-24 -right-24 size-96 opacity-30" aria-hidden="true">
        <circle cx={200} cy={200} r={190} fill="none" stroke="#ffffff" strokeWidth={2} />
        <circle cx={200} cy={200} r={140} fill="none" stroke="#ffffff" strokeWidth={2} />
        <circle cx={200} cy={200} r={90} fill="#fde047" opacity={0.6} />
      </svg>
      <svg viewBox="0 0 400 200" className="pointer-events-none absolute -bottom-10 -left-10 w-[120%] opacity-20" aria-hidden="true">
        <path d="M0 120 Q100 60 200 120 T400 120 V200 H0 Z" fill="#ffffff" />
      </svg>

      <div className="relative">
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm font-black tracking-[0.3em] uppercase">{a.media}</p>
          <p className="text-xs font-medium text-white/85">{a.date_fictive}</p>
        </div>

        <h2 className="mt-8 text-5xl leading-[0.95] font-black tracking-tight text-balance sm:text-6xl">{a.titre}</h2>

        <div className="mt-6 space-y-4">
          {contenu.map((b, i) => {
            switch (b.type) {
              case 'surtitre':
                return (
                  <p key={i} className="inline-block rounded-full bg-white/15 px-3 py-1 text-xs font-bold tracking-widest uppercase ring-1 ring-white/30">
                    {b.texte}
                  </p>
                )
              case 'titre':
                return (
                  <h3 key={i} className="text-2xl leading-tight font-extrabold">
                    {b.texte}
                  </h3>
                )
              case 'chapo':
                return (
                  <p key={i} className="text-xl leading-snug font-semibold text-white">
                    {b.texte}
                  </p>
                )
              case 'citation':
                return (
                  <blockquote key={i} className="font-serif text-2xl leading-snug italic">
                    « {sansGuillemets(b.texte)} »
                  </blockquote>
                )
              case 'liste':
                return (
                  <ul key={i} className="space-y-2">
                    {lignesListe(b.texte).map((l, j) => (
                      <li key={j} className="flex items-start gap-2.5 text-base font-medium">
                        <IconeCoche className="mt-0.5 text-yellow-200" />
                        <span>{l}</span>
                      </li>
                    ))}
                  </ul>
                )
              case 'encadre':
                return (
                  <div key={i} className="rounded-2xl bg-white/15 p-4 text-base ring-1 ring-white/30 backdrop-blur">
                    {b.texte}
                  </div>
                )
              default:
                return (
                  <p key={i} className="text-base leading-relaxed text-white/90">
                    {b.texte}
                  </p>
                )
            }
          })}
        </div>

        {prix.length > 0 && (
          <div className="mt-8 flex flex-wrap items-center gap-4">
            {prix.map((p, i) => (
              <span
                key={i}
                className="inline-flex -rotate-3 items-center rounded-2xl bg-yellow-300 px-5 py-3 text-3xl font-black text-fuchsia-950 shadow-lg"
              >
                {p.texte}
              </span>
            ))}
          </div>
        )}

        {mentions.length > 0 && (
          <div className="mt-8 space-y-1 border-t border-white/25 pt-3 text-[11px] leading-snug text-white/85">
            {mentions.map((m, i) => (
              <p key={i}>{m.texte}</p>
            ))}
          </div>
        )}
      </div>
    </article>
  )
}

// ---------------------------------------------------------------------------
// Fiche produit
// ---------------------------------------------------------------------------

function VisuelProduit({ graine }: { graine: number }) {
  const teinte = graine % 360
  return (
    <svg viewBox="0 0 200 200" className="size-3/5" aria-hidden="true">
      <defs>
        <linearGradient id={`produit-${graine}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={`hsl(${teinte} 70% 62%)`} />
          <stop offset="1" stopColor={`hsl(${(teinte + 50) % 360} 65% 38%)`} />
        </linearGradient>
      </defs>
      <ellipse cx={100} cy={178} rx={62} ry={8} fill="#0f172a" opacity={0.12} />
      <rect x={48} y={30} width={104} height={140} rx={28} fill={`url(#produit-${graine})`} />
      <rect x={62} y={46} width={76} height={60} rx={14} fill="#ffffff" opacity={0.25} />
      <circle cx={100} cy={136} r={14} fill="#ffffff" opacity={0.35} />
      <path d="M66 52 Q80 44 96 48" stroke="#ffffff" strokeWidth={4} strokeLinecap="round" fill="none" opacity={0.6} />
    </svg>
  )
}

function FicheProduit({ a }: { a: Artefact }) {
  const surtitre = de(a.blocs, 'surtitre')[0]
  const chapos = de(a.blocs, 'chapo')
  const prix = de(a.blocs, 'prix')
  const listes = de(a.blocs, 'liste')
  const encadres = de(a.blocs, 'encadre')
  const description = de(a.blocs, 'paragraphe', 'titre', 'citation')
  const mentions = de(a.blocs, 'mention')
  const graine = empreinte(a.titre + a.media)
  const an = annee(a.date_fictive)

  return (
    <article className="mx-auto max-w-5xl overflow-hidden rounded-2xl border border-slate-200 bg-white font-sans text-slate-800 shadow-xl">
      <div className="flex items-center gap-4 bg-slate-900 px-5 py-3 text-white">
        <p className="text-lg font-extrabold tracking-tight">{a.media}</p>
        <div className="hidden flex-1 items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-sm text-white/70 sm:flex">
          <svg viewBox="0 0 16 16" className="size-4" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={1.8}>
            <circle cx={7} cy={7} r={4.5} />
            <path d="M10.5 10.5 L14 14" strokeLinecap="round" />
          </svg>
          Rechercher un produit
        </div>
        <svg viewBox="0 0 24 24" className="ml-auto size-6 sm:ml-0" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={1.8}>
          <path d="M3 4h2l2.4 11h10.2L20 7H6.2" strokeLinejoin="round" strokeLinecap="round" />
          <circle cx={9} cy={19} r={1.5} />
          <circle cx={17} cy={19} r={1.5} />
        </svg>
      </div>

      <nav className="border-b border-slate-100 px-5 py-2.5 text-xs text-slate-500" aria-label="Fil d'Ariane fictif">
        Accueil <span aria-hidden="true">›</span> {surtitre?.texte ?? 'Catalogue'} <span aria-hidden="true">›</span>{' '}
        <span className="text-slate-700">{a.titre}</span>
      </nav>

      <div className="grid gap-8 p-5 sm:p-8 md:grid-cols-2">
        <div className="relative flex aspect-square items-center justify-center rounded-2xl bg-linear-to-br from-slate-50 to-indigo-100">
          {an && (
            <span className="absolute top-4 left-4 rounded-full bg-indigo-600 px-3 py-1 text-xs font-bold text-white">
              Nouveauté {an}
            </span>
          )}
          <VisuelProduit graine={graine} />
        </div>

        <div className="flex flex-col">
          {surtitre && <p className="text-xs font-semibold tracking-wider text-indigo-700 uppercase">{surtitre.texte}</p>}
          <h2 className="mt-1 text-3xl leading-tight font-bold text-balance text-slate-900">{a.titre}</h2>
          {chapos.map((c, i) => (
            <p key={i} className="mt-3 text-base leading-relaxed text-slate-600">
              {c.texte}
            </p>
          ))}

          {prix.length > 0 && (
            <div className="mt-5 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <p className="text-4xl font-extrabold tracking-tight text-slate-900">{prix[0].texte}</p>
              {prix.slice(1).map((p, i) => (
                <p key={i} className="text-sm text-slate-500">
                  {p.texte}
                </p>
              ))}
            </div>
          )}

          <div className="mt-5 flex gap-3">
            <span className="flex-1 rounded-xl bg-indigo-600 px-5 py-3 text-center text-sm font-bold text-white shadow-sm">
              Ajouter au panier
            </span>
            <span className="rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-700" aria-hidden="true">
              ♡
            </span>
          </div>

          {listes.map((l, i) => (
            <ul key={i} className="mt-6 space-y-2">
              {lignesListe(l.texte).map((ligne, j) => (
                <li key={j} className="flex items-start gap-2.5 text-sm text-slate-700">
                  <IconeCoche className="mt-0.5 text-emerald-600" />
                  <span>{ligne}</span>
                </li>
              ))}
            </ul>
          ))}

          {encadres.map((e, i) => (
            <div key={i} className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-relaxed text-emerald-900">
              {e.texte}
            </div>
          ))}
        </div>
      </div>

      {description.length > 0 && (
        <section className="border-t border-slate-100 px-5 py-6 sm:px-8">
          <h3 className="mb-3 text-lg font-bold text-slate-900">Description</h3>
          <div className="max-w-3xl space-y-3 text-sm leading-relaxed text-slate-700">
            {description.map((b, i) =>
              b.type === 'titre' ? (
                <h4 key={i} className="pt-2 font-semibold text-slate-900">
                  {b.texte}
                </h4>
              ) : b.type === 'citation' ? (
                <blockquote key={i} className="rounded-xl bg-slate-50 p-4 text-slate-800 italic">
                  « {sansGuillemets(b.texte)} »
                </blockquote>
              ) : (
                <p key={i}>{b.texte}</p>
              ),
            )}
          </div>
        </section>
      )}

      <footer className="space-y-1 border-t border-slate-100 bg-slate-50 px-5 py-3 text-[11px] text-slate-500 sm:px-8">
        <p>Fiche mise en ligne le {a.date_fictive}</p>
        {mentions.map((m, i) => (
          <p key={i}>{m.texte}</p>
        ))}
      </footer>
    </article>
  )
}

// ---------------------------------------------------------------------------
// Avis client
// ---------------------------------------------------------------------------

function Etoiles({ note }: { note: number }) {
  return (
    <div className="flex items-center gap-0.5" role="img" aria-label={`Note : ${note} sur 5`}>
      {[0, 1, 2, 3, 4].map((i) => (
        <svg key={i} viewBox="0 0 20 20" className="size-5" aria-hidden="true">
          <path
            d="M10 1.5 L12.6 7 L18.5 7.6 L14 11.6 L15.3 17.5 L10 14.5 L4.7 17.5 L6 11.6 L1.5 7.6 L7.4 7 Z"
            fill={i < Math.round(note) ? '#f59e0b' : '#e2e8f0'}
          />
        </svg>
      ))}
    </div>
  )
}

function AvisClient({ a }: { a: Artefact }) {
  const tout = [a.titre, ...a.blocs.map((b) => b.texte)].join(' ')
  const m = tout.match(/(\d(?:[.,]\d)?)\s*(?:\/|sur)\s*5\b/)
  const note = m ? Math.min(5, Math.max(0, Number(m[1].replace(',', '.')))) : 5
  const auteur = de(a.blocs, 'surtitre')[0]?.texte
  const contenu = a.blocs.filter((b) => b.type !== 'surtitre' && b.type !== 'mention')
  const mentions = de(a.blocs, 'mention')
  const utiles = 3 + (empreinte(a.titre) % 40)

  return (
    <article className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 font-sans text-slate-800 shadow-xl sm:p-8">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <p className="flex items-center gap-2 text-sm font-bold text-slate-900">
          <span className="flex size-7 items-center justify-center rounded-lg bg-emerald-600 text-xs font-black text-white">
            {initiales(a.media)}
          </span>
          {a.media}
        </p>
        <p className="text-xs text-slate-500">Publié le {a.date_fictive}</p>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <span className="flex size-11 items-center justify-center rounded-full bg-linear-to-br from-amber-200 to-rose-300 text-sm font-bold text-rose-950">
          {auteur ? initiales(auteur) : (
            <svg viewBox="0 0 20 20" className="size-5" aria-hidden="true">
              <circle cx={10} cy={7} r={3.5} fill="currentColor" />
              <path d="M3.5 17 Q10 9.5 16.5 17 Z" fill="currentColor" />
            </svg>
          )}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">{auteur ?? 'Client'}</p>
          <p className="flex items-center gap-1 text-xs font-medium text-emerald-700">
            <IconeCoche className="size-3.5" />
            Avis vérifié
          </p>
        </div>
      </div>

      <div className="mt-4">
        <Etoiles note={note} />
      </div>
      <h2 className="mt-2 text-xl leading-snug font-bold text-slate-900">{a.titre}</h2>

      <div className="mt-3 space-y-3 text-[15px] leading-relaxed">
        {contenu.map((b, i) => {
          switch (b.type) {
            case 'titre':
              return (
                <h3 key={i} className="pt-1 font-semibold text-slate-900">
                  {b.texte}
                </h3>
              )
            case 'chapo':
              return (
                <p key={i} className="font-semibold text-slate-800">
                  {b.texte}
                </p>
              )
            case 'citation':
              return (
                <blockquote key={i} className="rounded-xl border-l-4 border-amber-400 bg-amber-50 px-4 py-3 text-slate-800 italic">
                  « {sansGuillemets(b.texte)} »
                </blockquote>
              )
            case 'liste':
              return (
                <ul key={i} className="space-y-1.5">
                  {lignesListe(b.texte).map((l, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm">
                      <IconeCoche className="mt-0.5 text-emerald-600" />
                      <span>{l}</span>
                    </li>
                  ))}
                </ul>
              )
            case 'encadre':
              return (
                <div key={i} className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                  {b.texte}
                </div>
              )
            case 'prix':
              return (
                <p key={i} className="inline-block rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                  Prix : {b.texte}
                </p>
              )
            default:
              return (
                <p key={i} className="text-slate-700">
                  {b.texte}
                </p>
              )
          }
        })}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4 text-xs text-slate-500">
        <span>Cet avis vous a-t-il été utile ?</span>
        <span className="rounded-full border border-slate-200 px-3 py-1 font-medium text-slate-700">Oui ({utiles})</span>
        <span className="rounded-full border border-slate-200 px-3 py-1 font-medium text-slate-700">Non</span>
      </div>
      {mentions.length > 0 && (
        <div className="mt-3 space-y-1 text-[11px] text-slate-500">
          {mentions.map((mm, i) => (
            <p key={i}>{mm.texte}</p>
          ))}
        </div>
      )}
    </article>
  )
}

// ---------------------------------------------------------------------------
// Offre d'emploi
// ---------------------------------------------------------------------------

function OffreEmploi({ a }: { a: Artefact }) {
  const etiquettes = de(a.blocs, 'surtitre').flatMap((s) =>
    s.texte
      .split(/\s*[·|•]\s*/)
      .map((t) => t.trim())
      .filter(Boolean),
  )
  const prix = de(a.blocs, 'prix')
  const mentions = de(a.blocs, 'mention')
  const contenu = a.blocs.filter((b) => b.type !== 'surtitre' && b.type !== 'prix' && b.type !== 'mention')

  return (
    <article className="mx-auto max-w-3xl overflow-hidden rounded-2xl border border-slate-200 bg-white font-sans text-slate-800 shadow-xl">
      <div className="relative h-28 bg-linear-to-r from-teal-600 to-sky-700">
        <svg viewBox="0 0 400 112" className="absolute inset-0 h-full w-full opacity-25" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 80 Q80 40 160 70 T320 60 T400 50" fill="none" stroke="#ffffff" strokeWidth={2} />
          <path d="M0 95 Q100 60 200 90 T400 75" fill="none" stroke="#ffffff" strokeWidth={2} />
        </svg>
      </div>
      <div className="px-6 sm:px-8">
        <div className="-mt-10 flex size-20 items-center justify-center rounded-2xl bg-white text-2xl font-black text-teal-700 shadow-md ring-1 ring-slate-200">
          {initiales(a.media)}
        </div>
        <p className="mt-3 text-sm font-semibold text-slate-600">{a.media}</p>
        <h2 className="mt-1 text-3xl leading-tight font-bold text-balance text-slate-900">{a.titre}</h2>

        <div className="mt-4 flex flex-wrap gap-2 text-xs font-medium">
          {etiquettes.map((t, i) => (
            <span key={i} className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
              {t}
            </span>
          ))}
          {prix.map((p, i) => (
            <span key={i} className="rounded-full bg-emerald-100 px-3 py-1 font-semibold text-emerald-800">
              {p.texte}
            </span>
          ))}
          <span className="rounded-full border border-slate-200 px-3 py-1 text-slate-500">Publiée le {a.date_fictive}</span>
        </div>

        <div className="mt-5 flex gap-3">
          <span className="rounded-xl bg-teal-700 px-6 py-2.5 text-sm font-bold text-white shadow-sm">Postuler</span>
          <span className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700">Sauvegarder</span>
        </div>
      </div>

      <div className="mt-6 space-y-4 border-t border-slate-100 px-6 py-6 text-[15px] leading-relaxed sm:px-8">
        {contenu.map((b, i) => {
          switch (b.type) {
            case 'titre':
              return (
                <h3 key={i} className="flex items-center gap-2 pt-2 text-base font-bold text-slate-900">
                  <span className="inline-block h-4 w-1 rounded-full bg-teal-600" aria-hidden="true" />
                  {b.texte}
                </h3>
              )
            case 'chapo':
              return (
                <p key={i} className="text-lg leading-snug text-slate-800">
                  {b.texte}
                </p>
              )
            case 'liste':
              return (
                <ul key={i} className="space-y-2">
                  {lignesListe(b.texte).map((l, j) => (
                    <li key={j} className="flex items-start gap-2.5 text-slate-700">
                      <IconeCoche className="mt-1 text-teal-700" />
                      <span>{l}</span>
                    </li>
                  ))}
                </ul>
              )
            case 'encadre':
              return (
                <div key={i} className="rounded-xl bg-teal-50 p-4 text-slate-800 ring-1 ring-teal-100">
                  {b.texte}
                </div>
              )
            case 'citation':
              return (
                <blockquote key={i} className="border-l-4 border-teal-600 pl-4 text-slate-800 italic">
                  « {sansGuillemets(b.texte)} »
                </blockquote>
              )
            default:
              return (
                <p key={i} className="text-slate-700">
                  {b.texte}
                </p>
              )
          }
        })}
        {mentions.length > 0 && (
          <div className="space-y-1 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
            {mentions.map((m, i) => (
              <p key={i}>{m.texte}</p>
            ))}
          </div>
        )}
      </div>
    </article>
  )
}

// ---------------------------------------------------------------------------
// Notification d'application
// ---------------------------------------------------------------------------

interface Notif {
  etiquette?: string
  titre?: string
  corps: Bloc[]
}

function regrouperNotifications(a: Artefact): { notifs: Notif[]; mentions: Bloc[] } {
  const notifs: Notif[] = [{ titre: a.titre, corps: [] }]
  const mentions: Bloc[] = []
  for (const b of a.blocs) {
    const courante = notifs[notifs.length - 1]
    if (b.type === 'mention') mentions.push(b)
    else if (b.type === 'surtitre') {
      if (!courante.etiquette && courante.corps.length === 0) courante.etiquette = b.texte
      else notifs.push({ etiquette: b.texte, corps: [] })
    } else if (b.type === 'titre') {
      if (!courante.titre && courante.corps.length === 0) courante.titre = b.texte
      else notifs.push({ titre: b.texte, corps: [] })
    } else courante.corps.push(b)
  }
  return { notifs, mentions }
}

function CorpsNotification({ bloc }: { bloc: Bloc }): ReactNode {
  switch (bloc.type) {
    case 'liste':
      return (
        <ul className="mt-1 space-y-0.5">
          {lignesListe(bloc.texte).map((l, i) => (
            <li key={i} className="flex gap-1.5">
              <span aria-hidden="true">·</span>
              <span>{l}</span>
            </li>
          ))}
        </ul>
      )
    case 'citation':
      return <p className="mt-1 italic">« {sansGuillemets(bloc.texte)} »</p>
    case 'prix':
      return <p className="mt-1 font-bold text-slate-900">{bloc.texte}</p>
    case 'encadre':
      return <p className="mt-1.5 rounded-lg bg-slate-900/5 px-2 py-1">{bloc.texte}</p>
    case 'chapo':
      return <p className="mt-0.5 font-medium text-slate-800">{bloc.texte}</p>
    default:
      return <p className="mt-0.5">{bloc.texte}</p>
  }
}

function Notification({ a }: { a: Artefact }) {
  const { notifs, mentions } = regrouperNotifications(a)
  const graine = empreinte(a.media + a.date_fictive)
  const heure = `${String(7 + (graine % 3)).padStart(2, '0')}:${String((graine >>> 3) % 60).padStart(2, '0')}`

  return (
    <div className="mx-auto w-full max-w-[360px]">
      <div className="rounded-[3rem] bg-slate-900 p-3 shadow-2xl ring-1 ring-slate-700">
        <div className="relative min-h-[640px] overflow-hidden rounded-[2.4rem] bg-linear-to-b from-indigo-950 via-purple-900 to-rose-700 px-3 pt-3 pb-8 font-sans text-white">
          <svg viewBox="0 0 300 600" className="pointer-events-none absolute inset-0 h-full w-full opacity-40" preserveAspectRatio="none" aria-hidden="true">
            <circle cx={240} cy={120} r={90} fill="#f472b6" opacity={0.35} />
            <circle cx={40} cy={420} r={120} fill="#818cf8" opacity={0.3} />
            <path d="M0 470 Q75 420 150 460 T300 440 V600 H0 Z" fill="#fb923c" opacity={0.35} />
          </svg>

          {/* Barre d'état */}
          <div className="relative flex items-center justify-between px-4 pt-1 text-xs font-semibold">
            <span>{heure}</span>
            <span className="absolute top-0 left-1/2 h-7 w-24 -translate-x-1/2 rounded-full bg-black" aria-hidden="true" />
            <span className="flex items-center gap-1.5" aria-hidden="true">
              <svg viewBox="0 0 18 12" className="h-3 w-4">
                {[0, 1, 2, 3].map((i) => (
                  <rect key={i} x={i * 4.5} y={9 - i * 3} width={3} height={3 + i * 3} rx={0.8} fill="#ffffff" />
                ))}
              </svg>
              <svg viewBox="0 0 26 12" className="h-3 w-6">
                <rect x={0.5} y={0.5} width={22} height={11} rx={3} fill="none" stroke="#ffffff" opacity={0.6} />
                <rect x={2} y={2} width={16} height={8} rx={1.8} fill="#ffffff" />
                <rect x={23.5} y={4} width={2} height={4} rx={1} fill="#ffffff" opacity={0.6} />
              </svg>
            </span>
          </div>

          {/* Écran verrouillé */}
          <div className="relative mt-10 text-center">
            <p className="text-sm font-medium text-white/90">{a.date_fictive}</p>
            <p className="text-7xl leading-none font-extralight tracking-tight">{heure}</p>
          </div>

          <div className="relative mt-8 space-y-2.5">
            {notifs.map((n, i) => (
              <div key={i} className="rounded-3xl bg-white/85 p-3 text-slate-900 shadow-lg ring-1 ring-white/40 backdrop-blur-xl">
                <div className="flex items-center gap-2 text-[11px] text-slate-600">
                  <span className="flex size-5 items-center justify-center rounded-md bg-linear-to-br from-indigo-500 to-rose-500 text-[9px] font-black text-white">
                    {initiales(a.media).slice(0, 1)}
                  </span>
                  <span className="truncate font-semibold tracking-wide uppercase">{n.etiquette ?? a.media}</span>
                  <span className="ml-auto shrink-0">{i === 0 ? 'maintenant' : `il y a ${i * 7 + (graine % 5)} min`}</span>
                </div>
                <div className="mt-1.5 pl-7 text-[13px] leading-snug text-slate-700">
                  {n.titre && <p className="font-semibold text-slate-900">{n.titre}</p>}
                  {n.corps.map((b, j) => (
                    <CorpsNotification key={j} bloc={b} />
                  ))}
                </div>
              </div>
            ))}
          </div>

          {mentions.length > 0 && (
            <div className="relative mt-6 space-y-1 px-3 text-center text-[10px] leading-snug text-white/90">
              {mentions.map((m, i) => (
                <p key={i}>{m.texte}</p>
              ))}
            </div>
          )}

          <span className="absolute bottom-2 left-1/2 h-1 w-28 -translate-x-1/2 rounded-full bg-white/80" aria-hidden="true" />
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Composant principal
// ---------------------------------------------------------------------------

export function ArtefactFiction({ artefact }: Props) {
  let rendu: ReactNode
  switch (artefact.format) {
    case 'publicite':
      rendu = <Publicite a={artefact} />
      break
    case 'fiche_produit':
      rendu = <FicheProduit a={artefact} />
      break
    case 'avis_client':
      rendu = <AvisClient a={artefact} />
      break
    case 'offre_emploi':
      rendu = <OffreEmploi a={artefact} />
      break
    case 'notification':
      rendu = <Notification a={artefact} />
      break
    default:
      rendu = <UneDePresse a={artefact} />
  }

  return (
    <div className="w-full">
      {rendu}
      <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-slate-500">
        <svg viewBox="0 0 16 16" className="size-3.5" aria-hidden="true">
          <path d="M8 1 L9.4 6.6 L15 8 L9.4 9.4 L8 15 L6.6 9.4 L1 8 L6.6 6.6 Z" fill="currentColor" />
        </svg>
        Fiction prospective générée par IA
      </p>
    </div>
  )
}
