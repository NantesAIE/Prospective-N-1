"""Géorisques : risques naturels et technologiques de la commune (code INSEE)."""

from collections import Counter
from typing import ClassVar

import httpx

from prospective.flux.base import Flux
from prospective.flux.outils import aujourdhui, date_iso, rassembler
from prospective.modeles import Axe, ContexteUtilisateur, Niveau, SignalBrut

URL = "https://georisques.gouv.fr/api/v1/"
SOURCE = "Géorisques (BRGM, ministère de la Transition écologique)"
RADON = {"1": "faible", "2": "faible avec facteurs aggravants", "3": "significatif"}


class GeoRisques(Flux):
    id = "geo_risques"
    nom = "Géorisques (risques locaux)"
    description = "Risques recensés, arrêtés CatNat, inondation, sismicité et radon de la commune."
    axes: ClassVar[list[Axe]] = [Axe.E2]
    niveau = Niveau.LOCAL
    pays: ClassVar[list[str] | None] = ["FR"]
    interrogeable = False

    async def _appel(
        self, client: httpx.AsyncClient, chemin: str, params: dict
    ) -> tuple[list, str]:
        reponse = await client.get(URL + chemin, params=params)
        reponse.raise_for_status()
        return reponse.json().get("data") or [], str(reponse.url)

    async def collecter(
        self, ctx: ContexteUtilisateur, client: httpx.AsyncClient, requete: str | None = None
    ) -> list[SignalBrut]:
        loc = ctx.localisation
        if not loc.code_commune:
            raise ValueError("Code INSEE de la commune requis")
        insee = {"code_insee": loc.code_commune}
        # API lente et irrégulière : appels parallèles, résultats partiels conservés
        risques, catnat, tri, sismicite, radon = await rassembler(
            [
                self._appel(client, "gaspar/risques", insee),
                self._appel(client, "gaspar/catnat", {**insee, "page_size": 100}),
                self._appel(client, "gaspar/tri", insee),
                self._appel(client, "zonage_sismique", insee),
                self._appel(client, "radon", insee),
            ]
        )
        commune = loc.ville or loc.code_commune
        signaux: list[SignalBrut] = []

        def ajouter(titre: str, resume: str, url: str, date: str | None = None) -> None:
            signaux.append(
                SignalBrut(
                    titre=titre,
                    resume=resume,
                    source=SOURCE,
                    url=url,
                    date=date or aujourdhui(),
                    axe_presume=Axe.E2,
                    flux_id=self.id,
                    niveau=self.niveau,
                )
            )

        if risques and risques[0]:
            detail = risques[0][0].get("risques_detail") or []
            # Les codes à deux chiffres désignent les familles de risque
            familles = [r["libelle_risque_long"] for r in detail if len(r["num_risque"]) == 2]
            if familles:
                ajouter(
                    f"{commune} : {len(familles)} familles de risques recensées",
                    f"Géorisques recense à {commune} {len(familles)} familles de risques "
                    f"({', '.join(familles)}), détaillées en {len(detail) - len(familles)} aléas.",
                    risques[1],
                )

        if catnat and catnat[0]:
            arretes = catnat[0]
            types = Counter(a["libelle_risque_jo"] for a in arretes)
            dernier = max(arretes, key=lambda a: date_iso(a.get("date_publication_jo")))
            repartition = ", ".join(f"{n} « {t} »" for t, n in types.most_common(3))
            ajouter(
                f"{commune} : {len(arretes)} arrêtés de catastrophe naturelle",
                f"{len(arretes)} arrêtés CatNat concernent {commune} ({repartition}) ; le plus "
                f"récent, publié au JO le {date_iso(dernier['date_publication_jo'])}, porte sur "
                f"« {dernier['libelle_risque_jo']} » du {date_iso(dernier['date_debut_evt'])} "
                f"au {date_iso(dernier['date_fin_evt'])}.",
                catnat[1],
                date_iso(dernier.get("date_publication_jo")),
            )

        if tri and tri[0]:
            territoire = tri[0][0]
            aleas = ", ".join(
                r["libelle_risque_long"].lower() for r in territoire["liste_libelle_risque"]
            )
            ajouter(
                f"{commune} : territoire à risque important d'inondation (TRI)",
                f"{commune} appartient au TRI « {territoire['libelle_tri']} » ({aleas}), "
                f"arrêté national du {date_iso(territoire.get('date_arrete_national'))}.",
                tri[1],
            )

        morceaux, urls = [], []
        if sismicite and sismicite[0]:
            morceaux.append(f"zone de sismicité {sismicite[0][0]['zone_sismicite'].lower()}")
            urls.append(sismicite[1])
        if radon and radon[0]:
            classe = str(radon[0][0]["classe_potentiel"])
            morceaux.append(
                f"potentiel radon de catégorie {classe} ({RADON.get(classe, 'inconnu')})"
            )
            urls.append(radon[1])
        if morceaux:
            ajouter(
                f"{commune} : sismicité et radon",
                f"{commune} est classée en " + " et ".join(morceaux) + ".",
                urls[0],
            )

        if not signaux:
            raise RuntimeError("Géorisques : aucune réponse exploitable")
        return signaux
