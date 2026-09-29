import { useEffect, useState } from 'react'
import { api } from '../api'
import { ReglagesRun } from '../components/ReglagesRun'
import { Alerte, Bouton, Carte, Chargement, Titre } from '../components/ui'
import { ETAPES } from '../etapes'
import type { Mode, ResumeSession, SaisieProjet } from '../types'

const VIDE: SaisieProjet = {
  description: '',
  thematique: '',
  pays: 'France',
  lieu: '',
  horizon: 2040,
  ambition: '',
}

export function Accueil({ horsLigne, onOuvrir }: { horsLigne: boolean; onOuvrir: (id: string) => void }) {
  const [saisie, setSaisie] = useState<SaisieProjet>(VIDE)
  const [sessions, setSessions] = useState<ResumeSession[] | null>(null)
  const [envoi, setEnvoi] = useState(false)
  const [mode, setMode] = useState<Mode>('complet')
  const [modele, setModele] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)

  useEffect(() => {
    api.sessions().then(setSessions).catch((e) => setErreur(e.message))
  }, [])

  const maj = (partiel: Partial<SaisieProjet>) => setSaisie((s) => ({ ...s, ...partiel }))
  const longueur = saisie.description.length
  const valide = longueur >= 20 && longueur <= 2000 && saisie.thematique.trim() && saisie.pays.trim()

  const creer = async () => {
    setEnvoi(true)
    setErreur(null)
    try {
      const session = await api.creerSession({ ...saisie, lieu: saisie.lieu?.trim() || null }, mode, modele)
      onOuvrir(session.id)
    } catch (e) {
      setErreur((e as Error).message)
      setEnvoi(false)
    }
  }

  const champ = 'mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none'

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 via-white to-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="mb-8">
          <p className="text-sm font-semibold tracking-widest text-indigo-600 uppercase">Hack The Vibe</p>
          <h1 className="mt-1 text-4xl font-bold text-slate-900">Prospective 2040</h1>
          <p className="mt-2 max-w-2xl text-lg text-slate-600">
            Une première lecture prospective de votre projet, structurée, sourcée et validée pas à
            pas : <strong>30 minutes au lieu de 3 à 6 mois</strong>.
          </p>
          {horsLigne && (
            <div className="mt-4 max-w-2xl">
              <Alerte ton="info">
                Mode hors ligne (DEMO=true) : la session préenregistrée « sport santé seniors à
                Nantes » est rejouée sans aucun appel réseau.
              </Alerte>
            </div>
          )}
        </header>

        <div className="grid gap-6 lg:grid-cols-5">
          <Carte className="p-6 lg:col-span-3">
            <div className="mb-4 flex items-center justify-between">
              <Titre>Étape 0 : décrivez votre projet</Titre>
              <Bouton
                variante="discret"
                onClick={() => api.saisieDemo().then(setSaisie).catch((e) => setErreur(e.message))}
              >
                Pré-remplir avec le scénario de démo
              </Bouton>
            </div>
            <label className="block text-sm font-medium text-slate-700">
              Votre projet, en langage naturel
              <textarea
                className={`${champ} min-h-32`}
                rows={6}
                placeholder="Ex. : Je veux créer un service de… pour… sur le territoire de… Mon intuition est que…"
                value={saisie.description}
                onChange={(e) => maj({ description: e.target.value })}
              />
            </label>
            <p className={`text-right text-xs ${longueur > 2000 ? 'text-rose-600' : 'text-slate-400'}`}>
              {longueur} / 2000 caractères {longueur < 200 && '(200 conseillés pour un contexte riche)'}
            </p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <label className="text-sm font-medium text-slate-700">
                Thématique business
                <input
                  className={champ}
                  placeholder="sport, santé, alimentation, mobilité…"
                  value={saisie.thematique}
                  onChange={(e) => maj({ thematique: e.target.value })}
                />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Horizon
                <input
                  type="number"
                  className={champ}
                  min={2030}
                  max={2050}
                  value={saisie.horizon}
                  onChange={(e) => maj({ horizon: Number(e.target.value) })}
                />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Pays <span className="text-rose-600">*</span>
                <input className={champ} value={saisie.pays} onChange={(e) => maj({ pays: e.target.value })} />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Code postal ou ville <span className="text-slate-400">(facultatif)</span>
                <input
                  className={champ}
                  placeholder="44000"
                  value={saisie.lieu ?? ''}
                  onChange={(e) => maj({ lieu: e.target.value })}
                />
              </label>
            </div>
            <label className="mt-3 block text-sm font-medium text-slate-700">
              Ambition et contraintes <span className="text-slate-400">(budget, taille visée, valeurs)</span>
              <textarea
                className={champ}
                rows={2}
                value={saisie.ambition}
                onChange={(e) => maj({ ambition: e.target.value })}
              />
            </label>
            {erreur && (
              <div className="mt-3">
                <Alerte>{erreur}</Alerte>
              </div>
            )}
            {!horsLigne && (
              <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
                <ReglagesRun
                  mode={mode}
                  modele={modele}
                  onChange={(r) => {
                    if (r.mode) setMode(r.mode)
                    if (r.modele !== undefined) setModele(r.modele)
                  }}
                />
                <span className="text-xs text-slate-500">
                  {mode === 'demo'
                    ? 'Parcours complet en 5 minutes, livrables resserrés.'
                    : 'Parcours complet, livrables détaillés.'}
                </span>
              </div>
            )}
            <Bouton variante="principal" className="mt-4 w-full !py-2.5" disabled={!valide || envoi} onClick={creer}>
              {envoi ? 'Création de la session…' : 'Lancer la prospective →'}
            </Bouton>
          </Carte>

          <div className="space-y-4 lg:col-span-2">
            <Carte>
              <Titre>Reprendre une session</Titre>
              {sessions === null ? (
                <Chargement texte="Lecture des archives…" />
              ) : sessions.length === 0 ? (
                <p className="text-sm text-slate-500">Aucune session archivée pour l'instant.</p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {sessions.map((s) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        onClick={() => onOuvrir(s.id)}
                        className="w-full py-2 text-left hover:bg-slate-50"
                      >
                        <p className="text-sm font-medium text-slate-800">
                          {s.thematique} · {s.lieu}
                        </p>
                        <p className="line-clamp-1 text-xs text-slate-500">{s.description}</p>
                        <p className="mt-0.5 text-xs text-slate-400">
                          {new Date(s.cree_le).toLocaleDateString('fr-FR')} · {s.nb_validees}/9 étapes
                          validées · reprise à « {ETAPES[s.etape_courante]?.court} »
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Carte>
            <Carte>
              <Titre>Le parcours en 9 étapes</Titre>
              <ol className="space-y-1 text-sm text-slate-700">
                {ETAPES.map((e, i) => (
                  <li key={i}>
                    <span className="font-mono text-xs text-slate-400">{i}</span> {e.titre}
                  </li>
                ))}
              </ol>
              <p className="mt-3 text-xs text-slate-500">
                Chaque étape se termine par votre validation et produit un fichier Markdown archivé
                localement.
              </p>
            </Carte>
          </div>
        </div>
      </div>
    </div>
  )
}
