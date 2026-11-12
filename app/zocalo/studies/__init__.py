"""Studies: surveys, A/B tests and information treatments, run over a population or a saved panel.

Kinds
  survey     every selected person answers every question (stateless: no question sees another's answer)
  ab         matched halves of the panel; half A sees version A of each question, half B sees version B
  treatment  matched thirds: control (no news), treatment (the news), placebo (neutral news of similar length).
             Optional same-person mode runs alongside: a further group answers, reads the news, answers again in
             the same conversation. Reported effect = treatment minus placebo, never the raw change.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict

from .. import db
from ..population import age_band

ARMS = {"survey": ["main"], "ab": ["A", "B"], "treatment": ["control", "treatment", "placebo"]}
SUBGROUP_FIELDS = ["age_band", "sex", "region", "education", "party", "urban", "religion", "race", "country"]


def field_value(rec: dict, field: str):
    if field == "age_band":
        return age_band(rec.get("age"))
    return rec.get(field)


def matches(rec: dict, flt: dict) -> bool:
    if not flt:
        return True
    age = rec.get("age")
    if flt.get("age_min") is not None and (age is None or age < int(flt["age_min"])):
        return False
    if flt.get("age_max") is not None and (age is None or age > int(flt["age_max"])):
        return False
    for f, vals in (flt.get("fields") or {}).items():
        if vals and field_value(rec, f) not in vals:
            return False
    return True


def select_people(population_id: int, flt: dict | None, panel_id: int | None = None, size: int | None = None,
                  seed: int = 1) -> list[dict]:
    if panel_id:
        panel = db.q1("SELECT * FROM panels WHERE id=?", panel_id)
        ids = json.loads(panel["person_ids_json"]) if panel else []
        if not ids:
            return []
        rows = db.q(f"SELECT * FROM people WHERE id IN ({','.join('?' * len(ids))}) ORDER BY id", *ids)
    else:
        rows = db.q("SELECT * FROM people WHERE population_id=? ORDER BY id", population_id)
    out = []
    for r in rows:
        rec = json.loads(r["base_json"])
        if matches(rec, flt or {}):
            r["rec"] = rec
            out.append(r)
    if size and size < len(out):
        rng = random.Random(seed)
        out = rng.sample(out, size)
        out.sort(key=lambda r: r["id"])
    return out


def assign_arms(people: list[dict], arms: list[str], seed: int) -> dict[int, str]:
    """Matched assignment: sort into strata (age band, sex, region, education), shuffle within, deal round-robin."""
    if len(arms) == 1:
        return {p["id"]: arms[0] for p in people}
    rng = random.Random(seed)
    strata = defaultdict(list)
    for p in people:
        r = p["rec"]
        strata[(age_band(r.get("age")), r.get("sex"), r.get("region"), r.get("education"))].append(p)
    order = []
    for key in sorted(strata, key=str):
        group = strata[key]
        rng.shuffle(group)
        order.extend(group)
    start = rng.randrange(len(arms))
    return {p["id"]: arms[(start + i) % len(arms)] for i, p in enumerate(order)}


def study_seed(study_id: int) -> int:
    return int(hashlib.sha256(f"study-{study_id}".encode()).hexdigest()[:8], 16)


def get(study_id: int) -> dict | None:
    s = db.q1("SELECT * FROM studies WHERE id=?", study_id)
    if not s:
        return None
    s["filter"] = db.loads(s.pop("filter_json"), {})
    s["config"] = db.loads(s.pop("config_json"), {})
    s["questions"] = [dict(q, options=json.loads(q.pop("options_json")), meta=db.loads(q.pop("meta_json"), {}))
                      for q in db.q("SELECT * FROM questions WHERE study_id=? ORDER BY idx", study_id)]
    pop = db.q1("SELECT id,name,country,source,size FROM populations WHERE id=?", s["population_id"])
    s["population"] = pop
    return s


def create(data: dict) -> int:
    from ..answering import with_unsure
    from ..errors import guess_qtype
    kind = data.get("kind", "survey")
    if kind not in ARMS:
        raise ValueError("unknown study kind")
    lang = data.get("lang", "en")
    with db.tx() as con:
        cur = con.execute(
            "INSERT INTO studies(name,kind,population_id,panel_id,filter_json,config_json,status,created_at) "
            "VALUES(?,?,?,?,?,?,?,?)", (data.get("name") or "Untitled study", kind, int(data["population_id"]),
            data.get("panel_id"), json.dumps(data.get("filter") or {}), json.dumps(data.get("config") or {}),
            "draft", db.now()))
        sid = cur.lastrowid
        for i, qd in enumerate(data.get("questions") or []):
            opts = with_unsure(qd.get("options") or [], lang) if qd.get("include_unsure", True) else qd["options"]
            meta = {"ordered": bool(qd.get("ordered")), "text_b": qd.get("text_b") or None}
            con.execute("INSERT INTO questions(study_id,idx,text,options_json,qtype,topical,meta_json) VALUES(?,?,?,?,?,?,?)",
                        (sid, i, qd["text"].strip(), json.dumps(opts, ensure_ascii=False),
                         qd.get("qtype") or guess_qtype(qd["text"]), int(bool(qd.get("topical"))), json.dumps(meta)))
    return sid


def clone_people_ids(study: dict) -> list[int]:
    cfg = study["config"]
    people = select_people(study["population_id"], study["filter"], study.get("panel_id"), cfg.get("size"),
                           study_seed(study["id"]))
    return [p["id"] for p in people]
