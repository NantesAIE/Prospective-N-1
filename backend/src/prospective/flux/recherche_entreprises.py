"""API Recherche d'entreprises : concurrents locaux par mots-clés, code postal et code NAF."""

from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.outils import (
    Limiteur,
    aujourdhui,
    entrelacer,
    nombre,
    rassembler,
    termes,
)
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://recherche-entreprises.api.gouv.fr/search"
# Permalien officiel de l'Annuaire des entreprises, construit à partir du SIREN renvoyé
URL_FICHE = "https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}"
SOURCE = "Annuaire des entreprises (API Recherche d'entreprises)"
MAX_SIGNAUX = 12

# Limite documentée : 7 requêtes par seconde
_limiteur = Limiteur(1 / 7)

TRANCHES_EFFECTIF = {
    "NN": "non employeuse",
    "00": "0 salarié",
    "01": "1 ou 2 salariés",
    "02": "3 à 5 salariés",
    "03": "6 à 9 salariés",
    "11": "10 à 19 salariés",
    "12": "20 à 49 salariés",
    "21": "50 à 99 salariés",
    "22": "100 à 199 salariés",
    "31": "200 à 249 salariés",
    "32": "250 à 499 salariés",
    "41": "500 à 999 salariés",
    "42": "1 000 à 1 999 salariés",
    "51": "2 000 à 4 999 salariés",
    "52": "5 000 à 9 999 salariés",
    "53": "10 000 salariés et plus",
}


def _effectif(code: str | None) -> str:
    return TRANCHES_EFFECTIF.get(code or "NN", "effectif non renseigné")


def _etablissement_local(entreprise: dict, code_departement: str | None) -> dict | None:
    """Établissement ouvert dans le département, sinon None (l'acteur n'est pas local)."""
    candidats = [*(entreprise.get("matching_etablissements") or []), entreprise.get("siege") or {}]
    for etab in candidats:
        dans_zone = not code_departement or str(etab.get("code_postal") or "").startswith(
            code_departement
        )
        if etab.get("etat_administratif") == "A" and dans_zone:
            return etab
    return None


class RechercheEntreprises(Flux):
    id = "recherche_entreprises"
    nom = "Recherche d'entreprises (concurrents locaux)"
    description = "Entreprises actives du territoire par mots-clés et codes NAF (SIRENE, RNE)."
    axes: ClassVar[list[Axe]] = [Axe.E1]
    niveau = Niveau.LOCAL
    pays: ClassVar[list[str] | None] = ["FR"]

    async def _chercher(self, client: httpx.AsyncClient, params: dict) -> tuple[dict, str]:
        await _limiteur.attendre()
        reponse = await client.get(URL, params={"etat_administratif": "A", **params})
        reponse.raise_for_status()
        return reponse.json(), str(reponse.url)

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        loc = ctx.localisation
        zone = {"departement": loc.code_departement} if loc.code_departement else {}
        liste = termes(ctx, requete, maximum=3)
        recherches = [self._chercher(client, {"q": t, "per_page": 10, **zone}) for t in liste]
        if ctx.codes_naf and (loc.code_postal or zone):
            filtre = {"code_postal": loc.code_postal} if loc.code_postal else zone
            naf = ",".join(ctx.codes_naf)
            recherches.append(
                self._chercher(client, {"activite_principale": naf, "per_page": 10, **filtre})
            )
        resultats = await rassembler(recherches)
        if all(r is None for r in resultats):
            raise RuntimeError("Recherche d'entreprises : aucune réponse")

        signaux: list[SignalBrut] = []
        if ctx.codes_naf and resultats[-1] is not None and len(resultats) > len(liste):
            donnees, url = resultats[-1]
            perimetre = (
                f"au code postal {loc.code_postal}" if loc.code_postal else "dans le territoire"
            )
            signaux.append(
                SignalBrut(
                    titre=f"Densité concurrentielle {perimetre} ({loc.ville or loc.pays})",
                    resume=(
                        f"{nombre(donnees['total_results'])} entreprises actives ont un "
                        f"établissement {perimetre} sur les codes NAF {', '.join(ctx.codes_naf)}."
                    ),
                    source=SOURCE,
                    url=url,
                    date=aujourdhui(),
                    axe_presume=Axe.E1,
                    flux_id=self.id,
                    niveau=self.niveau,
                )
            )

        # Chaque requête (mots-clés, codes NAF) est représentée à tour de rôle
        entreprises = entrelacer([r[0].get("results", []) for r in resultats if r is not None])
        vus: set[str] = set()
        for entreprise in entreprises:
            etab = _etablissement_local(entreprise, loc.code_departement)
            if etab is None or entreprise["siren"] in vus or len(signaux) >= MAX_SIGNAUX:
                continue
            vus.add(entreprise["siren"])
            signaux.append(self._signal(entreprise, etab))
        return signaux

    def _signal(self, entreprise: dict, etab: dict) -> SignalBrut:
        nom = entreprise.get("nom_complet") or entreprise.get("nom_raison_sociale") or "?"
        commune = etab.get("libelle_commune") or "commune inconnue"
        activite = etab.get("activite_principale") or entreprise.get("activite_principale")
        creation = entreprise.get("date_creation") or ""
        if creation.startswith("1900"):
            creation = ""  # date conventionnelle des très anciennes entreprises
        etab_creation = etab.get("date_creation") or creation
        categorie = entreprise.get("categorie_entreprise")
        ouverts = entreprise.get("nombre_etablissements_ouverts")
        details = [
            f"activité NAF {activite}",
            f"entreprise créée le {creation}" if creation else None,
            f"établissement local ouvert le {etab_creation}" if etab_creation != creation else None,
            _effectif(entreprise.get("tranche_effectif_salarie")),
            f"catégorie {categorie}" if categorie else None,
            f"{ouverts} établissement(s) ouvert(s)" if ouverts else None,
        ]
        return SignalBrut(
            titre=f"{nom} ({commune})",
            resume=f"Acteur présent à {commune} : " + ", ".join(d for d in details if d) + ".",
            source=SOURCE,
            url=URL_FICHE.format(siren=entreprise["siren"]),
            date=etab_creation,
            axe_presume=Axe.E1,
            flux_id=self.id,
            niveau=self.niveau,
        )
