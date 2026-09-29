"""Application FastAPI. Servie uniquement en local (127.0.0.1)."""

import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prospective.api import gerer_erreur_metier, routeur
from prospective.config import parametres
from prospective.llm import ErreurLLM
from prospective.session import ErreurSession

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s : %(message)s")

app = FastAPI(title="Prospective business : Hack The Vibe")

# Front Vite en développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(ErreurLLM, gerer_erreur_metier)
app.add_exception_handler(ErreurSession, gerer_erreur_metier)
app.include_router(routeur)


def main() -> None:
    p = parametres()
    p.dossier_archives.mkdir(exist_ok=True)
    uvicorn.run(
        "prospective.main:app",
        host=p.hote,
        port=p.port,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)],
    )
