"""Zócalo web app: JSON API under /api, the single-page app everywhere else."""
from __future__ import annotations

import csv
import io
import json
import secrets
from pathlib import Path

import markdown as md
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import calibration, chat, db, errors, providers, security, usage
from .config import DATASETS_HOST, DOCS_DIR, IN_DOCKER, VERSION, WEB_DIR
from .population import build as popbuild
from .population import effective_record, person_view
from .providers.pricing import default_price
from .studies import create as create_study
from .studies import get as get_study
from .studies import results as study_results
from .studies import runner

app = FastAPI(title="Zócalo", version=VERSION, docs_url=None, redoc_url=None)
OPEN_PATHS = ("/api/health", "/api/me", "/api/auth/")


@app.on_event("startup")
async def startup() -> None:
    db.init()
    security.auth_mode()
    runner.resume_all(runner.recover_interrupted())
    from . import harness
    harness.resume_all(harness.recover_interrupted())


# ---------- auth ----------
@app.middleware("http")
async def auth_gate(request: Request, call_next):
    path = request.url.path
    request.state.user = None
    if path.startswith("/api/") and not path.startswith(OPEN_PATHS):
        if security.auth_mode() == "accounts":
            user = security.user_for_token(request.cookies.get(security.SESSION_COOKIE))
            if not user:
                return JSONResponse({"detail": "login required"}, status_code=401)
            request.state.user = user
    return await call_next(request)


def _admin(request: Request) -> None:
    if security.auth_mode() == "accounts":
        u = request.state.user or security.user_for_token(request.cookies.get(security.SESSION_COOKIE))
        if not u or not u["is_admin"]:
            raise HTTPException(403, "admin only")


@app.get("/api/health")
def health():
    return {"ok": True, "version": VERSION}


@app.get("/api/me")
def me(request: Request):
    mode = security.auth_mode()
    user = security.user_for_token(request.cookies.get(security.SESSION_COOKIE))
    return {"auth_mode": mode, "user": user, "has_users": security.has_users(), "version": VERSION,
            "needs_login": mode == "accounts" and not user, "needs_setup": mode == "accounts" and not security.has_users()}


def _set_cookie(resp: Response, token: str, request: Request) -> None:
    resp.set_cookie(security.SESSION_COOKIE, token, httponly=True, samesite="lax",
                    secure=request.url.scheme == "https", max_age=security.SESSION_DAYS * 86400)


@app.post("/api/auth/setup")
async def auth_setup(request: Request, response: Response):
    """Create the first admin account. Allowed when there are no users yet (this also turns on logins)."""
    body = await request.json()
    if security.has_users():
        raise HTTPException(400, "Accounts already exist. Sign in instead.")
    if len(body.get("password", "")) < 8 or not body.get("username", "").strip():
        raise HTTPException(400, "Choose a username and a password of at least 8 characters.")
    uid = security.create_user(body["username"], body["password"], True)
    db.set_setting("auth_mode", "accounts")
    _set_cookie(response, security.new_session(uid), request)
    return {"ok": True}


@app.post("/api/auth/login")
async def login(request: Request, response: Response):
    body = await request.json()
    row = db.q1("SELECT * FROM users WHERE username=?", body.get("username", "").strip())
    if not row or not security.check_password(body.get("password", ""), row["pw_hash"]):
        raise HTTPException(401, "Wrong username or password.")
    _set_cookie(response, security.new_session(row["id"]), request)
    return {"ok": True}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    security.end_session(request.cookies.get(security.SESSION_COOKIE))
    response.delete_cookie(security.SESSION_COOKIE)
    return {"ok": True}


@app.post("/api/auth/join")
async def join(request: Request, response: Response):
    body = await request.json()
    inv = db.q1("SELECT * FROM invites WHERE code=? AND used_by IS NULL", body.get("code", ""))
    if not inv:
        raise HTTPException(400, "This invite code isn't valid or was already used.")
    if len(body.get("password", "")) < 8 or not body.get("username", "").strip():
        raise HTTPException(400, "Choose a username and a password of at least 8 characters.")
    if db.q1("SELECT 1 AS x FROM users WHERE username=?", body["username"].strip()):
        raise HTTPException(400, "That username is taken.")
    uid = security.create_user(body["username"], body["password"], False)
    db.ex("UPDATE invites SET used_by=? WHERE code=?", uid, inv["code"])
    _set_cookie(response, security.new_session(uid), request)
    return {"ok": True}


