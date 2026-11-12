"""Conversations: interviews with one person (twin chat), focus groups and debates.

Every conversation runs on its own branch of each person, so it never changes their base record or contaminates a
panel. The person's core facts are restated on every turn (personas drift back to the model's default within
about 8 turns otherwise), long histories are cut to the most recent turns plus a running summary, and drift is
measured: every DRIFT_EVERY turns the person is quietly re-asked one of their own recorded answers.

Debates: each side's stance is pinned in its instructions and must be held. Simulated groups reach full agreement
far more often than real people (85-96% vs 51%, Shao 2026), so a debate also asks both sides the final question
before the debate starts (a no-discussion branch) and reports how far each one moved.
"""
from __future__ import annotations

import json
import random

from . import db, providers, usage
from .population import effective_record, new_branch, profile_text

KEEP_TURNS = 12
DRIFT_EVERY = 10

PERSON_SYSTEM = """You are this person, talking in your own voice. Stay this person in every reply: their age,
place, work, beliefs and way of talking. Use only the facts below; if asked about something they wouldn't know or
haven't said, answer the way they would (guessing, not knowing, changing the subject). Do not become more
agreeable, polite or knowledgeable than they would be. Keep replies short and natural, like spoken conversation.
{extra}
THE PERSON
{profile}"""


def _person(pid: int) -> dict:
    return db.q1("SELECT * FROM people WHERE id=?", pid)


def create(kind: str, person_ids: list[int], model_ref: str, title: str | None = None, study_id: int | None = None,
           stances: dict | None = None, branch_ids: dict | None = None, config: dict | None = None) -> int:
    with db.tx() as con:
        cid = con.execute("INSERT INTO chats(kind,title,study_id,model_ref,config_json,created_at) VALUES(?,?,?,?,?,?)",
                          (kind, title, study_id, model_ref, json.dumps(config or {}), db.now())).lastrowid
    for pid in person_ids:
        parent = (branch_ids or {}).get(str(pid)) or (branch_ids or {}).get(pid)
        n = db.q1("SELECT COUNT(*) AS n FROM branches WHERE person_id=?", pid)["n"] + 1
        bid = new_branch(pid, f"{kind}-{n}", {"chat": cid}, parent)
        db.ex("INSERT INTO chat_members(chat_id,person_id,branch_id,stance) VALUES(?,?,?,?)", cid, pid, bid,
              (stances or {}).get(str(pid)) or (stances or {}).get(pid))
    return cid


def get(chat_id: int) -> dict:
    c = db.q1("SELECT * FROM chats WHERE id=?", chat_id)
    if not c:
        raise KeyError(chat_id)
    c["config"] = db.loads(c.pop("config_json"), {})
    c["members"] = db.q("SELECT cm.*, p.name, p.base_json FROM chat_members cm JOIN people p ON p.id=cm.person_id "
                        "WHERE cm.chat_id=?", chat_id)
    for m in c["members"]:
        rec = json.loads(m.pop("base_json"))
        m["record"] = rec
    c["messages"] = [dict(m, meta=db.loads(m.pop("meta_json"), {})) for m in
                     db.q("SELECT * FROM messages WHERE chat_id=? ORDER BY id", chat_id)]
    return c


def _history_for(chat: dict, pid: int) -> tuple[list[dict], str]:
    """Turns from this person's point of view: their lines are 'assistant', everyone else's are 'user'."""
    names = {m["person_id"]: m["name"].split(" ")[0] for m in chat["members"]}
    msgs = [m for m in chat["messages"] if m["role"] in ("user", "person")]
    summary = ""
    if len(msgs) > KEEP_TURNS:
        older = msgs[:-KEEP_TURNS]
        summary = "Earlier in this conversation (summary): " + " / ".join(
            f"{'You' if m['person_id'] == pid else (names.get(m['person_id']) or 'Interviewer')}: {m['content'][:120]}"
            for m in older[-20:])
        msgs = msgs[-KEEP_TURNS:]
    turns = []
    for m in msgs:
        if m["role"] == "person" and m["person_id"] == pid:
            turns.append({"role": "assistant", "content": m["content"]})
        else:
            who = "Interviewer" if m["role"] == "user" else names.get(m["person_id"], "Someone")
            content = m["content"] if (m["role"] == "user" and len(chat["members"]) == 1) else f"{who}: {m['content']}"
            if turns and turns[-1]["role"] == "user":
                turns[-1]["content"] += "\n" + content
            else:
                turns.append({"role": "user", "content": content})
    return turns, summary


