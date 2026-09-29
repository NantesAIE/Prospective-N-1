import type { CatalogueModeles, MessageChat, Mode, ResumeSession, SaisieProjet, Session } from './types'

export class ErreurApi extends Error {}

async function appeler<T>(chemin: string, init?: RequestInit): Promise<T> {
  let reponse: Response
  try {
    reponse = await fetch(`/api${chemin}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ErreurApi('Back-end injoignable : vérifiez que le serveur est lancé.')
  }
  if (!reponse.ok) {
    let detail = `Erreur ${reponse.status}`
    try {
      const corps = await reponse.json()
      if (typeof corps.detail === 'string') detail = corps.detail
      else if (Array.isArray(corps.detail)) detail = 'Données invalides : vérifiez le formulaire.'
    } catch {
      // corps non JSON : on garde le code HTTP
    }
    throw new ErreurApi(detail)
  }
  const type = reponse.headers.get('content-type') ?? ''
  return (type.includes('application/json') ? reponse.json() : reponse.text()) as Promise<T>
}

const envoyer = (methode: string, corps: unknown): RequestInit => ({
  method: methode,
  body: JSON.stringify(corps),
})

export const api = {
  sante: () => appeler<{ demo: boolean; cle_api_configuree: boolean; modele: string }>('/sante'),
  saisieDemo: () => appeler<SaisieProjet>('/demo/saisie'),
  sessions: () => appeler<ResumeSession[]>('/sessions'),
  modeles: () => appeler<CatalogueModeles>('/modeles'),
  creerSession: (saisie: SaisieProjet, mode: Mode, modele: string | null) =>
    appeler<Session>('/sessions', envoyer('POST', { ...saisie, mode, modele })),
  regler: (id: string, reglages: { mode?: Mode; modele?: string | null }) =>
    appeler<Session>(`/sessions/${id}`, envoyer('PATCH', reglages)),
  session: (id: string) => appeler<Session>(`/sessions/${id}`),
  generer: (id: string, n: number, consigne?: string, options: Record<string, unknown> = {}) =>
    appeler<Session>(`/sessions/${id}/etapes/${n}/generer`, envoyer('POST', { consigne, options })),
  modifier: (id: string, n: number, livrable: unknown, commentaire?: string) =>
    appeler<Session>(`/sessions/${id}/etapes/${n}`, envoyer('PUT', { livrable, commentaire })),
  valider: (id: string, n: number, commentaire?: string, options: Record<string, unknown> = {}) =>
    appeler<Session>(
      `/sessions/${id}/etapes/${n}/valider`,
      envoyer('POST', { commentaire, options }),
    ),
  conversation: (id: string) => appeler<MessageChat[]>(`/sessions/${id}/conversation`),
  parler: (id: string, message: string, etape: number) =>
    appeler<MessageChat[]>(`/sessions/${id}/assistant`, envoyer('POST', { message, etape })),
  fichiers: (id: string) => appeler<string[]>(`/sessions/${id}/fichiers`),
  fichier: (id: string, nom: string) =>
    appeler<string>(`/sessions/${id}/fichiers/${encodeURIComponent(nom)}`),
}