@app.get("/api/users")
def users(request: Request):
    _admin(request)
    return {"users": db.q("SELECT id,username,is_admin,created_at FROM users ORDER BY id"),
            "invites": db.q("SELECT code,created_at FROM invites WHERE used_by IS NULL ORDER BY created_at DESC")}


@app.post("/api/users/invite")
def invite(request: Request):
    _admin(request)
    code = secrets.token_urlsafe(9)
    db.ex("INSERT INTO invites(code,created_by,created_at) VALUES(?,?,?)", code,
          (request.state.user or {}).get("id"), db.now())
    return {"code": code}


@app.delete("/api/users/{uid}")
def delete_user(uid: int, request: Request):
    _admin(request)
    if (request.state.user or {}).get("id") == uid:
        raise HTTPException(400, "You can't remove yourself.")
    db.ex("DELETE FROM sessions WHERE user_id=?", uid)
    db.ex("DELETE FROM users WHERE id=?", uid)
    return {"ok": True}


# ---------- settings ----------
SERVER_SETTINGS = {"monthly_cap": None, "confirm_above": None, "concurrency": 6, "allow_noncommercial": True,
                   "default_models": [], "datasets_dir": None}


@app.get("/api/settings")
def get_settings():
    from .datasets import datasets_dir
    out = {k: db.get_setting(k, v) for k, v in SERVER_SETTINGS.items()}
    d = datasets_dir()
    out.update(datasets_path=str(d), datasets_host=DATASETS_HOST or None, datasets_editable=not IN_DOCKER,
               datasets_present=d.exists(), auth_mode=security.auth_mode(), version=VERSION)
    return out


@app.put("/api/settings")
async def put_settings(request: Request):
    _admin(request)
    body = await request.json()
    for k, v in body.items():
        if k not in SERVER_SETTINGS:
            continue
        if k == "datasets_dir" and IN_DOCKER:
            continue
        if k in ("monthly_cap", "confirm_above"):
            v = None if v in (None, "", 0, "0") else float(v)
        if k == "concurrency":
            v = max(1, min(32, int(v)))
        db.set_setting(k, v)
    return get_settings()


# ---------- providers and models ----------
def _provider_out(p: dict) -> dict:
    return {k: p[k] for k in ["id", "kind", "label", "base_url", "key_hint", "status", "status_msg", "checked_at",
                              "created_at"]} | {"models": json.loads(p["models_json"]),
                                                "kind_name": providers.KINDS.get(p["kind"], {}).get("name", p["kind"])}


@app.get("/api/providers")
def list_providers():
    return {"kinds": providers.KINDS, "providers": [_provider_out(p) for p in db.q("SELECT * FROM providers ORDER BY id")]}


@app.post("/api/providers/test")
async def test_provider(request: Request):
    """Check a key without saving it: returns the models it can use."""
    _admin(request)
    b = await request.json()
    kind = b.get("kind")
    if kind not in providers.KINDS:
        raise HTTPException(400, "Unknown provider.")
    try:
        models = await providers.list_models(kind, (b.get("key") or "").strip(), (b.get("base_url") or "").strip() or None)
    except (providers.ProviderError, Exception) as e:
        return {"ok": False, "message": str(e)[:300]}
    return {"ok": True, "models": models}


