"""Contexte TLS compatible avec le proxy d'entreprise.

Module sans dépendance interne : base.py peut l'importer sans cycle.
"""

import ssl
from functools import lru_cache

import certifi


@lru_cache
def contexte_tls() -> ssl.SSLContext:
    """Certificats certifi et magasin système.

    Le proxy d'entreprise (Zscaler) réémet les certificats de certains domaines
    (api.insee.fr, api.openalex.org…) avec une autorité interne absente de certifi,
    tandis que le magasin Windows seul ne suffit pas pour d'autres (export.arxiv.org).
    """
    contexte = ssl.create_default_context(cafile=certifi.where())
    contexte.load_default_certs()
    return contexte
