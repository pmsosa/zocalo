"""Running a study: cost estimate, spending guard, concurrent calls, progress, cancel."""
from __future__ import annotations

import asyncio
import json
import time

from .. import answering, db, providers, usage
from ..population import effective_record, new_branch
from . import ARMS, assign_arms, get, select_people, study_seed

_cancel: set[int] = set()
_running: dict[int, asyncio.Task] = {}


def _plan(study: dict) -> tuple[list[dict], dict[int, str], list[str]]:
    cfg = study["config"]
    people = select_people(study["population_id"], study["filter"], study.get("panel_id"), cfg.get("size"),
                           study_seed(study["id"]))
    arms = list(ARMS[study["kind"]])
    if study["kind"] == "treatment" and cfg.get("within"):
        arms.append("within")
    assignment = assign_arms(people, arms, study_seed(study["id"]))
    models = [str(m) for m in (cfg.get("models") or [])]
    return people, assignment, models


def estimate(study_id: int) -> dict:
    study = get(study_id)
    people, assignment, models = _plan(study)
    method = study["config"].get("method", "spread")
    calls = cost = 0.0
    per_model = []
    sample = people[:25] or []
    for mref in models:
        try:
            m = providers.model_row(mref)
        except providers.ProviderError:
            continue
        mcost, mcalls = 0.0, 0
        for q in study["questions"]:
            if sample:
                tin = sum(answering.estimate_tokens(p["rec"], q["text"], q["options"], method)[0] for p in sample) / len(sample)
                tout = answering.estimate_tokens(sample[0]["rec"], q["text"], q["options"], method)[1]
            else:
                tin, tout = 600, 140
            n_calls = sum(2 if assignment[p["id"]] == "within" else 1 for p in people)
            mcalls += n_calls
            mcost += n_calls * providers.cost_of(m, int(tin), int(tout))
        per_model.append({"model": mref, "name": f"{m['provider_label']} · {m['label']}", "calls": mcalls,
                          "cost": round(mcost, 4), "price_known": m["price_in"] is not None})
        calls += mcalls
        cost += mcost
    guard = usage.guard_status(cost)
    return {"people": len(people), "questions": len(study["questions"]), "models": per_model, "calls": int(calls),
            "cost": round(cost, 4), "big_panel": len(people) > 10_000, **guard}


async def _answer_one(study, q, person, arm, mref, sem, lang):
    cfg = study["config"]
    rec = person["rec"]
    method = cfg.get("method", "spread")
    order = answering.option_order(len(q["options"]), q["meta"].get("ordered", False),
                                   (study["id"], q["id"], person["id"], mref))
    text = q["text"]
    context = ""
    if study["kind"] == "ab" and arm == "B":
        text = q["meta"].get("text_b") or text
        context = cfg.get("stimulus_b") or ""
    elif study["kind"] == "ab":
        context = cfg.get("stimulus_a") or ""
    elif arm == "treatment":
        context = cfg.get("treatment") or ""
    elif arm == "placebo":
        context = cfg.get("placebo") or ""
    asked = answering.Asked(text, q["options"], order, context, lang)
    async with sem:
        if study["id"] in _cancel:
            return None
        results = []
        try:
            if arm == "within":
                # Same person, one conversation: answer, read the news, answer again.
                first = answering.Asked(text, q["options"], order, "", lang)
                a1 = await answering.ask(mref, rec, first, method=method)
                hist = [{"role": "user", "content": f"Question: {text}"},
                        {"role": "assistant", "content": json.dumps({"answer_given": q["options"][a1.answer_idx]})}]
                second = answering.Asked(text, q["options"], order, cfg.get("treatment") or "", lang)
                a2 = await answering.ask(mref, rec, second, method=method,
                                         design_informed=bool(cfg.get("design_informed")), history=hist)
                results = [("within_before", a1), ("within_after", a2)]
            else:
                a = await answering.ask(mref, rec, asked, method=method,
                                        design_informed=bool(cfg.get("design_informed")))
                results = [(arm, a)]
        except (providers.ProviderError, ValueError) as e:
            db.ex("INSERT INTO answers(study_id,question_id,person_id,arm,model_ref,ok,error,created_at) "
                  "VALUES(?,?,?,?,?,0,?,?)", study["id"], q["id"], person["id"], arm, mref, str(e)[:300], db.now())
            return 0.0
        spent = 0.0
        for arm_name, a in results:
            db.ex("INSERT INTO answers(study_id,question_id,person_id,branch_id,arm,model_ref,spread_json,answer_idx,"
                  "reason,prompt_hash,option_order_json,seed,tokens_in,tokens_out,cost,ok,created_at) "
                  "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)", study["id"], q["id"], person["id"],
                  person.get("branch_id"), arm_name, mref, json.dumps([round(x, 4) for x in a.spread]), a.answer_idx,
                  a.reason, a.prompt_hash, json.dumps(order), study_seed(study["id"]), a.tokens_in, a.tokens_out,
                  a.cost, db.now())
            usage.record(study["id"], "study", mref, a.tokens_in, a.tokens_out, a.cost)
            spent += a.cost
        return spent