@app.post("/api/providers")
async def add_provider(request: Request):
    _admin(request)
    b = await request.json()
    kind = b.get("kind")
    if kind not in providers.KINDS:
        raise HTTPException(400, "Unknown provider.")
    key = (b.get("key") or "").strip()
    base = (b.get("base_url") or "").strip() or None
    if providers.KINDS[kind]["key"] and not key:
        raise HTTPException(400, "This provider needs an API key.")
    try:
        models = await providers.list_models(kind, key, base)
        status, msg = "ok", f"{len(models)} models"
    except Exception as e:
        raise HTTPException(400, f"The key didn't work: {str(e)[:300]}")
    pid = db.ex("INSERT INTO providers(kind,label,base_url,key_enc,key_hint,status,status_msg,checked_at,models_json,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)", kind, b.get("label") or providers.KINDS[kind]["name"], base,
                security.encrypt(key) if key else None, security.key_hint(key) if key else None, status, msg, db.now(),
                json.dumps(models), db.now())
    failed = {}
    for mid in b.get("models") or []:
        err = await _try_model(pid, mid)
        if err:
            failed[mid] = err
        else:
            _add_model(pid, mid, models)
    return _provider_out(db.q1("SELECT * FROM providers WHERE id=?", pid)) | {"failed_models": failed}


async def _try_model(provider_id: int, model_id: str) -> str | None:
    """A tiny real call, because providers list models they no longer serve. Returns an error message or None."""
    p = providers.provider_row(provider_id)
    try:
        comp = await providers.complete(p["kind"], security.decrypt(p["key_enc"]), p["base_url"], model_id,
                                        "Reply with JSON only.", 'Reply with {"ok": true}', max_tokens=50)
        providers.parse_json(comp.text)
        return None
    except Exception as e:
        return str(e)[:300]


def _add_model(provider_id: int, model_id: str, listing: list[dict] | None = None) -> None:
    label = next((m["label"] for m in (listing or []) if m["id"] == model_id), model_id)
    pin, pout = default_price(model_id)
    db.ex("INSERT OR IGNORE INTO models(provider_id,model_id,label,price_in,price_out,enabled) VALUES(?,?,?,?,?,1)",
          provider_id, model_id, label, pin, pout)


@app.post("/api/providers/{pid}/check")
async def check_provider(pid: int, request: Request):
    _admin(request)
    p = providers.provider_row(pid)
    try:
        models = await providers.list_models(p["kind"], security.decrypt(p["key_enc"]), p["base_url"])
        db.ex("UPDATE providers SET status='ok', status_msg=?, checked_at=?, models_json=? WHERE id=?",
              f"{len(models)} models", db.now(), json.dumps(models), pid)
    except Exception as e:
        db.ex("UPDATE providers SET status='error', status_msg=?, checked_at=? WHERE id=?", str(e)[:300], db.now(), pid)
    return _provider_out(db.q1("SELECT * FROM providers WHERE id=?", pid))


@app.put("/api/providers/{pid}")
async def update_provider(pid: int, request: Request):
    _admin(request)
    b = await request.json()
    if b.get("key"):
        db.ex("UPDATE providers SET key_enc=?, key_hint=? WHERE id=?", security.encrypt(b["key"].strip()),
              security.key_hint(b["key"]), pid)
    if b.get("label"):
        db.ex("UPDATE providers SET label=? WHERE id=?", b["label"], pid)
    return await check_provider(pid, request)


@app.delete("/api/providers/{pid}")
def delete_provider(pid: int, request: Request):
    _admin(request)
    db.ex("DELETE FROM providers WHERE id=?", pid)
    return {"ok": True}


@app.get("/api/models")
def list_models():
    rows = db.q("SELECT m.*, p.label AS provider_label, p.kind, p.status AS provider_status FROM models m "
                "JOIN providers p ON p.id=m.provider_id ORDER BY p.id, m.label")
    return {"models": rows}


@app.post("/api/models")
async def add_model(request: Request):
    _admin(request)
    b = await request.json()
    p = providers.provider_row(int(b["provider_id"]))
    err = await _try_model(p["id"], b["model_id"])
    if err:
        raise HTTPException(400, f"That model didn't answer a test call: {err}")
    _add_model(p["id"], b["model_id"], json.loads(p["models_json"]))
    return list_models()


@app.put("/api/models/{mid}")
async def update_model(mid: int, request: Request):
    _admin(request)
    b = await request.json()
    for k in ("price_in", "price_out"):
        if k in b:
            db.ex(f"UPDATE models SET {k}=? WHERE id=?", None if b[k] in ("", None) else float(b[k]), mid)
    if "enabled" in b:
        db.ex("UPDATE models SET enabled=? WHERE id=?", int(bool(b["enabled"])), mid)
    return list_models()


