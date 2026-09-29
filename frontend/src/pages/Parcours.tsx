import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Assistant } from '../components/Assistant'
import { BarreValidation } from '../components/BarreValidation'
import { PanneauContexte } from '../components/PanneauContexte'
import { ReglagesRun } from '../components/ReglagesRun'
import { Chrono, Stepper } from '../components/Stepper'
import { Alerte, Bouton, Carte, Chargement } from '../components/ui'
import { VisionneuseArchives } from '../components/VisionneuseArchives'
import { ETAPES } from '../etapes'
import type { Options } from '../etapes/commun'
import type { LivrableCollecte, Mode, ResultatSource, Session, Suggestion } from '../types'

// Étapes lancées automatiquement : rapides et sans réglage préalable
const LANCEMENT_AUTO = new Set([0, 1])

function Attente({ message, debut, progression }: { message: string; debut: number; progression: string | null }) {
  const [secondes, setSecondes] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setSecondes(Math.round((Date.now() - debut) / 1000)), 1000)
    return () => clearInterval(t)
  }, [debut])
  return (
    <Carte className="border-indigo-200 bg-indigo-50/50">
      <Chargement texte={`${message} (${secondes} s)`} />
      {progression && <p className="mt-2 text-sm text-indigo-800">{progression}</p>}
      <p className="mt-2 text-xs text-slate-500">
        La passerelle peut mettre plusieurs minutes avant de répondre sur les étapes d'analyse.
        Les résultats partiels sont conservés en cas d'interruption.
      </p>
    </Carte>
  )
}

