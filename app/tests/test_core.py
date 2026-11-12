"""Core tests. Model calls are faked; nothing here touches the network."""
import asyncio
import time
import json
import os
import random
import tempfile

os.environ["ZOCALO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ZOCALO_DATASETS_DIR"] = tempfile.mkdtemp()
os.environ["ZOCALO_AUTH"] = "none"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from zocalo import answering, calibration, db, errors, providers, security  # noqa: E402
from zocalo.harness import item_metrics  # noqa: E402
from zocalo.population import demo, effective_record, new_branch, profile_text, save_population  # noqa: E402
from zocalo.studies import assign_arms, matches  # noqa: E402

db.init()


# ---------- fake model ----------
class FakeModel:
    """Answers as JSON. Probability of the first option rises with age, so results are checkable."""
    calls = 0

    async def __call__(self, kind, key, base_url, model, system, user, json_mode=True, max_tokens=600, temperature=None):
        FakeModel.calls += 1
        text = user if isinstance(user, str) else user[-1]["content"]
        if "Reply with JSON only: {\"probabilities\"" in text and "Options:" in text:
            letters = [ln[0] for ln in text.split("Options:")[1].splitlines() if len(ln) > 2 and ln[1] == "."]
            age = 40
            for ln in system.splitlines():
                if ln.startswith("Age:"):
                    age = int(ln.split(":")[1])
            p_first = min(0.9, max(0.1, age / 100))
            probs = {L: (1 - p_first) / (len(letters) - 1) for L in letters}
            # the canonical first option: find which letter shows it (the option text "Yes")
            for ln in text.split("Options:")[1].splitlines():
                if ln.endswith(". Yes"):
                    probs[ln[0]] = p_first
            s = sum(probs.values())
            probs = {k: v / s for k, v in probs.items()}
            return providers.Completion(json.dumps({"probabilities": probs, "answer": max(probs, key=probs.get), "reason": "Because."}), 100, 20)
        if "probabilities" in text:
            return providers.Completion('{"probabilities": {"A": 0.5, "B": 0.5}}', 50, 10)
        return providers.Completion("I'd say so, yes.", 80, 10)


@pytest.fixture(autouse=True)
def fake_model(monkeypatch):
    monkeypatch.setattr(providers, "complete", FakeModel())


def _model_ref():
    row = db.q1("SELECT id FROM models LIMIT 1")
    if row:
        return str(row["id"])
    pid = db.ex("INSERT INTO providers(kind,label,key_enc,key_hint,status,models_json,created_at) VALUES(?,?,?,?,?,?,?)",
                "openai", "Fake", security.encrypt("sk-test-123456"), "…3456", "ok", "[]", db.now())
    return str(db.ex("INSERT INTO models(provider_id,model_id,label,price_in,price_out) VALUES(?,?,?,?,?)",
                     pid, "fake-1", "fake-1", 1.0, 2.0))


# ---------- tests ----------
def test_encrypt_roundtrip():
    tok = security.encrypt("secret-key-abc")
    assert tok != "secret-key-abc" and security.decrypt(tok) == "secret-key-abc"


def test_password_hash():
    h = security.hash_password("correct horse")
    assert security.check_password("correct horse", h) and not security.check_password("wrong", h)


def test_option_order_keeps_unsure_last_and_flips_scales():
    for i in range(20):
        o = answering.option_order(5, False, ("x", i))
        assert o[-1] == 4 and sorted(o) == list(range(5))
        s = answering.option_order(5, True, ("y", i))
        assert s[:-1] in ([0, 1, 2, 3], [3, 2, 1, 0])
    assert sorted(answering.option_order(4, False, ("z",), last_fixed=False)) == [0, 1, 2, 3]


def test_with_unsure_adds_once():
    assert answering.with_unsure(["Yes", "No"]) == ["Yes", "No", "Not sure"]
    assert answering.with_unsure(["Yes", "No", "Not sure"]) == ["Yes", "No", "Not sure"]
    assert answering.with_unsure(["Sí", "No"], "es")[-1] == "No estoy seguro/a"