@app.delete("/api/models/{mid}")
def delete_model(mid: int, request: Request):
    _admin(request)
    db.ex("DELETE FROM models WHERE id=?", mid)
    return {"ok": True}


# ---------- populations, people, panels ----------
@app.get("/api/populations")
def populations():
    return {"populations": db.q("SELECT id,name,country,source,size,status,created_at,meta_json FROM populations ORDER BY id DESC")}


@app.get("/api/populations/sources")
async def population_sources():
    """Which sources can build people, and for which countries. Reading big files is slow the first time, so this
    runs in a thread and is cached on disk per file version."""
    import asyncio
    return {"sources": await asyncio.to_thread(popbuild.available_sources)}


@app.post("/api/populations")
async def new_population(request: Request):
    b = await request.json()
    n = int(b.get("size") or 2000)
    if n < 10 or n > 200_000:
        raise HTTPException(400, "Size must be between 10 and 200,000.")
    job = await popbuild.start(b.get("name") or f"{b['country']} · {b['source']}", b["source"], b["country"], n,
                               int(b.get("seed") or secrets.randbelow(10**6)), b.get("options") or {})
    return {"job": job}


@app.get("/api/populations/jobs/{job_id}")
def population_job(job_id: str):
    j = popbuild.job(job_id)
    if not j:
        raise HTTPException(404, "No such job.")
    return j


@app.get("/api/populations/{pid}/people")
def population_people(pid: int, limit: int = 20000):
    """Compact rows for the dot views: id, name and the fields filters use."""
    rows = db.q("SELECT id,name,base_json,weight FROM people WHERE population_id=? ORDER BY id LIMIT ?", pid, limit)
    keys = ["age", "sex", "region", "education", "party", "urban", "religion", "race", "country", "occupation",
            "employment", "income", "vote_last", "ideology"]
    out = []
    for r in rows:
        rec = json.loads(r["base_json"])
        out.append({"id": r["id"], "name": r["name"], "w": r["weight"], "f": {k: rec.get(k) for k in keys if rec.get(k) is not None}})
    pop = db.q1("SELECT * FROM populations WHERE id=?", pid)
    if not pop:
        raise HTTPException(404, "No such population.")
    pop["meta"] = db.loads(pop.pop("meta_json"), {})
    return {"population": pop, "people": out}


@app.delete("/api/populations/{pid}")
def delete_population(pid: int):
    if db.q1("SELECT 1 AS x FROM studies WHERE population_id=? LIMIT 1", pid):
        raise HTTPException(400, "Studies use this population. Delete them first.")
    db.ex("DELETE FROM populations WHERE id=?", pid)
    return {"ok": True}


@app.get("/api/people/{person_id}")
def person(person_id: int, lang: str = "en"):
    p = db.q1("SELECT * FROM people WHERE id=?", person_id)
    if not p:
        raise HTTPException(404, "No such person.")
    out = person_view(p, lang)
    out["branches"] = db.q("SELECT id,parent_id,name,overlay_json,created_at FROM branches WHERE person_id=? ORDER BY id",
                           person_id)
    out["answers"] = db.q("SELECT a.study_id, s.name AS study, q.text, q.options_json, a.arm, a.spread_json, a.reason "
                          "FROM answers a JOIN studies s ON s.id=a.study_id JOIN questions q ON q.id=a.question_id "
                          "WHERE a.person_id=? AND a.ok=1 ORDER BY a.id DESC LIMIT 50", person_id)
    out["chats"] = db.q("SELECT c.id,c.kind,c.title,c.created_at FROM chats c JOIN chat_members m ON m.chat_id=c.id "
                        "WHERE m.person_id=? ORDER BY c.id DESC", person_id)
    from .population import profile_text
    out["profile_text"] = profile_text(out["record"])
    return out


