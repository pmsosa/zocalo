"""Turning answers into results: shares, labelled error, effects, checks and subgroup breakdowns."""
from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict

import numpy as np

from .. import db, errors
from ..population import age_band, summary
from . import SUBGROUP_FIELDS, field_value, get, matches


def _sampled_choice(spread: list[float], key: tuple) -> int:
    rng = random.Random(int(hashlib.sha256(repr(key).encode()).hexdigest()[:10], 16))
    r, acc = rng.random(), 0.0
    for i, p in enumerate(spread):
        acc += p
        if r <= acc:
            return i
    return len(spread) - 1


def _share(rows: list[dict], n_opts: int) -> np.ndarray:
    if not rows:
        return np.zeros(n_opts)
    w = np.array([r["weight"] for r in rows], dtype=float)
    s = np.array([r["spread"] for r in rows], dtype=float)
    return (s * w[:, None]).sum(0) / max(w.sum(), 1e-9)


def compute(study_id: int, flt: dict | None = None, lang: str = "en") -> dict:
    from ..calibration import anchors_for, human_estimate
    study = get(study_id)
    if not study:
        raise KeyError(study_id)
    pop = study["population"] or {}
    demo = pop.get("source") == "demo"
    country = pop.get("country", "US")
    is_sub = bool(flt) or bool(study["filter"]) or bool(study.get("panel_id"))
    rows = db.q("SELECT a.question_id, a.person_id, a.arm, a.model_ref, a.spread_json, a.answer_idx, a.reason, "
                "p.base_json, p.weight, p.name FROM answers a JOIN people p ON p.id=a.person_id "
                "WHERE a.study_id=? AND a.ok=1", study_id)
    people: dict[int, dict] = {}
    by_q: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        if r["person_id"] not in people:
            people[r["person_id"]] = {"id": r["person_id"], "name": r["name"], "rec": json.loads(r["base_json"]),
                                      "weight": r["weight"], "answers": {}}
        person = people[r["person_id"]]
        if flt and not matches(person["rec"], flt):
            continue
        r["spread"] = json.loads(r["spread_json"])
        by_q[r["question_id"]].append(r)
    fails = db.q1("SELECT COUNT(*) AS n FROM answers WHERE study_id=? AND ok=0", study_id)["n"]
    models = sorted({r["model_ref"] for r in rows})
    out_q = []
    for q in study["questions"]:
        n_opts = len(q["options"])
        qrows = by_q.get(q["id"], [])
        # average each person's spread across models (each model is one "reading" of the same person)
        per_person_arm: dict[tuple, list] = defaultdict(list)
        for r in qrows:
            per_person_arm[(r["person_id"], r["arm"])].append(r)
        merged = []
        for (pid, arm), rs in per_person_arm.items():
            spread = np.mean([x["spread"] for x in rs], axis=0).tolist()
            merged.append({"person_id": pid, "arm": arm, "spread": spread, "weight": rs[0]["weight"],
                           "reason": rs[0]["reason"]})
            ans = people[pid]["answers"].setdefault(str(q["id"]), {})
            ans[arm] = {"spread": [round(x, 3) for x in spread], "pick": _sampled_choice(spread, (study_id, q["id"], pid, arm)),
                        "reason": rs[0]["reason"]}
        arms = sorted({m["arm"] for m in merged}, key=lambda a: ["main", "A", "B", "control", "treatment", "placebo",
                                                                 "within_before", "within_after"].index(a)
                      if a in ["main", "A", "B", "control", "treatment", "placebo", "within_before", "within_after"] else 99)
        arm_res = {}
        for arm in arms:
            ar = [m for m in merged if m["arm"] == arm]
            share = _share(ar, n_opts)
            picks = np.bincount([_sampled_choice(m["spread"], (study_id, q["id"], m["person_id"], arm)) for m in ar],
                                minlength=n_opts)
            per_model = {}
            if len(models) > 1:
                for mref in models:
                    mr = [r for r in qrows if r["arm"] == arm and r["model_ref"] == mref]
                    per_model[mref] = [round(float(x), 4) for x in _share(mr, n_opts)]
            arm_res[arm] = {
                "share": [round(float(x), 4) for x in share], "n": len(ar), "picks": picks.tolist(),
                "per_model": per_model,
                "error": errors.estimate(q["qtype"], bool(q["topical"]), len(ar), is_sub, country, demo, len(models)),
            }
        main_arm = "main" if "main" in arm_res else ("A" if "A" in arm_res else ("treatment" if "treatment" in arm_res else (arms[0] if arms else None)))
        checks = {}
        if main_arm:
            share = np.array(arm_res[main_arm]["share"])
            checks = {
                "rare_options": [i for i, s in enumerate(share) if s < 0.01],
                "unsure_share": float(share[-1]) if n_opts else 0.0,
                "mean_confidence": round(float(np.mean([max(m["spread"]) for m in merged if m["arm"] == main_arm])), 3)
                if merged else None,
            }
        effects = {}
        if study["kind"] == "treatment":
            def diff(a, b):
                if a in arm_res and b in arm_res:
                    return [round(x - y, 4) for x, y in zip(arm_res[a]["share"], arm_res[b]["share"])]
            effects = {"treatment_vs_placebo": diff("treatment", "placebo"), "treatment_vs_control": diff("treatment", "control"),
                       "placebo_vs_control": diff("placebo", "control"), "within_shift": diff("within_after", "within_before")}
        elif study["kind"] == "ab":
            if "A" in arm_res and "B" in arm_res:
                effects = {"b_vs_a": [round(x - y, 4) for x, y in zip(arm_res["B"]["share"], arm_res["A"]["share"])]}
        subgroups = {}
        if main_arm:
            ar = [m for m in merged if m["arm"] == main_arm]
            for f in SUBGROUP_FIELDS:
                groups = defaultdict(list)
                for m in ar:
                    v = field_value(people[m["person_id"]]["rec"], f)
                    if v not in (None, "", "unknown"):
                        groups[v].append(m)
                if 1 < len(groups) <= 30:
                    subgroups[f] = sorted([{"value": v, "n": len(g), "share": [round(float(x), 4) for x in _share(g, n_opts)],
                                            "error": errors.estimate(q["qtype"], bool(q["topical"]), len(g), True, country, demo)["p50"]}
                                           for v, g in groups.items()], key=lambda d: -d["n"])
        out_q.append({"id": q["id"], "text": q["text"], "text_b": q["meta"].get("text_b"), "options": q["options"],
                      "qtype": q["qtype"], "topical": bool(q["topical"]), "ordered": q["meta"].get("ordered", False),
                      "arms": arm_res, "main_arm": main_arm, "effects": effects, "checks": checks, "subgroups": subgroups,
                      "anchors": anchors_for(q["text"], country, limit=3),
                      "human": human_estimate(study_id, q, merged, main_arm)})
    people_out = []
    for p in people.values():
        if flt and not matches(p["rec"], flt):
            continue
        rec = p["rec"]
        people_out.append({"id": p["id"], "name": p["name"], "summary": summary(rec),
                           "f": {k: field_value(rec, k) for k in ["age", "age_band", "sex", "region", "education", "party",
                                                                    "urban", "religion", "race", "country", "occupation",
                                                                    "employment", "vote_last"]},
                           "answers": p["answers"]})
    from ..providers import model_name
    return {"study": {k: study[k] for k in ["id", "name", "kind", "status", "progress", "status_msg", "cost_actual",
                                            "cost_estimate", "created_at", "finished_at", "config", "filter", "population"]},
            "models": [{"ref": m, "name": model_name(m)} for m in models], "failed": fails,
            "questions": out_q, "people": people_out}
