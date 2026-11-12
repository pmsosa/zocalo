"""Calibration: anchors to real polls, and correction with a real human sample.

1. Weighting. Populations are drawn from census and survey records in proportion to their official weights, so
   a population is self-weighting. That is hygiene, not a fix: weighting does not remove model bias.
2. Anchors. Every downloaded opinion survey adds its questions and real answer shares to an index. A new question
   is matched to its closest real questions (TF-IDF cosine similarity). Anchors are shown next to results so you
   can compare. Whether shifting simulated answers toward anchors helps is an open experiment (Tests page); it is
   not applied to results by default.
3. Human-sample correction (prediction-powered inference). Import real answers to the same question from a small
   human sample. Each human is paired with the most similar simulated person; the average gap between real and
   simulated answers corrects the simulated share, and the interval is a real 95% confidence interval.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter

import numpy as np

from . import db

_index: dict = {"version": -1}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-záéíóúñüçàèâêôãõ0-9]+", text.lower())
    stop = {"the", "a", "an", "of", "to", "in", "and", "or", "you", "your", "do", "is", "are", "be", "for", "on",
            "that", "this", "with", "would", "how", "what", "which", "el", "la", "los", "las", "de", "y", "o", "en",
            "que", "usted", "su", "un", "una", "por", "para", "es", "se"}
    toks = [w for w in words if w not in stop and len(w) > 1]
    return toks + [a + "_" + b for a, b in zip(toks, toks[1:])]


def _build_index() -> dict:
    version = db.q1("SELECT COUNT(*) AS n, COALESCE(MAX(id),0) AS m FROM anchors")
    key = (version["n"], version["m"])
    if _index.get("version") == key:
        return _index
    rows = db.q("SELECT id, source, ref, country, year, text, options_json, dist_json FROM anchors")
    docs = [Counter(_tokens(r["text"])) for r in rows]
    df = Counter(t for d in docs for t in d)
    n = max(len(docs), 1)
    vocab = {t: i for i, t in enumerate(df)}
    idf = np.array([math.log((1 + n) / (1 + df[t])) + 1 for t in vocab]) if vocab else np.zeros(0)
    mat = np.zeros((len(docs), len(vocab)), dtype=np.float32)
    for i, d in enumerate(docs):
        for t, c in d.items():
            mat[i, vocab[t]] = (1 + math.log(c)) * idf[vocab[t]]
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    mat = mat / np.maximum(norms, 1e-9)
    _index.update(version=key, rows=rows, vocab=vocab, idf=idf, mat=mat)
    return _index


def anchors_for(text: str, country: str | None = None, limit: int = 3) -> list[dict]:
    idx = _build_index()
    if not idx.get("rows"):
        return []
    v = np.zeros(len(idx["vocab"]), dtype=np.float32)
    for t, c in Counter(_tokens(text)).items():
        if t in idx["vocab"]:
            v[idx["vocab"][t]] = (1 + math.log(c)) * idx["idf"][idx["vocab"][t]]
    nv = np.linalg.norm(v)
    if nv == 0:
        return []
    sims = idx["mat"] @ (v / nv)
    if country:  # prefer the same country, but keep strong matches from elsewhere
        boost = np.array([0.05 if r["country"] == country else 0.0 for r in idx["rows"]])
        sims = sims + boost
    order = np.argsort(-sims)[: limit * 4]
    out, seen = [], set()
    for i in order:
        r = idx["rows"][int(i)]
        if sims[i] < 0.15 or (r["source"], r["ref"]) in seen:
            continue
        seen.add((r["source"], r["ref"]))
        out.append({"source": r["source"], "ref": r["ref"], "country": r["country"], "year": r["year"],
                    "text": r["text"], "options": json.loads(r["options_json"]), "dist": json.loads(r["dist_json"]),
                    "similarity": round(float(min(sims[i], 1.0)), 3),
                    "closeness": "close" if sims[i] >= 0.55 else "some" if sims[i] >= 0.3 else "distant"})
        if len(out) >= limit:
            break
    return out


def add_anchors(items: list[dict]) -> int:
    with db.tx() as con:
        con.executemany(
            "INSERT OR REPLACE INTO anchors(source,ref,country,year,text,options_json,dist_json) VALUES(?,?,?,?,?,?,?)",
            [(i["source"], i["ref"], i.get("country"), i.get("year"), i["text"], json.dumps(i["options"], ensure_ascii=False),
              json.dumps(i["dist"])) for i in items])
    return len(items)


# ---------- human-sample correction ----------
MATCH_FIELDS = ["sex", "age", "region", "education", "party", "race", "country"]


def _similarity(h: dict, rec: dict) -> float:
    s = 0.0
    for f in MATCH_FIELDS:
        hv, rv = h.get(f), rec.get(f)
        if hv in (None, "") or rv in (None, ""):
            continue
        if f == "age":
            try:
                s += max(0.0, 1 - abs(float(hv) - float(rv)) / 15)
            except ValueError:
                pass
        elif str(hv).strip().lower() == str(rv).strip().lower():
            s += 1.0
    return s


def human_estimate(study_id: int, q: dict, merged: list[dict], arm: str | None) -> dict | None:
    row = db.q1("SELECT rows_json FROM human_samples WHERE study_id=? AND question_id=? ORDER BY id DESC LIMIT 1",
                study_id, q["id"])
    if not row or not arm:
        return None
    humans = json.loads(row["rows_json"])
    sims = [m for m in merged if m["arm"] == arm]
    if not humans or not sims:
        return None
    recs = {m["person_id"]: json.loads(db.q1("SELECT base_json FROM people WHERE id=?", m["person_id"])["base_json"])
            for m in sims}
    n_opts = len(q["options"])
    labels = [o.strip().lower() for o in q["options"]]
    diffs = []
    for h in humans:
        ans = str(h.get("answer", "")).strip().lower()
        if ans.isdigit() and int(ans) < n_opts:
            k = int(ans)
        elif ans in labels:
            k = labels.index(ans)
        else:
            continue
        best = max(sims, key=lambda m: _similarity(h, recs[m["person_id"]]))
        onehot = np.zeros(n_opts)
        onehot[k] = 1
        diffs.append(onehot - np.array(best["spread"]))
    if len(diffs) < 10:
        return {"n": len(diffs), "error": "too_few"}
    diffs = np.array(diffs)
    sim_all = np.array([m["spread"] for m in sims])
    theta = sim_all.mean(0) + diffs.mean(0)
    se = np.sqrt(sim_all.var(0, ddof=1) / len(sim_all) + diffs.var(0, ddof=1) / len(diffs))
    theta = np.clip(theta, 0, 1)
    return {"n": len(diffs), "share": [round(float(x), 4) for x in theta],
            "ci95": [round(float(1.96 * s * 100), 1) for s in se],
            "rectifier": [round(float(x), 4) for x in diffs.mean(0)]}


def save_human_sample(study_id: int, question_id: int, rows: list[dict]) -> int:
    return db.ex("INSERT INTO human_samples(study_id,question_id,rows_json,created_at) VALUES(?,?,?,?)",
                 study_id, question_id, json.dumps(rows), db.now())
