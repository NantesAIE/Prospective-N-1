import { Fragment, useState } from 'react'
import { Alerte, Carte, LienSource, Puces, Titre } from '../components/ui'
import { LIBELLES_OPINIONS, type LivrableEntretiens, type Opinion } from '../types'
import type { OptionsEtapeProps, VueEtapeProps } from './commun'

export const MENTION_ENTRETIENS = 'Entretiens simulés par IA, à confirmer par de vrais entretiens terrain.'

const COULEURS_OPINIONS: Record<Opinion, string> = {
  tres_favorable: 'bg-emerald-600',
  favorable: 'bg-emerald-400',
  neutre: 'bg-slate-300',
  reserve: 'bg-amber-400',
  hostile: 'bg-rose-500',
}

type Onglet = 'synthese' | 'verbatims' | 'personas' | 'guide'

/** Questions supplémentaires, prises en compte au lancement ou à la relance. */
export function OptionsEntretiens({ options, onOptions }: OptionsEtapeProps) {
  const questions = (options.questions_ajoutees as string[] | undefined) ?? []
  return (
    <div className="space-y-2">
      <p className="text-sm text-slate-600">
        Questions à ajouter au guide d'entretien (une par ligne), en plus des 5 questions générées :
      </p>
      <textarea
        className="w-full rounded-lg border border-slate-300 p-2 text-sm"
        rows={3}
        placeholder="Ex. : Seriez-vous prêt à payer un abonnement mensuel ?"
        value={questions.join('\n')}
        onChange={(e) => onOptions({ ...options, questions_ajoutees: e.target.value.split('\n') })}
      />
    </div>
  )
}

