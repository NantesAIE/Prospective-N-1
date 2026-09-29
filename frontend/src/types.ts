// Types alignés sur les modèles Pydantic du back-end (backend/src/prospective)

export type Axe = 'S' | 'T' | 'E1' | 'E2' | 'P' | 'L'
export type Niveau = 'monde' | 'zone' | 'pays' | 'local'
export type StatutEtape = 'a_faire' | 'brouillon' | 'valide'
export type Mode = 'demo' | 'complet'

export const LIBELLES_AXES: Record<Axe, string> = {
  S: 'Social',
  T: 'Technologique',
  E1: 'Économique',
  E2: 'Environnemental',
  P: 'Politique',
  L: 'Légal',
}

export const LIBELLES_NIVEAUX: Record<Niveau, string> = {
  monde: 'Monde',
  zone: 'UE',
  pays: 'Pays',
  local: 'Local',
}

export interface SaisieProjet {
  description: string
  thematique: string
  pays: string
  lieu: string | null
  horizon: number
  ambition: string
}

export interface Localisation {
  pays: string
  code_pays: string
  ue: boolean
  ville: string | null
  code_postal: string | null
  departement: string | null
  region: string | null
  lat: number | null
  lon: number | null
  population: number | null
}

export interface EtatEtape<L = Record<string, unknown>> {
  numero: number
  statut: StatutEtape
  version: number
  livrable: L | null
  modifie: boolean
  commentaire: string
  consignes: string[]
  flux_utilises: string[]
  partiel: Record<string, unknown> | null
  valide_le: string | null
}

export interface Session {
  id: string
  dossier: string
  cree_le: string
  saisie: SaisieProjet
  mode: Mode
  modele: string | null
  etapes: EtatEtape[]
  duree_secondes: number
  derniere_activite: string
  etape_courante: number
}

export interface CatalogueModeles {
  modeles: string[]
  defaut: string
  rapide: string
}

export interface ResumeSession {
  id: string
  dossier: string
  cree_le: string
  thematique: string
  lieu: string
  description: string
  etape_courante: number
  nb_validees: number
}

export interface Source {
  nom: string
  url: string
  date?: string | null
}

// Étape 0
export interface FicheContexte {
  probleme: string
  cible: string
  proposition_valeur: string
  territoire: string
  hypotheses_implicites: string[]
  questions_ouvertes: string[]
  mots_cles: string[]
  mots_cles_en: string[]
  codes_naf: string[]
}
export interface LivrableContexte {
  fiche: FicheContexte
  localisation: Localisation
}

// Étape 1
export interface FluxActivation {
  id: string
  nom: string
  description: string
  axes: Axe[]
  niveau: Niveau
  cle_requise: boolean
  actif: boolean
  raison: string
}
export interface LivrableFlux {
  flux: FluxActivation[]
}

// Étape 2
export interface Signal {
  id: string
  titre: string
  resume: string
  axe: Axe
  source: string | null
  url: string | null
  date: string | null
  niveau: Niveau | null
  flux_id: string | null
  hypothese_ia: boolean
  donnees_demo: boolean
  ajout_manuel: boolean
  retenu: boolean
}
export interface LivrableCollecte {
  signaux: Signal[]
  flux_degrades: string[]
  nb_elements_bruts: number
}

// Étape 3
export type Opinion = 'tres_favorable' | 'favorable' | 'neutre' | 'reserve' | 'hostile'
export const LIBELLES_OPINIONS: Record<Opinion, string> = {
  tres_favorable: 'Très favorable',
  favorable: 'Favorable',
  neutre: 'Neutre',
  reserve: 'Réservé',
  hostile: 'Hostile',
}
export interface Persona {
  id: string
  prenom: string
  age: number
  genre: string
  situation: string
  csp: string
  lieu_de_vie: string
  usages: string
  attentes: string
  reponses: string[]
  opinion: Opinion
}
export interface LivrableEntretiens {
  avertissement: string
  guide: string[]
  profil_demographique: string
  source_demographique: Source | null
  personas: Persona[]
  panel: string[]
  synthese: {
    attentes_majeures: string[]
    irritants: string[]
    usages_emergents: string[]
    verbatims: { persona_id: string; citation: string }[]
    enseignements: string[]
  }
  repartition: { opinion: Opinion; nombre: number }[]
}