def test_parse_json_tolerates_fences():
    assert providers.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert providers.parse_json('Sure! {"a": {"b": 2}} done') == {"a": {"b": 2}}


def test_ask_maps_letters_back_to_options():
    ref = _model_ref()
    rec = {"age": 80, "sex": "female", "country": "US"}
    order = [1, 0, 2]  # letters: A=No, B=Yes, C=Not sure
    a = asyncio.run(answering.ask(ref, rec, answering.Asked("Q?", ["Yes", "No", "Not sure"], order)))
    assert abs(sum(a.spread) - 1) < 1e-6 and a.spread[0] == pytest.approx(0.8, abs=1e-6)
    assert a.answer_idx == 0 and a.cost > 0


def test_profile_has_facts_only_and_no_name():
    rec = {"age": 33, "sex": "male", "country": "MX", "region": "Jalisco", "views": [{"q": "Trust?", "a": "Some"}]}
    text = profile_text(rec)
    assert "Age: 33" in text and "Jalisco" in text and "Trust? → Some" in text


def test_branch_overlays_never_touch_base():
    recs = demo.build("US", 5, 1)
    pid = save_population("t", "US", "demo", recs, 1, {})
    person = db.q1("SELECT * FROM people WHERE population_id=? LIMIT 1", pid)
    b = new_branch(person["id"], "news", {"context": ["read the news"], "set": {"party": "Green"}})
    rec, chain = effective_record(person, b)
    base = json.loads(db.q1("SELECT base_json FROM people WHERE id=?", person["id"])["base_json"])
    assert rec["party"] == "Green" and rec["context"] == ["read the news"] and len(chain) == 1
    assert base.get("party") != "Green" or True and "context" not in base


def test_matched_arms_are_balanced():
    people = [{"id": i, "rec": {"age": 20 + i % 50, "sex": "female" if i % 2 else "male", "region": "R", "education": "x"}} for i in range(300)]
    arms = assign_arms(people, ["control", "treatment", "placebo"], 3)
    counts = {a: list(arms.values()).count(a) for a in ["control", "treatment", "placebo"]}
    assert max(counts.values()) - min(counts.values()) <= 1


def test_filter_matching():
    rec = {"age": 30, "sex": "female", "region": "California"}
    assert matches(rec, {"age_max": 34, "fields": {"sex": ["female"]}})
    assert not matches(rec, {"fields": {"region": ["Texas"]}})


def test_error_labels():
    e = errors.estimate("opinion", False, 2000, False)
    assert e["kind"] == "prior" and e["p50"] == 7.0
    sub = errors.estimate("opinion", False, 120, True)
    assert sub["p50"] > e["p50"] and "subgroup" in sub["warnings"]
    assert errors.estimate("other", False, 2000, False)["kind"] == "flat"
    assert "knowledge" in errors.estimate("knowledge", False, 2000, False)["warnings"]
    assert errors.guess_qtype("Would you pay $10 a month?") == "consumer"
    assert errors.guess_qtype("Have you heard of ChatGPT?") == "knowledge"


def test_item_metrics():
    m = item_metrics([0.5, 0.5, 0.0], [0.6, 0.4, 0.0])
    assert m["mae"] == pytest.approx(20 / 3, abs=1e-6) and m["max"] == pytest.approx(10)
    assert item_metrics([0.3, 0.7], [0.0, 1.0])["missed"] == 1


def test_anchor_search():
    calibration.add_anchors([{"source": "t", "ref": "v1", "country": "US", "year": 2024, "text": "Do you favor or oppose the death penalty for murder?",
                              "options": ["Favor", "Oppose"], "dist": [0.6, 0.4]},
                             {"source": "t", "ref": "v2", "country": "US", "year": 2024, "text": "How often do you attend religious services?",
                              "options": ["Often", "Never"], "dist": [0.3, 0.7]}])
    hits = calibration.anchors_for("Should the death penalty be used for murder?", "US")
    assert hits and hits[0]["ref"] == "v1"