@app.get("/api/panels")
def panels():
    return {"panels": db.q("SELECT p.id,p.name,p.population_id,p.filter_json,p.created_at,"
                           "json_array_length(p.person_ids_json) AS size, po.name AS population "
                           "FROM panels p JOIN populations po ON po.id=p.population_id ORDER BY p.id DESC")}


@app.post("/api/panels")
async def new_panel(request: Request):
    from .studies import select_people
    b = await request.json()
    if b.get("person_ids"):
        wanted = {int(x) for x in b["person_ids"]}
        ids = [r["id"] for r in db.q("SELECT id FROM people WHERE population_id=?", int(b["population_id"])) if r["id"] in wanted]
    else:
        ids = [p["id"] for p in select_people(int(b["population_id"]), b.get("filter") or {}, None, b.get("size"),
                                              int(b.get("seed") or 1))]
    if not ids:
        raise HTTPException(400, "Nobody matches this filter.")
    pid = db.ex("INSERT INTO panels(name,population_id,filter_json,person_ids_json,created_at) VALUES(?,?,?,?,?)",
                b.get("name") or "Panel", int(b["population_id"]), json.dumps(b.get("filter") or {}),
                json.dumps(ids), db.now())
    return {"id": pid, "size": len(ids)}


@app.delete("/api/panels/{pid}")
def delete_panel(pid: int):
    db.ex("DELETE FROM panels WHERE id=?", pid)
    return {"ok": True}


# ---------- studies ----------
@app.get("/api/studies")
def studies():
    return {"studies": db.q("SELECT s.id,s.name,s.kind,s.status,s.progress,s.cost_actual,s.cost_estimate,s.created_at,"
                            "s.finished_at,p.name AS population,p.country,p.source,"
                            "(SELECT COUNT(*) FROM questions q WHERE q.study_id=s.id) AS n_questions,"
                            "(SELECT text FROM questions q WHERE q.study_id=s.id ORDER BY idx LIMIT 1) AS first_question "
                            "FROM studies s JOIN populations p ON p.id=s.population_id ORDER BY s.id DESC")}


@app.post("/api/studies")
async def new_study(request: Request):
    b = await request.json()
    if not b.get("questions"):
        raise HTTPException(400, "Add at least one question.")
    for q in b["questions"]:
        if not q.get("text", "").strip() or len([o for o in q.get("options", []) if o.strip()]) < 2:
            raise HTTPException(400, "Every question needs text and at least two options.")
    sid = create_study(b)
    est = runner.estimate(sid)
    db.ex("UPDATE studies SET cost_estimate=? WHERE id=?", est["cost"], sid)
    return {"id": sid, "estimate": est}


@app.get("/api/studies/{sid}")
def study(sid: int):
    s = get_study(sid)
    if not s:
        raise HTTPException(404, "No such study.")
    return s


@app.get("/api/studies/{sid}/estimate")
def study_estimate(sid: int):
    return runner.estimate(sid)


@app.post("/api/studies/{sid}/run")
async def run_study(sid: int, request: Request):
    b = await request.json() if (await request.body()) else {}
    est = runner.estimate(sid)
    if est["over_cap"]:
        raise HTTPException(400, "This run would go over your monthly spending cap (Settings).")
    if est["needs_confirm"] and not b.get("confirm"):
        return {"needs_confirm": True, "estimate": est}
    if not b.get("resume"):
        db.ex("UPDATE studies SET cost_estimate=? WHERE id=?", est["cost"], sid)
    runner.start(sid, b.get("lang", "en"), resume=bool(b.get("resume")))
    return {"ok": True, "estimate": est}


@app.post("/api/studies/{sid}/cancel")
def cancel_study(sid: int):
    runner.cancel(sid)
    return {"ok": True}


@app.post("/api/studies/{sid}/duplicate")
def duplicate_study(sid: int):
    s = get_study(sid)
    new = {"name": s["name"] + " (copy)", "kind": s["kind"], "population_id": s["population_id"], "panel_id": s["panel_id"],
           "filter": s["filter"], "config": s["config"],
           "questions": [{"text": q["text"], "options": q["options"], "qtype": q["qtype"], "topical": q["topical"],
                          "ordered": q["meta"].get("ordered"), "text_b": q["meta"].get("text_b"), "include_unsure": False}
                         for q in s["questions"]]}
    return {"id": create_study(new)}