export function Etape3Entretiens(props: VueEtapeProps<LivrableEntretiens>) {
  const { livrable } = props
  const [onglet, setOnglet] = useState<Onglet>('synthese')
  const [ouvert, setOuvert] = useState<string | null>(null)
  const [panelSeul, setPanelSeul] = useState(false)
  const panel = new Set(livrable.panel ?? [])
  const listees = livrable.personas.filter((p) => !panelSeul || panel.has(p.id))
  const s = livrable.synthese
  const personas = Object.fromEntries(livrable.personas.map((p) => [p.id, p]))
  const total = livrable.repartition.reduce((n, r) => n + r.nombre, 0) || 1

  return (
    <div className="space-y-4">
      <Alerte ton="avertissement">
        <strong>{MENTION_ENTRETIENS}</strong>
      </Alerte>

      <Carte>
        <Titre>Répartition des opinions sur la base de {livrable.personas.length} personas</Titre>
        <p className="mb-2 text-sm text-slate-600">
          Les {livrable.personas.length} personas forment une base ancrée sur la démographie du territoire ; un
          panel représentatif de <strong>{panel.size}</strong> personas a été interrogé.
        </p>
        <div className="flex h-6 overflow-hidden rounded-full">
          {livrable.repartition.map((r) =>
            r.nombre ? (
              <div
                key={r.opinion}
                className={COULEURS_OPINIONS[r.opinion]}
                style={{ width: `${(r.nombre / total) * 100}%` }}
                title={`${LIBELLES_OPINIONS[r.opinion]} : ${r.nombre}`}
              />
            ) : null,
          )}
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-600">
          {livrable.repartition.map((r) => (
            <span key={r.opinion} className="inline-flex items-center gap-1">
              <span className={`h-2.5 w-2.5 rounded-full ${COULEURS_OPINIONS[r.opinion]}`} />
              {LIBELLES_OPINIONS[r.opinion]} : {r.nombre}
            </span>
          ))}
        </div>
      </Carte>

      <div className="flex gap-1 border-b border-slate-200">
        {(
          [
            ['synthese', 'Synthèse'],
            ['verbatims', 'Verbatims'],
            ['personas', `Base et panel (${livrable.personas.length})`],
            ['guide', "Guide et ancrage"],
          ] as [Onglet, string][]
        ).map(([id, libelle]) => (
          <button
            key={id}
            type="button"
            onClick={() => setOnglet(id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              onglet === id ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500'
            }`}
          >
            {libelle}
          </button>
        ))}
      </div>

      {onglet === 'synthese' && (
        <div className="grid gap-4 md:grid-cols-2">
          {(
            [
              ['Attentes majeures', s.attentes_majeures],
              ['Irritants', s.irritants],
              ['Usages émergents', s.usages_emergents],
              ['Enseignements pour la prospective', s.enseignements],
            ] as [string, string[]][]
          ).map(([titre, liste]) => (
            <Carte key={titre}>
              <Titre>{titre}</Titre>
              <Puces elements={liste} />
            </Carte>
          ))}
        </div>
      )}

      {onglet === 'verbatims' && (
        <div className="grid gap-3 md:grid-cols-2">
          {s.verbatims.map((v, i) => {
            const p = personas[v.persona_id]
            return (
              <Carte key={i}>
                <p className="text-slate-800 italic">« {v.citation} »</p>
                <p className="mt-2 text-xs text-slate-500">
                  {v.persona_id}
                  {p && `, ${p.prenom}, ${p.age} ans, ${p.situation} (${LIBELLES_OPINIONS[p.opinion]})`}
                </p>
              </Carte>
            )
          })}
        </div>
      )}

      {onglet === 'personas' && (
        <Carte className="overflow-x-auto p-0">
          <label className="flex items-center gap-2 border-b border-slate-100 px-3 py-2 text-xs text-slate-600">
            <input type="checkbox" checked={panelSeul} onChange={(e) => setPanelSeul(e.target.checked)} />
            Afficher seulement le panel interrogé ({panel.size})
          </label>
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                {['Id', 'Prénom', 'Âge', 'Situation', 'CSP', 'Lieu de vie', 'Opinion'].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {listees.map((p) => (
                <Fragment key={p.id}>
                  <tr
                    className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                    onClick={() => setOuvert(ouvert === p.id ? null : p.id)}
                  >
                    <td className="px-3 py-1.5 font-mono text-xs text-slate-400">{p.id}</td>
                    <td className="px-3 py-1.5">
                      {p.prenom}
                      {panel.has(p.id) && (
                        <span className="ml-1.5 rounded bg-indigo-100 px-1.5 text-xs font-medium text-indigo-700">
                          panel
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-1.5">{p.age}</td>
                    <td className="px-3 py-1.5">{p.situation}</td>
                    <td className="px-3 py-1.5">{p.csp}</td>
                    <td className="px-3 py-1.5">{p.lieu_de_vie}</td>
                    <td className="px-3 py-1.5">
                      <span className="inline-flex items-center gap-1">
                        <span className={`h-2 w-2 rounded-full ${COULEURS_OPINIONS[p.opinion]}`} />
                        {LIBELLES_OPINIONS[p.opinion]}
                      </span>
                    </td>
                  </tr>
                  {ouvert === p.id && (
                    <tr className="bg-slate-50">
                      <td colSpan={7} className="px-3 py-2 text-sm">
                        <p>
                          <strong>Usages :</strong> {p.usages}
                        </p>
                        <p>
                          <strong>Attentes :</strong> {p.attentes}
                        </p>
                        {!p.reponses.length && (
                          <p className="mt-1 text-xs text-slate-500">Persona de la base, non interrogé.</p>
                        )}
                        <ol className="mt-1 list-decimal pl-5">
                          {p.reponses.map((r, i) => (
                            <li key={i}>
                              <span className="text-slate-500">{livrable.guide[i]}</span>
                              <br />« {r} »
                            </li>
                          ))}
                        </ol>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </Carte>
      )}

      {onglet === 'guide' && (
        <div className="grid gap-4 md:grid-cols-2">
          <Carte>
            <Titre>Guide d'entretien</Titre>
            <ol className="list-decimal space-y-1 pl-5 text-sm">
              {livrable.guide.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ol>
          </Carte>
          <Carte>
            <Titre>Ancrage démographique</Titre>
            <pre className="text-sm whitespace-pre-wrap text-slate-700">{livrable.profil_demographique}</pre>
            {livrable.source_demographique && (
              <div className="mt-2">
                <LienSource source={livrable.source_demographique.nom} url={livrable.source_demographique.url} />
              </div>
            )}
          </Carte>
        </div>
      )}

      {props.modifiable && (
        <Carte>
          <Titre>Compléter le guide</Titre>
          <OptionsEntretiens session={props.session} options={props.options} onOptions={props.onOptions} />
          <p className="mt-1 text-xs text-slate-500">
            Utilisez ensuite « Relancer » pour réinterroger le panel avec le guide complété.
          </p>
        </Carte>
      )}
    </div>
  )
}