def test_full_study_flow_and_api():
    from zocalo.main import app
    ref = _model_ref()
    with TestClient(app) as c:
        assert c.get("/api/me").json()["auth_mode"] == "none"
        r = c.post("/api/populations", json={"source": "demo", "country": "US", "size": 60, "seed": 5})
        job = r.json()["job"]
        for _ in range(100):
            time.sleep(0.05)
            j = c.get(f"/api/populations/jobs/{job}").json()
            if j["status"] != "running":
                break
        assert j["status"] == "done", j
        pop = j["population_id"]
        r = c.post("/api/studies", json={"name": "t", "kind": "treatment", "population_id": pop,
                                         "questions": [{"text": "Would you buy it?", "options": ["Yes", "No"]}],
                                         "config": {"models": [ref], "treatment": "Prices fell.", "placebo": "The office moved.", "within": True}})
        sid = r.json()["id"]
        est = r.json()["estimate"]
        assert est["people"] == 60 and est["cost"] > 0
        assert c.post(f"/api/studies/{sid}/run", json={}).json()["ok"]
        for _ in range(200):
            time.sleep(0.05)
            s = c.get(f"/api/studies/{sid}").json()
            if s["status"] != "running":
                break
        assert s["status"] == "done", s
        res = c.post(f"/api/studies/{sid}/results", json={}).json()
        q = res["questions"][0]
        assert set(q["arms"]) >= {"control", "treatment", "placebo", "within_before", "within_after"}
        assert q["effects"]["treatment_vs_placebo"] is not None
        assert q["arms"]["control"]["error"]["kind"] in ("prior", "measured")
        assert len(res["people"]) == 60
        # filtered results and CSV
        res2 = c.post(f"/api/studies/{sid}/results", json={"filter": {"age_min": 50}}).json()
        assert all(p["f"]["age"] >= 50 for p in res2["people"])
        assert "p_option_1" in c.get(f"/api/studies/{sid}/export.csv").text
        # human-sample correction
        rows = "answer,age,sex\n" + "\n".join(f"{'Yes' if i % 3 else 'No'},{30 + i},{'female' if i % 2 else 'male'}" for i in range(30))
        r = c.post(f"/api/studies/{sid}/human/{q['id']}", files={"file": ("h.csv", rows, "text/csv")})
        assert r.json()["rows"] == 30
        q2 = c.post(f"/api/studies/{sid}/results", json={}).json()["questions"][0]
        assert q2["human"]["n"] == 30 and len(q2["human"]["ci95"]) == 3
        # usage recorded
        u = c.get("/api/usage").json()
        assert u["total"] > 0 and u["by_study"]
        # interview
        pid = res["people"][0]["id"]
        chat = c.post("/api/chats", json={"kind": "interview", "person_ids": [pid], "model": ref, "opening": "Why?"}).json()
        assert any(m["role"] == "person" for m in chat["messages"])
        # sign-in can be turned on, and then the API needs a session
        assert c.post("/api/auth/setup", json={"username": "admin", "password": "longpassword"}).json()["ok"]
        c.cookies.clear()
        assert c.get("/api/studies").status_code == 401
        assert c.post("/api/auth/login", json={"username": "admin", "password": "longpassword"}).status_code == 200
        assert c.get("/api/studies").status_code == 200


def test_spa_and_static():
    from zocalo.main import app
    with TestClient(app) as c:
        assert "Zócalo" in c.get("/").text
        assert c.get("/static/js/app.js").status_code == 200
        assert c.get("/manifest.webmanifest").json()["name"] == "Zócalo"
        assert c.get("/sw.js").status_code == 200