@app.delete("/api/studies/{sid}")
def delete_study(sid: int):
    runner.cancel(sid)
    db.ex("DELETE FROM studies WHERE id=?", sid)
    return {"ok": True}


@app.post("/api/studies/{sid}/results")
async def study_results_filtered(sid: int, request: Request):
    b = await request.json() if (await request.body()) else {}
    try:
        return study_results.compute(sid, b.get("filter") or None, b.get("lang", "en"))
    except KeyError:
        raise HTTPException(404, "No such study.")


@app.get("/api/studies/{sid}/export.csv")
def export_csv(sid: int):
    s = get_study(sid)
    if not s:
        raise HTTPException(404, "No such study.")
    rows = db.q("SELECT a.*, p.name, p.base_json FROM answers a JOIN people p ON p.id=a.person_id WHERE a.study_id=? "
                "ORDER BY a.question_id, a.person_id", sid)
    qs = {q["id"]: q for q in s["questions"]}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["study", "question", "person_id", "name", "age", "sex", "country", "region", "education", "party", "arm",
                "model", "answer_most_likely"] + [f"p_option_{i + 1}" for i in range(max(len(q["options"]) for q in qs.values()))]
               + ["reason", "ok", "error"])
    for r in rows:
        rec = json.loads(r["base_json"])
        q = qs[r["question_id"]]
        spread = json.loads(r["spread_json"]) if r["spread_json"] else []
        w.writerow([s["name"], q["text"], r["person_id"], r["name"], rec.get("age"), rec.get("sex"), rec.get("country"),
                    rec.get("region"), rec.get("education"), rec.get("party"), r["arm"], providers.model_name(r["model_ref"]),
                    q["options"][r["answer_idx"]] if r["answer_idx"] is not None else ""] + spread
                   + [""] * (len(q["options"]) - len(spread)) + [r["reason"] or "", r["ok"], r["error"] or ""])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="zocalo-study-{sid}.csv"'})


@app.post("/api/studies/{sid}/human/{qid}")
async def human_sample(sid: int, qid: int, file: UploadFile):
    text = (await file.read()).decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    rows = [{k.strip().lower(): (v or "").strip() for k, v in r.items() if k} for r in rows]
    if not rows or "answer" not in rows[0]:
        raise HTTPException(400, "The CSV needs an 'answer' column (option text or number), plus optional "
                                 "age, sex, region, education, party, country columns.")
    calibration.save_human_sample(sid, qid, rows)
    return {"ok": True, "rows": len(rows)}


@app.get("/api/errors/preview")
def error_preview(qtype: str = "opinion", topical: bool = False, n: int = 2000, subgroup: bool = False,
                  country: str = "US", demo: bool = False):
    return errors.estimate(qtype, topical, n, subgroup, country, demo)


@app.get("/api/errors/guess")
def guess(text: str):
    return {"qtype": errors.guess_qtype(text), "anchors": calibration.anchors_for(text, None, 3)}


# ---------- conversations ----------
@app.post("/api/chats")
async def new_chat(request: Request):
    b = await request.json()
    ids = [int(x) for x in b.get("person_ids") or []]
    if not ids or not b.get("model"):
        raise HTTPException(400, "Choose at least one person and a model.")
    cid = chat.create(b.get("kind", "interview"), ids, str(b["model"]), b.get("title"), b.get("study_id"),
                      b.get("stances"), b.get("branch_ids"), b.get("config"))
    if b.get("opening"):
        await chat.say(cid, b["opening"])
    return chat.get(cid)


@app.get("/api/chats")
def chats():
    return {"chats": db.q("SELECT c.id,c.kind,c.title,c.created_at,(SELECT COUNT(*) FROM messages m WHERE m.chat_id=c.id) AS n, "
                          "(SELECT group_concat(p.name, ', ') FROM chat_members cm JOIN people p ON p.id=cm.person_id "
                          "WHERE cm.chat_id=c.id) AS people FROM chats c ORDER BY c.id DESC LIMIT 200")}


