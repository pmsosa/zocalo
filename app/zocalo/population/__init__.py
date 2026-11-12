"""People and populations.

A person's base record is written once and never changed. It holds demographics (from a census record, or a survey
respondent), optional attitudes (the person's own answers, or matched from an opinion survey), and provenance:
where every fact came from. Branches layer changes on top (see `effective_record`).

Names are display labels only, drawn from per-country name lists. They are not sent to the model, because
identity-coded names push models toward stereotypes.
"""
from __future__ import annotations

import copy
import json
import random

from .. import db

FIELDS = ["country", "region", "age", "sex", "education", "income", "employment", "occupation", "race",
          "marital", "urban", "household", "religion", "religiosity", "party", "ideology", "vote_last"]

FIELD_LABELS = {
    "en": {"country": "Country", "region": "Region", "age": "Age", "sex": "Sex", "education": "Education",
           "income": "Household income", "employment": "Work", "occupation": "Occupation", "race": "Race/ethnicity",
           "marital": "Marital status", "urban": "Lives in", "household": "Household", "religion": "Religion",
           "religiosity": "Religious practice", "party": "Party", "ideology": "Political views",
           "vote_last": "Last vote"},
    "es": {"country": "País", "region": "Región", "age": "Edad", "sex": "Sexo", "education": "Estudios",
           "income": "Ingreso del hogar", "employment": "Trabajo", "occupation": "Ocupación", "race": "Raza/etnia",
           "marital": "Estado civil", "urban": "Vive en", "household": "Hogar", "religion": "Religión",
           "religiosity": "Práctica religiosa", "party": "Partido", "ideology": "Ideas políticas",
           "vote_last": "Último voto"},
}

AGE_BANDS = [(18, 29, "18–29"), (30, 44, "30–44"), (45, 64, "45–64"), (65, 120, "65+")]


def age_band(age: int | None) -> str:
    if age is None:
        return "unknown"
    for lo, hi, label in AGE_BANDS:
        if lo <= age <= hi:
            return label
    return "under 18"


# ---------- branches ----------
def effective_record(person: dict, branch_id: int | None) -> tuple[dict, list[dict]]:
    """The base record with every branch overlay on the path applied, plus the list of branches applied."""
    base = json.loads(person["base_json"]) if isinstance(person.get("base_json"), str) else person["base"]
    rec = copy.deepcopy(base)
    chain: list[dict] = []
    bid = branch_id
    while bid:
        b = db.q1("SELECT * FROM branches WHERE id=?", bid)
        if not b:
            break
        chain.append(b)
        bid = b["parent_id"]
    for b in reversed(chain):
        ov = json.loads(b["overlay_json"])
        for k, v in ov.get("set", {}).items():
            rec[k] = v
        rec.setdefault("context", []).extend(ov.get("context", []))
    return rec, chain


def new_branch(person_id: int, name: str, overlay: dict | None = None, parent_id: int | None = None) -> int:
    return db.ex("INSERT INTO branches(person_id,parent_id,name,overlay_json,created_at) VALUES(?,?,?,?,?)",
                 person_id, parent_id, name, json.dumps(overlay or {}), db.now())


# ---------- the profile the model sees ----------
def profile_text(rec: dict) -> str:
    """Facts only, one per line. Nothing here is invented: every line comes from a record field."""
    L = FIELD_LABELS["en"]
    lines = []
    if rec.get("age") is not None:
        lines.append(f"Age: {rec['age']}")
    for k in ["sex", "country", "region", "urban", "education", "employment", "occupation", "income", "household",
              "marital", "race", "religion", "religiosity", "party", "ideology", "vote_last"]:
        v = rec.get(k)
        if v not in (None, "", "unknown"):
            lines.append(f"{L[k]}: {v}")
    views = rec.get("views") or []
    if views:
        lines.append("Some of this person's own past survey answers:")
        for item in views[:24]:
            lines.append(f"- {item['q']} → {item['a']}")
    if rec.get("background"):
        lines.append(f"Background (paraphrased from the record above, nothing added): {rec['background']}")
    for c in rec.get("context") or []:
        lines.append(f"Recently: {c}")
    return "\n".join(lines)


def summary(rec: dict, lang: str = "en") -> str:
    bits = [str(rec.get("age")) if rec.get("age") is not None else None, rec.get("occupation") or rec.get("employment"),
            ", ".join(x for x in [rec.get("region"), rec.get("country_name") or rec.get("country")] if x)]
    return " · ".join(b for b in bits if b)


