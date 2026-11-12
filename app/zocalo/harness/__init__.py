"""The testing harness: how wrong are simulated answers, measured on real survey data.

A test run takes a test set (questions with real answer shares), a model and a method, and scores each question:

  population  simulated people answer (the real method). For "twins" test sets each simulated person is a twin of
              a real respondent: their demographics plus some of their other answers, never the question tested.
  aggregate   no people: the model is asked directly for the share of the country choosing each option
  anchor      no model: the answer shares of the closest *other* real question in the index
  uniform     no model: every option equally likely
  knn         no model (twins sets only): each held-out respondent gets the answers of their most similar
              respondents in the other half of the sample, on demographics alone

Per question we record the mean absolute error across options (in percentage points), the largest single-option
error, the total variation distance, options real people chose (≥5%) that the simulation almost never did (<1%),
and the ratio of simulated to real spread. Results by question type feed the error estimates shown on results
("measured" error), and each run records how often the shown error ranges actually held (coverage).
"""
from __future__ import annotations

import asyncio
import json
import random
import traceback

import numpy as np

from .. import answering, db, errors, providers, usage
from ..population import profile_text  # noqa: F401  (kept for prompt parity)

_cancel: set[int] = set()
METHODS = ["population", "aggregate", "anchor", "uniform", "knn"]

AGG_SYSTEM = "You estimate how a country's adult population answers survey questions. Be calibrated, not agreeable."
AGG_USER = """Question asked of adults in {country}: {question}
Options:
{options}
Estimate the share of adults choosing each option. Reply with JSON only: {{"probabilities": {{"A": 0.0, ...}}}}"""


def recover_interrupted() -> list[int]:
    """Runs that a restart interrupted pick up where they stopped: questions already scored are kept."""
    ids = [r["id"] for r in db.q("SELECT id FROM harness_runs WHERE status IN ('running','queued')")]
    for rid in ids:
        db.ex("UPDATE harness_runs SET status_msg='Resumed after a restart.' WHERE id=?", rid)
    return ids


def resume_all(ids: list[int]) -> None:
    for rid in ids:
        r = db.q1("SELECT config_json FROM harness_runs WHERE id=?", rid)
        asyncio.get_event_loop().create_task(_run(rid, db.loads(r["config_json"], {})))


def overview() -> dict:
    from ..datasets import loaders
    runs = db.q("SELECT id,testset,model_ref,method,config_json,status,progress,status_msg,metrics_json,created_at,finished_at "
                "FROM harness_runs ORDER BY id DESC")
    for r in runs:
        r["config"] = db.loads(r.pop("config_json"), {})
        r["metrics"] = db.loads(r.pop("metrics_json"), None)
        r["model_name"] = providers.model_name(r["model_ref"]) if r["model_ref"] not in ("", "none") else "—"
    return {"testsets": loaders.testsets(), "runs": runs, "error_table": error_table(), "methods": METHODS}


def error_table() -> list[dict]:
    out = []
    for qtype in errors.QTYPES[:-1]:
        for topical in (0, 1):
            m = errors._measured(qtype, topical)
            prior = errors.PRIORS[(qtype, topical)]
            out.append({"qtype": qtype, "topical": bool(topical), "prior_p50": prior[0], "prior_p80": prior[1],
                        "measured_p50": m[0] if m else None, "measured_p80": m[1] if m else None,
                        "items": m[2] if m else len(db.q(
                            "SELECT hi.id FROM harness_items hi JOIN harness_runs hr ON hr.id=hi.run_id WHERE "
                            "hr.status='done' AND hr.method='population' AND hi.qtype=?", qtype))})
    return out


def run_detail(rid: int) -> dict:
    r = db.q1("SELECT * FROM harness_runs WHERE id=?", rid)
    if not r:
        return {}
    r["config"] = db.loads(r.pop("config_json"), {})
    r["metrics"] = db.loads(r.pop("metrics_json"), None)
    r["items"] = [dict(i, real=json.loads(i.pop("real_json")), sim=json.loads(i.pop("sim_json")),
                       meta=db.loads(i.pop("meta_json"), {})) for i in
                  db.q("SELECT * FROM harness_items WHERE run_id=? ORDER BY abs_error DESC", rid)]
    r["model_name"] = providers.model_name(r["model_ref"]) if r["model_ref"] not in ("", "none") else "—"
    return r


def cancel(rid: int) -> None:
    _cancel.add(rid)


