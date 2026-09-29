"""Tirage déterministe d'une base de personas à partir du profil démographique réel.

Aucun appel au modèle : l'âge suit les tranches du recensement, la CSP suit la répartition
des 15 ans et plus (conditionnée par l'âge), le genre alterne. Le modèle n'enrichit ensuite
que les usages, les attentes et l'opinion.
"""

import random
import re
from typing import Any

# Répartition de repli des adultes par tranche d'âge (France, ordre de grandeur)
TRANCHES_DEFAUT = [
    ("18-29 ans", 18.0),
    ("30-44 ans", 24.0),
    ("45-59 ans", 25.0),
    ("60-74 ans", 21.0),
    ("75 ans et plus", 12.0),
]

CSP_DEFAUT = {
    "Agriculteurs exploitants": 0.8,
    "Artisans, commerçants, chefs d'entreprise": 3.7,
    "Cadres et professions intellectuelles supérieures": 10.0,
    "Professions intermédiaires": 14.5,
    "Employés": 15.5,
    "Ouvriers": 11.5,
    "Retraités": 27.0,
    "Autres personnes sans activité professionnelle": 17.0,
}

PRENOMS = {
    # (âge maximal de la génération) : (prénoms féminins, prénoms masculins)
    34: (
        ["Emma", "Léa", "Chloé", "Manon", "Camille", "Inès", "Jade", "Sarah", "Lina", "Zoé"],
        ["Lucas", "Hugo", "Théo", "Nathan", "Louis", "Mathis", "Enzo", "Yanis", "Adam", "Noah"],
    ),
    54: (
        [
            "Julie",
            "Aurélie",
            "Émilie",
            "Céline",
            "Sandrine",
            "Nadia",
            "Stéphanie",
            "Laure",
            "Sonia",
            "Élodie",
        ],
        [
            "Nicolas",
            "Julien",
            "Sébastien",
            "Mickaël",
            "Karim",
            "Thomas",
            "Guillaume",
            "David",
            "Fabien",
            "Samir",
        ],
    ),
    74: (
        [
            "Catherine",
            "Isabelle",
            "Sylvie",
            "Martine",
            "Nathalie",
            "Christine",
            "Françoise",
            "Brigitte",
            "Fatima",
            "Annie",
        ],
        [
            "Philippe",
            "Patrick",
            "Alain",
            "Michel",
            "Thierry",
            "Pascal",
            "Jean-Luc",
            "Didier",
            "Mohamed",
            "Gilles",
        ],
    ),
    200: (
        [
            "Monique",
            "Jacqueline",
            "Josiane",
            "Simone",
            "Colette",
            "Odette",
            "Paulette",
            "Yvette",
            "Denise",
            "Suzanne",
        ],
        [
            "Jean",
            "Bernard",
            "André",
            "Roger",
            "Marcel",
            "Gérard",
            "René",
            "Claude",
            "Robert",
            "Henri",
        ],
    ),
}

SITUATIONS = {
    "jeune": ["étudiant·e", "vit en colocation", "en couple, sans enfant", "vit seul·e"],
    "actif": [
        "en couple, deux enfants",
        "parent solo, un enfant",
        "vit seul·e",
        "en couple, sans enfant",
        "en couple, enfants partis",
        "famille recomposée",
    ],
    "senior": [
        "en couple, grands-parents",
        "veuf·ve, vit seul·e",
        "vit seul·e",
        "en couple, aidant·e d'un parent âgé",
    ],
}


def tranches_adultes(profil: dict[str, Any]) -> list[tuple[str, float]]:
    """Tranches d'âge adultes (18 ans et plus) du profil, au format {"15-24": 18.8, "80+": 4.6}.

    Une tranche à cheval sur 18 ans est ramenée à sa part adulte, au prorata des années.
    """
    tranches = []
    for libelle, part in (profil.get("tranches_age_pct") or {}).items():
        bornes = re.match(r"(\d+)(?:-(\d+)|\+)", str(libelle))
        if not bornes or not part:
            continue
        bas = int(bornes[1])
        haut = int(bornes[2]) if bornes[2] else None
        if haut is not None and haut < 18:
            continue
        if bas < 18:
            part = part * (haut - 17) / (haut - bas + 1) if haut else part
            bas = 18
        nom = f"{bas}-{haut} ans" if haut else f"{bas} ans et plus"
        tranches.append((nom, float(part)))
    return tranches or TRANCHES_DEFAUT


def _bornes(tranche: str) -> tuple[int, int]:
    nombres = [int(n) for n in re.findall(r"\d+", tranche)]
    return (nombres[0], nombres[1]) if len(nombres) > 1 else (nombres[0], nombres[0] + 12)


def _csp(age: int, repartition: dict[str, float], rng: random.Random) -> str:
    retraites = [c for c in repartition if c.lower().startswith("retrait")]
    sans_activite = [c for c in repartition if "sans activit" in c.lower()]
    actifs = {c: p for c, p in repartition.items() if c not in retraites + sans_activite and p > 0}
    if age >= 65 and retraites:
        return (
            retraites[0]
            if rng.random() < 0.9
            else rng.choices(list(actifs), list(actifs.values()))[0]
        )
    if age < 25 and sans_activite and rng.random() < 0.55:
        return "Étudiant·e"
    if 58 <= age < 65 and retraites and rng.random() < 0.35:
        return retraites[0]
    return rng.choices(list(actifs), list(actifs.values()))[0]


def generer_base(
    profil: dict[str, Any], lieu: str, nombre: int, graine: str
) -> list[dict[str, Any]]:
    """Base de `nombre` personas, reproductible pour une même graine (identifiant de session)."""
    rng = random.Random(graine)
    tranches = tranches_adultes(profil)
    total = sum(part for _, part in tranches)
    quotas = [(nom, round(part / total * nombre)) for nom, part in tranches]
    ages_tranches = [nom for nom, n in quotas for _ in range(n)]
    ages_tranches = (ages_tranches + [tranches[-1][0]] * nombre)[:nombre]
    repartition = profil.get("csp_15_ans_et_plus_pct") or CSP_DEFAUT

    personas = []
    for i, tranche in enumerate(ages_tranches):
        bas, haut = _bornes(tranche)
        age = rng.randint(bas, haut)
        genre = "femme" if i % 2 == 0 else "homme"
        generation = next(v for k, v in PRENOMS.items() if age <= k)
        prenom = rng.choice(generation[0] if genre == "femme" else generation[1])
        cle = "jeune" if age < 30 else "actif" if age < 62 else "senior"
        personas.append(
            {
                "prenom": prenom,
                "age": age,
                "genre": genre,
                "situation": rng.choice(SITUATIONS[cle]),
                "csp": _csp(age, repartition, rng),
                "lieu_de_vie": lieu,
            }
        )
    rng.shuffle(personas)
    return personas