async def _reply(chat: dict, member: dict, prompt_suffix: str = "") -> str:
    rec, _ = effective_record(_person(member["person_id"]), member["branch_id"])
    extra = []
    if member.get("stance"):
        extra.append(f"In this discussion you hold this position and you keep holding it unless you are genuinely "
                     f"persuaded the way this person realistically could be: {member['stance']}")
    if len(chat["members"]) > 1:
        others = ", ".join(m["name"].split(" ")[0] for m in chat["members"] if m["person_id"] != member["person_id"])
        extra.append(f"You are in a group conversation with {others} and a moderator. Speak only for yourself.")
    turns, summary = _history_for(chat, member["person_id"])
    if summary:
        extra.append(summary)
    system = PERSON_SYSTEM.format(extra="\n".join(extra), profile=profile_text(rec))
    if not turns or turns[-1]["role"] != "user":
        turns.append({"role": "user", "content": prompt_suffix or "(Your turn to speak.)"})
    elif prompt_suffix:
        turns[-1]["content"] += "\n" + prompt_suffix
    comp, m = await providers.complete_ref(chat["model_ref"], system, turns, json_mode=False, max_tokens=350)
    cost = providers.cost_of(m, comp.tokens_in, comp.tokens_out)
    usage.record(chat.get("study_id"), "chat", chat["model_ref"], comp.tokens_in, comp.tokens_out, cost)
    return comp.text.strip()


def add_message(chat_id: int, role: str, content: str, person_id: int | None = None, meta: dict | None = None) -> int:
    return db.ex("INSERT INTO messages(chat_id,role,person_id,content,meta_json,ts) VALUES(?,?,?,?,?,?)",
                 chat_id, role, person_id, content, json.dumps(meta or {}), db.now())


async def say(chat_id: int, text: str) -> list[dict]:
    """The user speaks; every member replies in turn (each sees what the others said)."""
    add_message(chat_id, "user", text)
    replies = []
    chat = get(chat_id)
    for member in chat["members"]:
        reply = await _reply(chat, member)
        add_message(chat_id, "person", reply, member["person_id"])
        replies.append({"person_id": member["person_id"], "content": reply})
        chat = get(chat_id)
    turns = len([m for m in chat["messages"] if m["role"] == "user"])
    if turns and turns % DRIFT_EVERY == 0:
        await drift_check(chat_id)
    return replies


async def drift_check(chat_id: int) -> list[dict]:
    """Re-ask each member one of their own recorded answers, inside the conversation's context, and compare."""
    chat = get(chat_id)
    out = []
    for member in chat["members"]:
        rec, _ = effective_record(_person(member["person_id"]), member["branch_id"])
        views = rec.get("views") or []
        if not views:
            continue
        item = random.Random(chat_id * 7 + len(chat["messages"])).choice(views)
        probe = (f"Quick aside, answer in a few words only: {item['q']} "
                 f"Pick the answer closest to what you think.")
        reply = await _reply(chat, member, prompt_suffix=probe)
        same = item["a"].lower()[:18] in reply.lower()
        meta = {"probe": item["q"], "recorded": item["a"], "reply": reply, "consistent": same}
        add_message(chat_id, "drift", f"{item['q']} → recorded: {item['a']} · now: {reply}", member["person_id"], meta)
        out.append(meta)
    return out


async def debate(chat_id: int, question: str, rounds: int = 3) -> dict:
    """Before: each side answers alone (no-discussion branch). Then rounds of exchange. After: each answers again."""
    chat = get(chat_id)
    before, after = {}, {}
    for m in chat["members"]:
        rec, _ = effective_record(_person(m["person_id"]), m["branch_id"])
        system = PERSON_SYSTEM.format(extra="", profile=profile_text(rec))
        comp, mm = await providers.complete_ref(chat["model_ref"], system,
                                                f"{question}\nAnswer in one or two sentences, with your position first.",
                                                json_mode=False, max_tokens=200)
        usage.record(chat.get("study_id"), "chat", chat["model_ref"], comp.tokens_in, comp.tokens_out,
                     providers.cost_of(mm, comp.tokens_in, comp.tokens_out))
        before[m["person_id"]] = comp.text.strip()
    add_message(chat_id, "user", f"Debate question: {question}", meta={"debate": True})
    for r in range(rounds):
        for m in chat["members"]:
            chat = get(chat_id)
            reply = await _reply(chat, m, "Respond to the others and make your case." if r else "Give your view.")
            add_message(chat_id, "person", reply, m["person_id"], {"round": r + 1})
    chat = get(chat_id)
    for m in chat["members"]:
        reply = await _reply(chat, m, f"Final answer, one or two sentences, position first: {question}")
        after[m["person_id"]] = reply
        add_message(chat_id, "person", reply, m["person_id"], {"final": True})
    result = {"before": before, "after": after}
    cfg = chat["config"]
    cfg["debate"] = result
    db.ex("UPDATE chats SET config_json=? WHERE id=?", json.dumps(cfg), chat_id)
    return result