@app.get("/api/chats/{cid}")
def get_chat(cid: int):
    try:
        return chat.get(cid)
    except KeyError:
        raise HTTPException(404, "No such conversation.")


@app.post("/api/chats/{cid}/say")
async def chat_say(cid: int, request: Request):
    b = await request.json()
    try:
        await chat.say(cid, b["text"])
    except providers.ProviderError as e:
        raise HTTPException(502, f"The model didn't answer: {e}")
    return chat.get(cid)


@app.post("/api/chats/{cid}/debate")
async def chat_debate(cid: int, request: Request):
    b = await request.json()
    try:
        await chat.debate(cid, b["question"], int(b.get("rounds") or 3))
    except providers.ProviderError as e:
        raise HTTPException(502, f"The model didn't answer: {e}")
    return chat.get(cid)


@app.post("/api/chats/{cid}/drift")
async def chat_drift(cid: int):
    await chat.drift_check(cid)
    return chat.get(cid)


@app.delete("/api/chats/{cid}")
def delete_chat(cid: int):
    db.ex("DELETE FROM chats WHERE id=?", cid)
    return {"ok": True}


# ---------- usage ----------
@app.get("/api/usage")
def get_usage():
    out = usage.summary()
    for r in out["by_model"]:
        r["name"] = providers.model_name(r["model_ref"]) if r["model_ref"] else "—"
    return out


# ---------- data sources ----------
@app.get("/api/data")
def data_sources(lang: str = "en"):
    from .datasets import registry
    return registry.overview(lang)


@app.post("/api/data/{source_id}/download")
async def data_download(source_id: str, request: Request):
    _admin(request)
    from .datasets import registry
    b = await request.json() if (await request.body()) else {}
    try:
        registry.start_download(source_id, b.get("options") or {})
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/data/{source_id}/upload")
async def data_upload(source_id: str, request: Request, file: UploadFile):
    """For sources that need a sign-in or form: upload the file you downloaded from the publisher."""
    _admin(request)
    import asyncio
    from .datasets import registry
    try:
        found = await asyncio.to_thread(registry.save_upload, source_id, file.filename, file.file)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": bool(found), "files": found}


@app.post("/api/data/{source_id}/index")
async def data_index(source_id: str, request: Request):
    _admin(request)
    from .datasets import registry
    try:
        registry.start_indexing(source_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


# ---------- tests (harness) ----------
@app.get("/api/tests")
def tests():
    from . import harness
    return harness.overview()


@app.post("/api/tests")
async def start_test(request: Request):
    from . import harness
    b = await request.json()
    try:
        rid = harness.start(b)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"id": rid}


@app.get("/api/tests/{rid}")
def get_test(rid: int):
    from . import harness
    return harness.run_detail(rid)


@app.post("/api/tests/{rid}/cancel")
def cancel_test(rid: int):
    from . import harness
    harness.cancel(rid)
    return {"ok": True}


@app.delete("/api/tests/{rid}")
def delete_test(rid: int):
    db.ex("DELETE FROM harness_runs WHERE id=?", rid)
    return {"ok": True}


# ---------- documentation ----------
DOCS = {"methodology": "METHODOLOGY", "data": "DATA"}


@app.get("/api/docs/{name}")
def doc(name: str, lang: str = "en"):
    if name not in DOCS:
        raise HTTPException(404, "No such document.")
    base = DOCS_DIR / DOCS[name]
    path = Path(f"{base}.{lang}.md") if lang != "en" and Path(f"{base}.{lang}.md").exists() else Path(f"{base}.md")
    if not path.exists():
        raise HTTPException(404, "Document missing.")
    text = path.read_text(encoding="utf-8")
    html = md.markdown(text, extensions=["tables", "fenced_code", "toc", "sane_lists"])
    return {"html": html, "lang": lang if path.name.endswith(f".{lang}.md") else "en"}


# ---------- the web app ----------
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


@app.get("/sw.js")
def service_worker():
    return FileResponse(WEB_DIR / "static" / "js" / "sw.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(WEB_DIR / "static" / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/{path:path}", response_class=HTMLResponse)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Not found.")
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})
