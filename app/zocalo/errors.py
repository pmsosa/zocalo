"""How far off a simulated result is likely to be, and what kind of estimate that is.

Every number in the app carries one of these labels:
  measured  per-question-type error measured by this install's own tests (Tests page), on enough items
  prior     per-question-type error taken from published evaluations, until your own tests cover this type
  flat      overall error, when the question type isn't one we can estimate well
  human     a real confidence interval, because a real human sample was used (see calibration.py)
Never a sampling margin of error: adding simulated people does not shrink the model's bias.

Errors are in percentage points of an option's share: "usually within ±p50, 1 in 5 times more than ±p80".
"""
from __future__ import annotations

import math

import numpy as np

from . import db

QTYPES = ["opinion", "behaviour", "consumer", "knowledge", "other"]

# Starting values from published evaluations (docs/research.md): Pew Research Center 2026 silicon samples
# (mean error 12.4 pts, 28% of questions over 15), Verasight 2025 (about 4 pts on common political toplines,
# 10-30 on subgroups, 19.8 on consumer questions), Pew's knowledge items (+43 to +46 pts).
PRIORS = {
    ("opinion", 0): (7.0, 15.0),
    ("opinion", 1): (10.0, 22.0),
    ("behaviour", 0): (9.0, 18.0),
    ("behaviour", 1): (11.0, 23.0),
    ("consumer", 0): (12.0, 25.0),
    ("consumer", 1): (14.0, 28.0),
    ("knowledge", 0): (18.0, 40.0),
    ("knowledge", 1): (22.0, 45.0),
}
FLAT = (12.0, 25.0)
MIN_ITEMS = 20

KEYWORDS = {
    "knowledge": ["heard of", "have you heard", "do you know", "which of the following is", "how much have you heard",
                  "is it true", "who is", "what is the name", "has oído", "sabe usted", "conoce"],
    "consumer": ["buy", "pay", "price", "purchase", "subscribe", "$", "€", "brand", "cost", "comprar", "pagar",
                 "precio", "suscrib"],
    "behaviour": ["do you use", "have you ever", "how often", "do you own", "did you", "in the past",
                  "usa usted", "alguna vez", "con qué frecuencia", "tiene usted"],
}


def guess_qtype(text: str) -> str:
    t = text.lower()
    for qtype in ["knowledge", "consumer", "behaviour"]:
        if any(k in t for k in KEYWORDS[qtype]):
            return qtype
    return "opinion"


def _measured(qtype: str, topical: int) -> tuple[float, float, int, float | None] | None:
    rows = db.q("SELECT hi.abs_error, hi.meta_json FROM harness_items hi JOIN harness_runs hr ON hr.id=hi.run_id "
                "WHERE hr.status='done' AND hr.method='population' AND hi.qtype=? AND hi.subgroup IS NULL "
                "AND hi.abs_error IS NOT NULL", qtype)
    errs = np.array([r["abs_error"] for r in rows if (db.loads(r["meta_json"], {}).get("topical", 0) == topical)])
    if len(errs) < MIN_ITEMS:
        return None
    return float(np.percentile(errs, 50)), float(np.percentile(errs, 80)), len(errs), None


def subgroup_factor(n_people: int, is_subgroup: bool) -> float:
    if not is_subgroup:
        return 1.0
    # Subgroups err more (Pew: 16.1 pts for Republicans and 15.1 for Black adults vs 12.4 overall), and
    # small ones more again: segment gaps are exaggerated 2-4x (Chen et al. 2026).
    small = max(0.0, math.log10(max(1000 / max(n_people, 1), 1.0)))
    return 1.3 + 0.35 * small


def estimate(qtype: str, topical: bool, n_people: int, is_subgroup: bool, country: str = "US",
             demo: bool = False, n_models: int = 1) -> dict:
    qtype = qtype if qtype in QTYPES else "other"
    t = int(bool(topical))
    warnings = []
    kind, basis = "flat", "overall error across question types"
    p50, p80 = FLAT
    n_items = None
    if qtype != "other":
        m = _measured(qtype, t)
        if m:
            p50, p80, n_items, _ = m
            kind, basis = "measured", f"{qtype}{', topical' if t else ''} questions in this install's tests ({n_items} items)"
        else:
            p50, p80 = PRIORS[(qtype, t)]
            kind, basis = "prior", f"{qtype}{', topical' if t else ''} questions, from published evaluations (not yet tested here)"
    f = subgroup_factor(n_people, is_subgroup)
    if country not in ("US",):
        f *= 1.25
        warnings.append("non_us")
    if is_subgroup:
        warnings.append("subgroup")
    if qtype == "knowledge":
        warnings.append("knowledge")
    if demo:
        warnings.append("demo")
    return {"kind": kind, "p50": round(p50 * f, 1), "p80": round(p80 * f, 1), "basis": basis,
            "qtype": qtype, "topical": bool(t), "items": n_items, "warnings": warnings}
