"""Étape 1 : activation des flux."""

from pydantic import BaseModel

from prospective.activation import FluxActivation, activer
from prospective.etapes.base import Etape, Generation
from prospective.modeles import LIBELLES_AXES, LIBELLES_NIVEAUX, Niveau
from prospective.session import ErreurSession, Session


class LivrableFlux(BaseModel):
    flux: list[FluxActivation]


class EtapeFlux(Etape):
    numero = 1
    titre = "Activation des flux"
    fichier = "01-flux-actives"
    modele = LivrableFlux

    async def generer(self, gen: Generation) -> LivrableFlux:
        if gen.session.contexte is None:
            raise ErreurSession("Validez d'abord l'étape 0.")
        return LivrableFlux(flux=activer(gen.session.contexte))

    def avant_validation(self, livrable: LivrableFlux, options: dict) -> LivrableFlux:
        if not any(f.actif for f in livrable.flux):
            raise ErreurSession("Activez au moins un flux.")
        return livrable

    def markdown(self, livrable: LivrableFlux, session: Session) -> str:
        blocs = []
        for niveau in Niveau:
            lignes = [
                f"| {'oui' if f.actif else 'non'} | {f.nom} | "
                f"{', '.join(LIBELLES_AXES[a] for a in f.axes)} | {f.raison} |"
                for f in livrable.flux
                if f.niveau == niveau
            ]
            if lignes:
                blocs.append(
                    f"### Niveau {LIBELLES_NIVEAUX[niveau]}\n\n"
                    "| Actif | Flux | Axes | Raison |\n|---|---|---|---|\n" + "\n".join(lignes)
                )
        return "\n\n".join(blocs)
