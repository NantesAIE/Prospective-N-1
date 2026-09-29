import { useMemo, useState } from 'react'
import { Alerte, BadgeAxe, Bouton, Carte, LienSource, Titre } from '../components/ui'
import { LIBELLES_AXES, type Axe, type LivrableCollecte, type Signal } from '../types'
import type { VueEtapeProps } from './commun'

const AXES = Object.keys(LIBELLES_AXES) as Axe[]

function FormulaireAjout({ onAjouter }: { onAjouter: (s: Omit<Signal, 'id'>) => void }) {
  const [titre, setTitre] = useState('')
  const [resume, setResume] = useState('')
  const [axe, setAxe] = useState<Axe>('S')
  const [source, setSource] = useState('')
  const [url, setUrl] = useState('')
  const ajouter = () => {
    onAjouter({
      titre,
      resume,
      axe,
      source: source || null,
      url: url || null,
      date: new Date().toISOString().slice(0, 10),
      niveau: null,
      flux_id: null,
      hypothese_ia: false,
      donnees_demo: false,
      ajout_manuel: true,
      retenu: true,
    })
    setTitre('')
    setResume('')
    setSource('')
    setUrl('')
  }
  const champ = 'rounded-lg border border-slate-300 px-2 py-1.5 text-sm'
  return (
    <Carte>
      <Titre>Ajouter un signal manuellement</Titre>
      <div className="grid gap-2 md:grid-cols-2">
        <input className={champ} placeholder="Titre" value={titre} onChange={(e) => setTitre(e.target.value)} />
        <select className={champ} value={axe} onChange={(e) => setAxe(e.target.value as Axe)}>
          {AXES.map((a) => (
            <option key={a} value={a}>
              {LIBELLES_AXES[a]}
            </option>
          ))}
        </select>
        <input
          className={`${champ} md:col-span-2`}
          placeholder="Résumé en une phrase"
          value={resume}
          onChange={(e) => setResume(e.target.value)}
        />
        <input className={champ} placeholder="Source (facultatif)" value={source} onChange={(e) => setSource(e.target.value)} />
        <input className={champ} placeholder="URL (facultatif)" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <Bouton className="mt-2" variante="principal" disabled={!titre || !resume} onClick={ajouter}>
        Ajouter
      </Bouton>
    </Carte>
  )
}

export function Etape2Collecte({ livrable, modifiable, onChange }: VueEtapeProps<LivrableCollecte>) {
  const [filtreAxe, setFiltreAxe] = useState<Axe | null>(null)
  const [filtreFlux, setFiltreFlux] = useState<string>('')
  const [voirEcartes, setVoirEcartes] = useState(false)

  const flux = useMemo(
    () => [...new Set(livrable.signaux.map((s) => s.flux_id ?? 'hypothese'))].sort(),
    [livrable.signaux],
  )
  const visibles = livrable.signaux.filter(
    (s) =>
      s.retenu !== voirEcartes &&
      (!filtreAxe || s.axe === filtreAxe) &&
      (!filtreFlux || (s.flux_id ?? 'hypothese') === filtreFlux),
  )
  const nbRetenus = livrable.signaux.filter((s) => s.retenu).length

  const basculer = (id: string) =>
    onChange({
      ...livrable,
      signaux: livrable.signaux.map((s) => (s.id === id ? { ...s, retenu: !s.retenu } : s)),
    })
  const ajouter = (s: Omit<Signal, 'id'>) =>
    onChange({
      ...livrable,
      signaux: [...livrable.signaux, { ...s, id: `m${livrable.signaux.length + 1}` }],
    })

  return (
    <div className="space-y-4">
      {livrable.flux_degrades.length > 0 && (
        <Alerte ton="avertissement">
          Données de démonstration utilisées pour : {livrable.flux_degrades.join(', ')} (flux
          injoignables ou en échec).
        </Alerte>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-slate-600">
          <strong>{nbRetenus}</strong> signaux retenus sur {livrable.signaux.length}, extraits de{' '}
          {livrable.nb_elements_bruts} éléments bruts.
        </span>
        <div className="ml-auto flex flex-wrap gap-1">
          <Bouton variante={filtreAxe ? 'discret' : 'secondaire'} onClick={() => setFiltreAxe(null)}>
            Tous
          </Bouton>
          {AXES.map((a) => (
            <Bouton key={a} variante={filtreAxe === a ? 'secondaire' : 'discret'} onClick={() => setFiltreAxe(a)}>
              {LIBELLES_AXES[a]}
            </Bouton>
          ))}
          <select
            className="rounded-lg border border-slate-300 px-2 text-sm"
            value={filtreFlux}
            onChange={(e) => setFiltreFlux(e.target.value)}
            aria-label="Filtrer par source"
          >
            <option value="">Toutes les sources</option>
            {flux.map((f) => (
              <option key={f} value={f}>
                {f === 'hypothese' ? 'Hypothèses IA et ajouts' : f}
              </option>
            ))}
          </select>
          <Bouton variante="discret" onClick={() => setVoirEcartes(!voirEcartes)}>
            {voirEcartes ? 'Voir les retenus' : 'Voir les écartés'}
          </Bouton>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {visibles.map((s) => (
          <Carte key={s.id} className={s.retenu ? '' : 'opacity-60'}>
            <div className="flex items-start justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-slate-400">{s.id}</span>
                <BadgeAxe axe={s.axe} />
              </div>
              {modifiable && (
                <Bouton variante="discret" className="!px-2 !py-0.5 text-xs" onClick={() => basculer(s.id)}>
                  {s.retenu ? 'Écarter' : 'Rétablir'}
                </Bouton>
              )}
            </div>
            <p className="mt-2 font-medium text-slate-900">{s.titre}</p>
            <p className="mt-1 text-sm text-slate-600">{s.resume}</p>
            <div className="mt-2">
              <LienSource
                source={s.source}
                url={s.url}
                date={s.date}
                niveau={s.niveau}
                hypotheseIa={s.hypothese_ia}
                demo={s.donnees_demo}
              />
            </div>
          </Carte>
        ))}
        {!visibles.length && <p className="text-sm text-slate-500">Aucun signal pour ce filtre.</p>}
      </div>
      {modifiable && <FormulaireAjout onAjouter={ajouter} />}
    </div>
  )
}