def start(cfg: dict) -> int:
    from ..datasets import loaders
    method = cfg.get("method", "population")
    if method not in METHODS:
        raise ValueError("Unknown method.")
    if method in ("population", "aggregate") and not cfg.get("model"):
        raise ValueError("Choose a model.")
    ts = next((t for t in loaders.testsets() if t["id"] == cfg.get("testset")), None)
    if not ts or not ts["ready"]:
        raise ValueError("That test set isn't downloaded yet (Data page).")
    if method == "knn" and ts["kind"] != "twins":
        raise ValueError("The kNN baseline needs a twins test set (respondent-level data).")
    rid = db.ex("INSERT INTO harness_runs(testset,model_ref,method,config_json,status,created_at) VALUES(?,?,?,?,?,?)",
                cfg["testset"], str(cfg.get("model") or "none") if method in ("population", "aggregate") else "none",
                method, json.dumps(cfg), "queued", db.now())
    asyncio.get_event_loop().create_task(_run(rid, cfg))
    return rid


def item_metrics(real: list[float], sim: list[float]) -> dict:
    r, s = np.array(real, float), np.array(sim, float)
    r, s = r / max(r.sum(), 1e-9), s / max(s.sum(), 1e-9)
    diff = np.abs(r - s) * 100
    return {"mae": float(diff.mean()), "max": float(diff.max()), "tvd": float(0.5 * np.abs(r - s).sum() * 100),
            "missed": int(((r >= 0.05) & (s < 0.01)).sum())}


def _spread_ratio(real: list[float], sim: list[float]) -> float | None:
    """For ordered options: simulated standard deviation over real. Below 1 means answers too bunched."""
    k = np.arange(len(real))
    r, s = np.array(real, float), np.array(sim, float)
    if r.sum() <= 0 or s.sum() <= 0 or len(real) < 3:
        return None
    r, s = r / r.sum(), s / s.sum()
    sd = lambda p: float(np.sqrt((p * (k - (p * k).sum()) ** 2).sum()))
    return round(sd(s) / sd(r), 3) if sd(r) > 0 else None


async def _aggregate(model_ref: str, item: dict) -> tuple[list[float], float]:
    opts = item["options"]
    block = "\n".join(f"{answering.LETTERS[i]}. {o}" for i, o in enumerate(opts))
    comp, m = await providers.complete_ref(model_ref, AGG_SYSTEM, AGG_USER.format(
        country=item.get("country_name") or item.get("country") or "the country", question=item["text"], options=block),
        max_tokens=300)
    probs = providers.parse_json(comp.text).get("probabilities", {})
    spread = [max(0.0, float(probs.get(answering.LETTERS[i], 0) or 0)) for i in range(len(opts))]
    tot = sum(spread) or 1
    cost = providers.cost_of(m, comp.tokens_in, comp.tokens_out)
    usage.record(None, "test", model_ref, comp.tokens_in, comp.tokens_out, cost)
    return [x / tot for x in spread], cost


async def _population(model_ref: str, item: dict, people: list[dict], sem: asyncio.Semaphore, rid: int) -> tuple[list[float], float, list]:
    opts = item["options"]
    spreads, weights, cost = [], [], 0.0
    individual = []

    async def one(p):
        nonlocal cost
        if rid in _cancel:
            return
        order = answering.option_order(len(opts), item.get("ordered", False), ("test", rid, item["ref"], p["ref"]),
                                       last_fixed=bool(item.get("has_dk")))
        asked = answering.Asked(item["text"], opts, order, "", "en")
        async with sem:
            try:
                a = await answering.ask(model_ref, p["record"], asked)
            except (providers.ProviderError, ValueError):
                return
        usage.record(None, "test", model_ref, a.tokens_in, a.tokens_out, a.cost)
        cost += a.cost
        spreads.append(a.spread)
        weights.append(p.get("weight", 1.0))
        if p.get("actual") is not None:
            individual.append((p["actual"], a.answer_idx))

    await asyncio.gather(*(one(p) for p in people))
    if not spreads:
        raise providers.ProviderError("no answers came back")
    w = np.array(weights)
    share = (np.array(spreads) * w[:, None]).sum(0) / w.sum()
    return share.tolist(), cost, individual


