"""Demo populations: made-up people for trying the app before any dataset is downloaded.

These are NOT built from census records. Each person is drawn from rough, rounded country-level shares (region,
age, education, work, settlement, religion, broad political leaning), with a few simple dependencies (students are
young, retirees are old). They are labelled "demo" everywhere in the app, and their results carry a warning.
Use them to learn the interface; use a real population (Data page) for anything you want to rely on.
"""
from __future__ import annotations

import random

ADULT_AGES = [(18, 24, 12), (25, 34, 18), (35, 44, 17), (45, 54, 16), (55, 64, 16), (65, 74, 13), (75, 90, 8)]

COUNTRIES: dict[str, dict] = {
    "US": {"name": "United States",
           "regions": [("California", 12), ("Texas", 9), ("Florida", 7), ("New York", 6), ("Pennsylvania", 4),
                       ("Illinois", 4), ("Ohio", 3.5), ("Georgia", 3.3), ("North Carolina", 3.2), ("Michigan", 3),
                       ("New Jersey", 2.8), ("Virginia", 2.6), ("Washington", 2.3), ("Arizona", 2.3),
                       ("Tennessee", 2.1), ("Massachusetts", 2.1), ("Colorado", 1.8), ("Wisconsin", 1.8),
                       ("Minnesota", 1.7), ("Alabama", 1.5), ("Oregon", 1.3), ("Iowa", 1), ("Nevada", 1),
                       ("Other states", 18)],
           "education": [("high school or less", 37), ("some college", 26), ("bachelor's degree", 23), ("graduate degree", 14)],
           "urban": [("a city", 31), ("a suburb", 52), ("a rural area", 17)],
           "religion": [("Protestant", 40), ("Catholic", 20), ("no religion", 29), ("other religion", 11)],
           "party": [("Democrat", 31), ("Republican", 30), ("independent", 39)],
           "race": [("White", 59), ("Hispanic", 19), ("Black", 12), ("Asian", 6), ("other or mixed", 4)]},
    "MX": {"name": "México",
           "regions": [("Estado de México", 13.5), ("Ciudad de México", 7.3), ("Jalisco", 6.6), ("Veracruz", 6),
                       ("Puebla", 5.2), ("Guanajuato", 4.9), ("Nuevo León", 4.6), ("Chiapas", 4.4), ("Michoacán", 3.8),
                       ("Oaxaca", 3.3), ("Chihuahua", 3), ("Guerrero", 2.8), ("Baja California", 3), ("Otros estados", 31.6)],
           "education": [("primaria o menos", 30), ("secundaria", 27), ("preparatoria", 23), ("universidad", 20)],
           "urban": [("una ciudad", 79), ("una zona rural", 21)],
           "religion": [("católica", 78), ("evangélica/cristiana", 11), ("sin religión", 9), ("otra", 2)],
           "party": [("Morena", 40), ("PAN", 17), ("PRI", 12), ("Movimiento Ciudadano", 9), ("ninguno", 22)]},
    "GB": {"name": "United Kingdom",
           "regions": [("London", 13.4), ("South East", 13.8), ("North West", 11), ("East of England", 9.4),
                       ("West Midlands", 8.9), ("South West", 8.5), ("Yorkshire and the Humber", 8.2),
                       ("Scotland", 8.1), ("East Midlands", 7.3), ("Wales", 4.6), ("North East", 4), ("Northern Ireland", 2.8)],
           "education": [("no qualifications or GCSEs", 34), ("A levels or vocational", 30), ("degree", 36)],
           "urban": [("a city or town", 82), ("a rural area", 18)],
           "religion": [("no religion", 46), ("Christian", 42), ("Muslim", 7), ("other religion", 5)],
           "party": [("Labour", 30), ("Conservative", 22), ("Reform UK", 16), ("Liberal Democrat", 11), ("Green", 8), ("none", 13)]},
    "DE": {"name": "Deutschland",
           "regions": [("Nordrhein-Westfalen", 21.5), ("Bayern", 15.9), ("Baden-Württemberg", 13.4), ("Niedersachsen", 9.6),
                       ("Hessen", 7.6), ("Sachsen", 4.9), ("Rheinland-Pfalz", 4.9), ("Berlin", 4.4), ("Schleswig-Holstein", 3.5),
                       ("Brandenburg", 3), ("Sachsen-Anhalt", 2.6), ("Thüringen", 2.5), ("Hamburg", 2.2), ("other", 4)],
           "education": [("Hauptschule", 28), ("Realschule", 29), ("Abitur", 18), ("university degree", 25)],
           "urban": [("a city", 77), ("a rural area", 23)],
           "religion": [("no religion", 43), ("Catholic", 24), ("Protestant", 22), ("Muslim", 6), ("other", 5)],
           "party": [("CDU/CSU", 28), ("AfD", 20), ("SPD", 16), ("Greens", 11), ("Die Linke", 8), ("none", 17)]},
    "BR": {"name": "Brasil",
           "regions": [("São Paulo", 21.9), ("Minas Gerais", 10), ("Rio de Janeiro", 7.9), ("Bahia", 6.9), ("Paraná", 5.6),
                       ("Rio Grande do Sul", 5.3), ("Pernambuco", 4.6), ("Ceará", 4.3), ("Pará", 4), ("outros estados", 29.5)],
           "education": [("fundamental ou menos", 40), ("ensino médio", 37), ("superior", 23)],
           "urban": [("uma cidade", 87), ("uma área rural", 13)],
           "religion": [("católica", 50), ("evangélica", 31), ("sem religião", 10), ("outra", 9)],
           "party": [("PT", 28), ("PL", 22), ("MDB", 8), ("nenhum", 42)]},
    "IN": {"name": "India",
           "regions": [("Uttar Pradesh", 16.5), ("Maharashtra", 9.3), ("Bihar", 8.6), ("West Bengal", 7.5), ("Madhya Pradesh", 6),
                       ("Tamil Nadu", 6), ("Rajasthan", 5.7), ("Karnataka", 5), ("Gujarat", 5), ("Andhra Pradesh", 4.1),
                       ("other states", 26.3)],
           "education": [("no schooling", 22), ("primary", 18), ("secondary", 38), ("graduate", 22)],
           "urban": [("a city", 36), ("a village", 64)],
           "religion": [("Hindu", 79), ("Muslim", 14), ("Christian", 2.3), ("Sikh", 1.7), ("other", 3)],
           "party": [("BJP", 37), ("Congress", 21), ("regional party", 30), ("none", 12)]},
}

