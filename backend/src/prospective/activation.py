"""Règle d'activation des flux selon la localisation du user context (brief, section 6)."""

from pydantic import BaseModel

from prospective.flux import CATALOGUE
from prospective.flux.base import Flux
from prospective.modeles import Axe, ContexteUtilisateur, Niveau


class FluxActivation(BaseModel):
    id: str
    nom: str
    description: str
    axes: list[Axe]
    niveau: Niveau
    cle_requise: bool
    actif: bool
    raison: str


def _decision(flux: Flux, ctx: ContexteUtilisateur) -> tuple[bool, str]:
    loc = ctx.localisation
    if flux.cle_requise:
        return False, "Clé d'API requise : à activer si elle est renseignée dans .env."
    match flux.niveau:
        case Niveau.MONDE:
            return True, f"Niveau Monde, toujours actif (filtré sur {loc.code_pays})."
        case Niveau.ZONE:
            if loc.ue:
                return True, f"{loc.pays} appartient à l'Union européenne."
            return False, f"{loc.pays} n'appartient pas à l'Union européenne."
        case Niveau.PAYS:
            if flux.pays and loc.code_pays in flux.pays:
                return True, f"Connecteur national disponible pour {loc.pays}."
            return False, "Pas de connecteur national pour ce pays : repli sur le niveau Monde."
        case Niveau.LOCAL:
            if flux.pays and loc.code_pays not in flux.pays:
                return False, f"Connecteur local indisponible pour {loc.pays}."
            if loc.code_commune or loc.code_postal or (loc.lat is not None):
                return (
                    True,
                    f"Localisation infra-nationale fournie ({loc.ville or loc.code_postal}).",
                )
            return False, "Aucune localisation infra-nationale fournie."
    return False, "Niveau inconnu."


def activer(ctx: ContexteUtilisateur) -> list[FluxActivation]:
    resultat = []
    for flux in CATALOGUE:
        actif, raison = _decision(flux, ctx)
        resultat.append(
            FluxActivation(
                id=flux.id,
                nom=flux.nom,
                description=flux.description,
                axes=flux.axes,
                niveau=flux.niveau,
                cle_requise=flux.cle_requise,
                actif=actif,
                raison=raison,
            )
        )
    return resultat