async def _run(rid: int, cfg: dict) -> None:
    from ..calibration import anchors_for
    from ..datasets import loaders
    db.ex("UPDATE harness_runs SET status='running' WHERE id=?", rid)
    method = cfg.get("method", "population")
    try:
        items = await asyncio.to_thread(loaders.testset_items, cfg["testset"], cfg)
        if not items:
            raise ValueError("No usable questions in this test set for these settings.")
        sem = asyncio.Semaphore(int(db.get_setting("concurrency", 6)))
        scored = {r["item_ref"] for r in db.q("SELECT item_ref FROM harness_items WHERE run_id=?", rid)}
        total_cost, done = 0.0, len(scored)
        for item in items:
            if rid in _cancel:
                break
            if item["ref"] in scored:
                continue
            cost_before = total_cost
            individual = []
            if method == "uniform":
                sim = [1 / len(item["options"])] * len(item["options"])
            elif method == "anchor":
                cands = [a for a in anchors_for(item["text"], item.get("country"), 8)
                         if not (a["source"] == item.get("source") and a["ref"] == item.get("anchor_ref"))
                         and len(a["dist"]) == len(item["options"])]
                if not cands:
                    continue
                sim = cands[0]["dist"]
            elif method == "aggregate":
                sim, c = await _aggregate(str(cfg["model"]), item)
                total_cost += c
            elif method == "knn":
                sim, individual = loaders.knn_predict(item)
            else:
                people = item.get("people") or []
                if not people:
                    continue
                sim, c, individual = await _population(str(cfg["model"]), item, people, sem, rid)
                total_cost += c
            met = item_metrics(item["real"], sim)
            est = errors.estimate(item.get("qtype", "opinion"), item.get("topical", False), len(item.get("people") or [1] * 1000),
                                  False, item.get("country") or "US")
            meta = {"cost": round(total_cost - cost_before, 6), "max": met["max"], "tvd": met["tvd"], "missed": met["missed"], "spread_ratio": _spread_ratio(item["real"], sim)
                    if item.get("ordered") else None, "topical": int(bool(item.get("topical"))), "text": item["text"],
                    "options": item["options"], "country": item.get("country"), "predicted_p80": est["p80"]}
            if individual:
                meta["individual_accuracy"] = round(float(np.mean([a == b for a, b in individual])), 3)
                meta["individual_n"] = len(individual)
            db.ex("INSERT INTO harness_items(run_id,item_ref,qtype,subgroup,real_json,sim_json,abs_error,meta_json) "
                  "VALUES(?,?,?,?,?,?,?,?)", rid, item["ref"], item.get("qtype", "opinion"), None,
                  json.dumps([round(x, 4) for x in item["real"]]), json.dumps([round(float(x), 4) for x in sim]),
                  met["mae"], json.dumps(meta, ensure_ascii=False))
            done += 1
            db.ex("UPDATE harness_runs SET progress=? WHERE id=?", done / len(items), rid)
        rows = db.q("SELECT abs_error, meta_json FROM harness_items WHERE run_id=?", rid)
        if not rows:
            raise ValueError("Nothing could be scored.")
        maes = np.array([r["abs_error"] for r in rows])
        metas = [json.loads(r["meta_json"]) for r in rows]
        acc = [m["individual_accuracy"] for m in metas if "individual_accuracy" in m]
        metrics = {"items": len(rows), "mae_mean": round(float(maes.mean()), 2), "mae_p50": round(float(np.percentile(maes, 50)), 2),
                   "mae_p80": round(float(np.percentile(maes, 80)), 2),
                   "share_over_15": round(float(np.mean([m["max"] > 15 for m in metas])), 3),
                   "missed_options": int(sum(m["missed"] for m in metas)),
                   "spread_ratio": round(float(np.mean([m["spread_ratio"] for m in metas if m.get("spread_ratio")])), 3)
                   if any(m.get("spread_ratio") for m in metas) else None,
                   "individual_accuracy": round(float(np.mean(acc)), 3) if acc else None,
                   "coverage_p80": round(float(np.mean([r["abs_error"] <= m.get("predicted_p80", 1e9) for r, m in zip(rows, metas)])), 3),
                   "cost": round(sum(m.get("cost", 0) for m in metas), 4)}
        status = "stopped" if rid in _cancel else "done"
        _cancel.discard(rid)
        db.ex("UPDATE harness_runs SET status=?, progress=1, metrics_json=?, finished_at=? WHERE id=?",
              status, json.dumps(metrics), db.now(), rid)
    except Exception as e:
        traceback.print_exc()
        db.ex("UPDATE harness_runs SET status='error', status_msg=?, finished_at=? WHERE id=?", str(e)[:400], db.now(), rid)


def sample_people(people: list[dict], n: int, seed: int) -> list[dict]:
    if len(people) <= n:
        return people
    rng = random.Random(seed)
    w = np.array([p.get("weight", 1.0) for p in people], float)
    idx = rng.choices(range(len(people)), weights=(w / w.sum()).tolist(), k=n)
    picked = [dict(people[i], weight=1.0) for i in idx]
    return picked