# ---------- names (display only) ----------
NAMES = {
    "en": (["Maria", "Linda", "Aisha", "Jennifer", "Rosa", "Emily", "Keisha", "Hannah", "Priya", "Donna", "Megan", "Grace",
            "Tanya", "Ruth", "Sofia", "Brittany", "Mei", "Carol", "Dana", "Olivia", "Fatima", "Chloe", "Nadia", "Joan"],
           ["James", "Luis", "Robert", "Darnell", "Kevin", "Tyler", "Jose", "Michael", "Raj", "Gary", "Brandon", "Wei",
            "Dennis", "Marcus", "Cody", "Ahmed", "Frank", "Diego", "Paul", "Ethan", "Omar", "Liam", "Victor", "Sam"],
           ["Garcia", "Smith", "Nguyen", "Johnson", "Patel", "Brown", "Martinez", "Williams", "Kim", "Davis", "Lopez",
            "Miller", "Okafor", "Wilson", "Rivera", "Anderson", "Chen", "Thomas", "Hernandez", "Moore", "Clark", "Reyes"]),
    "es": (["María", "Guadalupe", "Lucía", "Sofía", "Fernanda", "Daniela", "Rosa", "Ana", "Paola", "Carmen", "Valeria",
            "Ximena", "Andrea", "Luz", "Gabriela", "Elena", "Mariana", "Patricia", "Julieta", "Alejandra"],
           ["José", "Juan", "Luis", "Carlos", "Miguel", "Jorge", "Alejandro", "Diego", "Fernando", "Ricardo", "Javier",
            "Raúl", "Manuel", "Pedro", "Andrés", "Emiliano", "Santiago", "Héctor", "Arturo", "Mateo"],
           ["Hernández", "García", "Martínez", "López", "González", "Pérez", "Rodríguez", "Sánchez", "Ramírez", "Cruz",
            "Flores", "Gómez", "Morales", "Vázquez", "Reyes", "Jiménez", "Torres", "Díaz", "Ruiz", "Mendoza"]),
    "pt": (["Ana", "Maria", "Juliana", "Fernanda", "Camila", "Beatriz", "Larissa", "Patrícia", "Aline", "Gabriela"],
           ["João", "Pedro", "Lucas", "Gabriel", "Rafael", "Bruno", "Thiago", "Felipe", "Mateus", "Carlos"],
           ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Ferreira", "Almeida", "Rodrigues"]),
    "de": (["Anna", "Julia", "Katrin", "Laura", "Sabine", "Lea", "Monika", "Sarah", "Petra", "Lena"],
           ["Thomas", "Michael", "Jonas", "Lukas", "Stefan", "Andreas", "Felix", "Jan", "Markus", "Paul"],
           ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Hoffmann", "Schulz"]),
    "fr": (["Camille", "Léa", "Manon", "Chloé", "Inès", "Sophie", "Julie", "Claire", "Emma", "Nathalie"],
           ["Lucas", "Hugo", "Thomas", "Nicolas", "Julien", "Antoine", "Louis", "Pierre", "Karim", "Théo"],
           ["Martin", "Bernard", "Dubois", "Durand", "Moreau", "Laurent", "Simon", "Michel", "Lefèvre", "Garcia"]),
    "hi": (["Priya", "Anjali", "Sunita", "Pooja", "Neha", "Kavita", "Ananya", "Lakshmi", "Meera", "Divya"],
           ["Rahul", "Amit", "Arjun", "Vikram", "Suresh", "Rohan", "Sanjay", "Ravi", "Karan", "Imran"],
           ["Sharma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Iyer", "Das", "Khan", "Nair"]),
    "ja": (["Yui", "Haruka", "Sakura", "Aoi", "Mei", "Yuki", "Emi", "Rin", "Naoko", "Keiko"],
           ["Haruto", "Ren", "Sota", "Yuto", "Takashi", "Kenji", "Daiki", "Hiroshi", "Kaito", "Shota"],
           ["Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kobayashi", "Kato"]),
}
COUNTRY_NAME_LANG = {"MX": "es", "ES": "es", "AR": "es", "CO": "es", "CL": "es", "PE": "es", "BR": "pt", "PT": "pt",
                     "DE": "de", "AT": "de", "FR": "fr", "IN": "hi", "JP": "ja"}


def make_name(country: str, sex: str | None, rng: random.Random) -> str:
    first_f, first_m, last = NAMES[COUNTRY_NAME_LANG.get(country, "en")]
    first = rng.choice(first_f if sex == "female" else first_m if sex == "male" else first_f + first_m)
    return f"{first} {rng.choice(last)}"


def save_population(name: str, country: str, source: str, records: list[dict], seed: int, meta: dict) -> int:
    rng = random.Random(seed)
    weights = [float(r.pop("_weight", 1.0)) for r in records]
    with db.tx() as con:
        cur = con.execute("INSERT INTO populations(name,country,source,size,seed,status,meta_json,created_at) "
                          "VALUES(?,?,?,?,?,?,?,?)", (name, country, source, len(records), seed, "ready",
                          json.dumps(meta), db.now()))
        pid = cur.lastrowid
        con.executemany(
            "INSERT INTO people(population_id,name,base_json,weight,source_ref) VALUES(?,?,?,?,?)",
            [(pid, make_name(r.get("country", country), r.get("sex"), rng), json.dumps(r, ensure_ascii=False),
              w, r.get("provenance", {}).get("ref")) for r, w in zip(records, weights)])
    return pid


def person_view(p: dict, lang: str = "en") -> dict:
    rec = json.loads(p["base_json"])
    return {"id": p["id"], "name": p["name"], "weight": p["weight"], "record": rec, "summary": summary(rec, lang)}
