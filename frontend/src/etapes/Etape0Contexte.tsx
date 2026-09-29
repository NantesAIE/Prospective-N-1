import { Carte, ListeEditable, Puces, Titre } from '../components/ui'
import type { FicheContexte, LivrableContexte } from '../types'
import type { VueEtapeProps } from './commun'

const CHAMPS_TEXTE: { cle: 'probleme' | 'cible' | 'proposition_valeur' | 'territoire'; libelle: string }[] = [
  { cle: 'probleme', libelle: 'Problème' },
  { cle: 'cible', libelle: 'Cible' },
  { cle: 'proposition_valeur', libelle: 'Proposition de valeur pressentie' },
  { cle: 'territoire', libelle: 'Territoire' },
]

const CHAMPS_LISTE: { cle: keyof FicheContexte; libelle: string }[] = [
  { cle: 'hypotheses_implicites', libelle: 'Hypothèses implicites' },
  { cle: 'questions_ouvertes', libelle: 'Questions ouvertes' },
  { cle: 'mots_cles', libelle: 'Mots-clés de recherche' },
  { cle: 'codes_naf', libelle: 'Codes NAF' },
]

export function Etape0Contexte({ livrable, modifiable, onChange }: VueEtapeProps<LivrableContexte>) {
  const { fiche, localisation: loc } = livrable
  const maj = (partiel: Partial<FicheContexte>) => onChange({ ...livrable, fiche: { ...fiche, ...partiel } })

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <Carte>
          <Titre>Fiche contexte</Titre>
          <dl className="space-y-3">
            {CHAMPS_TEXTE.map(({ cle, libelle }) => (
              <div key={cle}>
                <dt className="text-xs font-semibold text-slate-500">{libelle}</dt>
                <dd className="mt-0.5 text-sm text-slate-800">
                  {modifiable ? (
                    <textarea
                      className="w-full rounded-lg border border-slate-300 p-2 text-sm"
                      rows={2}
                      value={fiche[cle]}
                      onChange={(e) => maj({ [cle]: e.target.value })}
                    />
                  ) : (
                    fiche[cle]
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </Carte>
        <div className="grid gap-4 md:grid-cols-2">
          {CHAMPS_LISTE.map(({ cle, libelle }) => (
            <Carte key={cle}>
              <Titre>{libelle}</Titre>
              {modifiable ? (
                <ListeEditable
                  valeurs={fiche[cle] as string[]}
                  onChange={(v) => maj({ [cle]: v } as Partial<FicheContexte>)}
                />
              ) : (
                <Puces elements={fiche[cle] as string[]} />
              )}
            </Carte>
          ))}
        </div>
      </div>
      <Carte className="h-fit">
        <Titre>Localisation géocodée</Titre>
        <dl className="space-y-1 text-sm">
          {[
            ['Commune', loc.ville],
            ['Code postal', loc.code_postal],
            ['Département', loc.departement],
            ['Région', loc.region],
            ['Pays', `${loc.pays} (${loc.code_pays})${loc.ue ? ', UE' : ''}`],
            ['Coordonnées', loc.lat != null ? `${loc.lat.toFixed(3)}, ${loc.lon?.toFixed(3)}` : null],
            ['Population', loc.population?.toLocaleString('fr-FR')],
          ]
            .filter(([, v]) => v)
            .map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <dt className="text-slate-500">{k}</dt>
                <dd className="text-right font-medium text-slate-800">{v}</dd>
              </div>
            ))}
        </dl>
        <p className="mt-3 text-xs text-slate-500">
          La localisation détermine les flux de données activés à l'étape suivante.
        </p>
      </Carte>
    </div>
  )
}