export function Parcours({
  sessionId,
  horsLigne,
  onAccueil,
}: {
  sessionId: string
  horsLigne: boolean
  onAccueil: () => void
}) {
  const [session, setSession] = useState<Session | null>(null)
  const [affichee, setAffichee] = useState(0)
  const [brouillon, setBrouillon] = useState<unknown>(null)
  const [options, setOptions] = useState<Options>({})
  const [occupe, setOccupe] = useState<{ message: string; debut: number; etape: number } | null>(null)
  const [progression, setProgression] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  const [edition, setEdition] = useState(false)
  const [contexteOuvert, setContexteOuvert] = useState(true)
  const [assistantOuvert, setAssistantOuvert] = useState(true)
  const [archives, setArchives] = useState<string | null | false>(false)
  const lancesAuto = useRef(new Set<number>())

  useEffect(() => {
    api
      .session(sessionId)
      .then((s) => {
        setSession(s)
        setAffichee(s.etape_courante)
      })
      .catch((e) => setErreur(e.message))
  }, [sessionId])

  // Réinitialise l'état local à chaque changement d'étape affichée
  const sessionChargee = session !== null
  useEffect(() => {
    if (!session) return
    setBrouillon(null)
    setEdition(false)
    setOptions(ETAPES[affichee].optionsInitiales?.(session) ?? {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [affichee, sessionChargee])

  const executer = useCallback(
    async (message: string, etape: number, action: () => Promise<Session>) => {
      setOccupe({ message, debut: Date.now(), etape })
      setErreur(null)
      try {
        const s = await action()
        setSession(s)
        return s
      } catch (e) {
        setErreur((e as Error).message)
        api.session(sessionId).then(setSession).catch(() => undefined)
        return null
      } finally {
        setOccupe(null)
        setProgression(null)
      }
    },
    [sessionId],
  )

  const lancer = useCallback(
    async (n: number, consigne?: string, opts?: Options) => {
      const s = await executer(ETAPES[n].attente, n, () => api.generer(sessionId, n, consigne, opts ?? {}))
      if (s) setBrouillon(null)
    },
    [executer, sessionId],
  )

  // Lancement automatique des étapes rapides
  useEffect(() => {
    if (!session || occupe || erreur) return
    const etat = session.etapes[affichee]
    if (
      LANCEMENT_AUTO.has(affichee) &&
      !etat.livrable &&
      affichee <= session.etape_courante &&
      !lancesAuto.current.has(affichee)
    ) {
      lancesAuto.current.add(affichee)
      lancer(affichee)
    }
  }, [session, affichee, occupe, erreur, lancer])

  // Progression des entretiens simulés : lecture des lots déjà conservés
  useEffect(() => {
    if (!occupe || occupe.etape !== 3) return
    const t = setInterval(() => {
      api
        .session(sessionId)
        .then((s) => {
          const partiel = s.etapes[3].partiel ?? {}
          const lots = (partiel.lots ?? {}) as Record<string, unknown[]>
          const n = Object.values(lots).reduce((total, l) => total + l.length, 0)
          const interroges = Object.keys((partiel.entretiens ?? {}) as object).length
          if (interroges) setProgression(`Base de ${n} personas prête ; ${interroges} personas du panel interrogés…`)
          else if (n) setProgression(`${n} personas sur 100 générés…`)
        })
        .catch(() => undefined)
    }, 4000)
    return () => clearInterval(t)
  }, [occupe, sessionId])

  if (!session) {
    return (
      <div className="flex h-screen items-center justify-center">
        {erreur ? <Alerte>{erreur}</Alerte> : <Chargement texte="Chargement de la session…" />}
      </div>
    )
  }

  const definition = ETAPES[affichee]
  const etat = session.etapes[affichee]
  const accessible = affichee <= session.etape_courante
  const livrable = brouillon ?? etat.livrable
  const modifiable = !occupe && etat.livrable !== null && (etat.statut === 'brouillon' || edition)
  const suivanteValidee = session.etapes.slice(affichee + 1).some((e) => e.statut === 'valide')

  const valider = async () => {
    const n = affichee
    const s = await executer('Validation et archivage…', n, async () => {
      if (brouillon) await api.modifier(sessionId, n, brouillon)
      return api.valider(sessionId, n, undefined, options)
    })
    if (!s) return
    setBrouillon(null)
    if (n === ETAPES.length - 1) setArchives('00-SYNTHESE.md')
    else setAffichee(n + 1)
  }

  const enregistrer = (commentaire: string) =>
    executer('Enregistrement des modifications…', affichee, () =>
      api.modifier(sessionId, affichee, brouillon, commentaire),
    ).then((s) => s && setBrouillon(null))

  const appliquerSuggestion = (s: Suggestion) => {
    const opts = s.etape === affichee ? options : (ETAPES[s.etape].optionsInitiales?.(session) ?? {})
    setAffichee(s.etape)
    lancer(s.etape, s.consigne, opts)
  }

  const collecte = session.etapes[2]
  const ajouterSignal =
    collecte.statut === 'brouillon'
      ? (r: ResultatSource) => {
          const base = ((affichee === 2 ? brouillon : null) ?? collecte.livrable) as unknown as LivrableCollecte
          const suivant: LivrableCollecte = {
            ...base,
            signaux: [
              ...base.signaux,
              {
                id: `m${base.signaux.length + 1}`,
                titre: r.titre,
                resume: r.resume,
                axe: r.axe_presume ?? 'S',
                source: r.source,
                url: r.url,
                date: r.date,
                niveau: r.niveau,
                flux_id: r.flux_id,
                hypothese_ia: false,
                donnees_demo: r.donnees_demo,
                ajout_manuel: true,
                retenu: true,
              },
            ],
          }
          executer('Ajout du signal au dossier…', 2, () => api.modifier(sessionId, 2, suivant)).then(
            (s) => s && affichee === 2 && setBrouillon(null),
          )
        }
      : undefined

  const regler = (reglages: { mode?: Mode; modele?: string | null }) =>
    api
      .regler(sessionId, reglages)
      .then(setSession)
      .catch((e) => setErreur(e.message))

  const Vue = definition.Vue
  const Options = definition.Options

  return (
    <div className="flex h-screen flex-col bg-slate-100">
      <header className="flex items-center gap-4 border-b border-slate-200 bg-white px-4 py-2">
        <button type="button" onClick={onAccueil} className="shrink-0 text-left" title="Retour à l'accueil">
          <p className="text-sm font-bold text-slate-900">Prospective 2040</p>
          <p className="text-xs text-slate-500">
            {session.saisie.thematique} · {session.saisie.lieu || session.saisie.pays}
          </p>
        </button>
        <div className="min-w-0 flex-1">
          <Stepper session={session} affichee={affichee} onChoisir={setAffichee} />
        </div>
        {horsLigne ? (
          <span
            className="rounded bg-yellow-100 px-2 py-1 text-xs font-medium text-yellow-800"
            title="DEMO=true : session préenregistrée rejouée sans réseau"
          >
            Hors ligne
          </span>
        ) : (
          <ReglagesRun
            mode={session.mode}
            modele={session.modele}
            desactive={occupe !== null}
            onChange={regler}
          />
        )}
        <Chrono session={session} />
      </header>

      <div className="flex min-h-0 flex-1">
        <PanneauContexte
          session={session}
          ouvert={contexteOuvert}
          onBasculer={() => setContexteOuvert(!contexteOuvert)}
          onArchives={() => setArchives(null)}
        />

        <main className="flex min-w-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto p-6">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-xs font-semibold tracking-wide text-indigo-600 uppercase">
                  Étape {affichee} sur 8
                </p>
                <h2 className="text-2xl font-bold text-slate-900">{definition.titre}</h2>
                <p className="text-sm text-slate-600">{definition.but}</p>
              </div>
              {affichee === 8 && session.etapes[8].statut === 'valide' && (
                <Bouton variante="principal" onClick={() => setArchives('00-SYNTHESE.md')}>
                  Ouvrir la synthèse complète
                </Bouton>
              )}
            </div>

            {erreur && (
              <div className="mb-4">
                <Alerte>
                  {erreur}
                  <button type="button" className="ml-2 underline" onClick={() => setErreur(null)}>
                    Fermer
                  </button>
                </Alerte>
              </div>
            )}

            {occupe && occupe.etape === affichee && (
              <div className="mb-4">
                <Attente message={occupe.message} debut={occupe.debut} progression={progression} />
              </div>
            )}

            {!accessible && !etat.livrable ? (
              <Alerte ton="info">Validez d'abord l'étape {session.etape_courante} pour accéder à celle-ci.</Alerte>
            ) : etat.livrable === null ? (
              !occupe && (
                <Carte className="p-6">
                  <p className="text-slate-700">{definition.but}</p>
                  {Options && (
                    <div className="mt-4">
                      <Options session={session} options={options} onOptions={setOptions} />
                    </div>
                  )}
                  <Bouton variante="principal" className="mt-4 !px-5 !py-2.5" onClick={() => lancer(affichee, undefined, options)}>
                    Lancer l'étape {affichee} →
                  </Bouton>
                </Carte>
              )
            ) : (
              <>
                {etat.statut === 'a_faire' && (
                  <div className="mb-4">
                    <Alerte ton="avertissement">
                      Une étape précédente a été reprise : ce contenu date d'avant. Relancez l'étape
                      pour le mettre à jour, ou validez-le tel quel.
                    </Alerte>
                  </div>
                )}
                <div className={occupe ? 'pointer-events-none opacity-50' : ''}>
                  <Vue
                    session={session}
                    livrable={livrable}
                    modifiable={modifiable}
                    onChange={setBrouillon}
                    options={options}
                    onOptions={setOptions}
                  />
                </div>
              </>
            )}
          </div>

          {etat.livrable !== null && accessible && (
            <BarreValidation
              key={`${affichee}-${etat.version}`}
              etat={etat}
              occupe={occupe !== null}
              nonEnregistre={brouillon !== null}
              suivanteValidee={suivanteValidee}
              onValider={valider}
              onEnregistrer={enregistrer}
              onRelancer={(consigne) => lancer(affichee, consigne, options)}
              onSuivante={() => setAffichee(Math.min(affichee + 1, ETAPES.length - 1))}
              onModeEdition={setEdition}
            />
          )}
        </main>

        {assistantOuvert ? (
          <Assistant
            session={session}
            etape={affichee}
            occupe={occupe !== null}
            onAppliquer={appliquerSuggestion}
            onAjouterSignal={ajouterSignal}
            onFermer={() => setAssistantOuvert(false)}
          />
        ) : (
          <button
            type="button"
            onClick={() => setAssistantOuvert(true)}
            className="flex w-8 shrink-0 items-start justify-center border-l border-slate-200 bg-white pt-4 text-xs font-medium text-indigo-700 hover:bg-indigo-50"
          >
            <span className="[writing-mode:vertical-rl]">◂ Assistant</span>
          </button>
        )}
      </div>

      {archives !== false && (
        <VisionneuseArchives
          sessionId={sessionId}
          initial={archives ?? undefined}
          onFermer={() => setArchives(false)}
        />
      )}
    </div>
  )
}