EMPLOYMENT = {"en": ["working full-time", "working part-time", "self-employed", "unemployed", "homemaker", "student", "retired"],
              "es": ["trabaja tiempo completo", "trabaja medio tiempo", "trabaja por su cuenta", "desempleado/a",
                     "se dedica al hogar", "estudiante", "jubilado/a"]}
OCCUPATIONS = ["nurse", "truck driver", "teacher", "software developer", "cashier", "electrician", "accountant",
               "home health aide", "farmer", "cook", "sales manager", "mechanic", "pharmacist", "warehouse worker",
               "real estate agent", "police officer", "graphic designer", "machinist", "dental hygienist",
               "small business owner", "construction worker", "office clerk", "cleaner", "engineer"]


def _pick(rng: random.Random, items):
    total = sum(w for _, w in items)
    r = rng.random() * total
    for v, w in items:
        r -= w
        if r <= 0:
            return v
    return items[-1][0]


def build(country: str, n: int, seed: int) -> list[dict]:
    c = COUNTRIES[country]
    rng = random.Random(seed)
    es_like = country in ("MX",)
    out = []
    for i in range(n):
        lo, hi = _pick(rng, [((a, b), w) for a, b, w in ADULT_AGES])
        age = rng.randint(lo, hi)
        sex = "female" if rng.random() < 0.51 else "male"
        edu_items = c["education"]
        if age < 23:  # young adults haven't finished degrees yet
            edu_items = edu_items[:-1] if len(edu_items) > 2 else edu_items
        emp_pool = EMPLOYMENT["es" if es_like else "en"]
        if age >= 66:
            emp = emp_pool[6] if rng.random() < 0.8 else emp_pool[1]
        elif age < 23 and rng.random() < 0.55:
            emp = emp_pool[5]
        else:
            emp = _pick(rng, list(zip(emp_pool[:5], [52, 12, 10, 6, 8])))
        rec = {
            "country": country, "country_name": c["name"], "region": _pick(rng, c["regions"]), "age": age,
            "sex": sex, "education": _pick(rng, edu_items), "employment": emp,
            "occupation": rng.choice(OCCUPATIONS) if emp in (emp_pool[0], emp_pool[1], emp_pool[2]) else None,
            "urban": _pick(rng, c["urban"]), "religion": _pick(rng, c["religion"]),
            "party": _pick(rng, c["party"]),
            "provenance": {"kind": "demo", "ref": f"demo-{country}-{seed}-{i}",
                           "note": "Synthetic demo person drawn from rounded country shares. Not a census record."},
        }
        if "race" in c:
            rec["race"] = _pick(rng, c["race"])
        out.append(rec)
    return out