async def run(study_id: int, lang: str = "en") -> None:
    study = get(study_id)
    people, assignment, models = _plan(study)
    if not models:
        db.ex("UPDATE studies SET status='error', status_msg=? WHERE id=?", "No model chosen for this study.", study_id)
        return
    # Each person in a treatment study gets their own branch ("saw the news", "placebo"…), so the base record and
    # any panel stay clean.
    if study["kind"] in ("treatment", "ab"):
        for p in people:
            arm = assignment[p["id"]]
            p["branch_id"] = new_branch(p["id"], f"study {study_id} · {arm}",
                                        {"context": [], "study": study_id, "arm": arm})
    db.ex("DELETE FROM answers WHERE study_id=?", study_id)
    db.ex("UPDATE studies SET status='running', progress=0, status_msg=NULL, cost_actual=0 WHERE id=?", study_id)
    sem = asyncio.Semaphore(int(db.get_setting("concurrency", 6)))
    jobs = [(q, p, assignment[p["id"]], m) for m in models for q in study["questions"] for p in people]
    total, done, spent = len(jobs), 0, 0.0
    cap_left = usage.cap_remaining()
    last = time.time()
    tasks = [asyncio.create_task(_answer_one(study, q, p, arm, m, sem, lang)) for q, p, arm, m in jobs]
    stopped = None
    for fut in asyncio.as_completed(tasks):
        c = await fut
        done += 1
        if c:
            spent += c
        if cap_left is not None and spent >= cap_left and not stopped:
            stopped = "cap"
            _cancel.add(study_id)
        if time.time() - last > 1.0 or done == total:
            last = time.time()
            db.ex("UPDATE studies SET progress=?, cost_actual=? WHERE id=?", done / max(total, 1), round(spent, 6), study_id)
    failed = db.q1("SELECT COUNT(*) AS n FROM answers WHERE study_id=? AND ok=0", study_id)["n"]
    if study_id in _cancel:
        _cancel.discard(study_id)
        status, msg = ("stopped", "Stopped: the monthly spending cap was reached.") if stopped == "cap" else ("stopped", "Stopped by you.")
    else:
        ok = db.q1("SELECT COUNT(*) AS n FROM answers WHERE study_id=? AND ok=1", study_id)["n"]
        first = db.q1("SELECT error FROM answers WHERE study_id=? AND ok=0 LIMIT 1", study_id)
        status = "done" if ok else "error"
        msg = (f"{failed} of {failed + ok} answers failed. First error: {first['error']}" if failed else None)
    db.ex("UPDATE studies SET status=?, status_msg=?, progress=?, cost_actual=?, finished_at=? WHERE id=?",
          status, msg, done / max(total, 1), round(spent, 6), db.now(), study_id)


def start(study_id: int, lang: str = "en") -> None:
    if study_id in _running and not _running[study_id].done():
        return
    _cancel.discard(study_id)
    _running[study_id] = asyncio.get_event_loop().create_task(run(study_id, lang))


def cancel(study_id: int) -> None:
    _cancel.add(study_id)


def recover_interrupted() -> None:
    """After a restart, studies that were running can't continue in-process; mark them so the user can rerun."""
    db.ex("UPDATE studies SET status='stopped', status_msg='Interrupted by a restart. Run it again to finish.' "
          "WHERE status='running'")