// Étape 4
export type Categorie = 'signal_faible' | 'tendance_lourde' | 'incertitude'
export const LIBELLES_CATEGORIES: Record<Categorie, string> = {
  signal_faible: 'Signal faible',
  tendance_lourde: 'Tendance lourde',
  incertitude: 'Incertitude',
}
export interface ElementQualifie {
  id: string
  titre: string
  description: string
  axe: Axe
  categorie: Categorie
  impact: number
  incertitude: number
  justification: string
  origine: 'collecte' | 'entretiens' | 'ia'
  ref_signal: string | null
  source: string | null
  url: string | null
  date: string | null
  hypothese_ia: boolean
}
export interface LivrableSteepl {
  elements: ElementQualifie[]
}

// Étape 5
export type Zone = 'probable' | 'plausible' | 'possible' | 'souhaitable'
export const LIBELLES_ZONES: Record<Zone, string> = {
  probable: 'Probable',
  plausible: 'Plausible',
  possible: 'Possible',
  souhaitable: 'Souhaitable',
}
export interface Position {
  element_id: string
  titre: string
  categorie: Categorie
  axe: Axe
  zone: Zone
  jalon: number
  commentaire: string
}
export interface LivrableCone {
  zones: { zone: Zone; description: string }[]
  positions: Position[]
}

// Étape 6
export type Quadrant = '++' | '+-' | '-+' | '--'
export interface AxeScenario {
  element_id: string
  intitule: string
  pole_moins: string
  pole_plus: string
}
export interface Scenario {
  quadrant: Quadrant
  titre: string
  recit: string
  elements_menants: string[]
  conditions_bascule: string[]
  implication_projet: string
}
export interface LivrableScenarios {
  axe_x: AxeScenario
  axe_y: AxeScenario
  scenarios: Scenario[]
  choix: { cible: Quadrant | null; vigilance: Quadrant | null }
}

// Étape 7
export type HorizonJalon = '2040' | '2035' | '2030' | '18 mois' | '90 jours'
export interface LivrableRoadmap {
  impact: {
    offre: string
    clients: string
    modele_economique: string
    risques: string[]
    opportunites: string[]
  }
  robustesse: { quadrant: string; titre_scenario: string; score: number; commentaire: string }[]
  jalons: { horizon: HorizonJalon; objectif: string; actions: string[] }[]
  signaux_a_surveiller: {
    indicateur: string
    ce_qui_alerte: string
    source_suivi: string
    flux_id: string | null
    hypothese_ia: boolean
  }[]
  paris_sans_regret: { action: string; justification: string }[]
}

// Étape 8
export type FormatArtefact =
  | 'une_de_presse'
  | 'publicite'
  | 'fiche_produit'
  | 'avis_client'
  | 'offre_emploi'
  | 'notification'
export const LIBELLES_FORMATS: Record<FormatArtefact, string> = {
  une_de_presse: 'Une de presse locale',
  publicite: 'Publicité',
  fiche_produit: 'Fiche produit',
  avis_client: 'Avis client',
  offre_emploi: "Offre d'emploi",
  notification: "Notification d'application",
}
export type TypeBloc =
  | 'surtitre'
  | 'titre'
  | 'chapo'
  | 'paragraphe'
  | 'encadre'
  | 'citation'
  | 'liste'
  | 'prix'
  | 'mention'
export interface Artefact {
  format: FormatArtefact
  media: string
  date_fictive: string
  titre: string
  blocs: { type: TypeBloc; texte: string }[]
}
export interface LivrableRestitution {
  narratif: { titre: string; texte: string }
  artefact: Artefact
  synthese_executive: string
}

// Assistant
export interface Suggestion {
  titre: string
  explication: string
  etape: number
  consigne: string
}
export interface ResultatSource {
  id: string
  titre: string
  resume: string
  source: string
  url: string
  date: string
  axe_presume: Axe | null
  flux_id: string
  niveau: Niveau
  niveau_libelle: string
  donnees_demo: boolean
}
export interface MessageChat {
  role: 'user' | 'assistant'
  contenu: string
  etape: number
  horodatage: string
  suggestions: Suggestion[]
  resultats: ResultatSource[]
}
