"""Spending: every model call is recorded, and the optional spending guard is checked before and during runs."""
from __future__ import annotations

import datetime as dt

from . import db


def record(study_id: int | None, purpose: str, model_ref: str | None, tokens_in: int, tokens_out: int, cost: float) -> None:
    db.ex("INSERT INTO usage(ts,study_id,purpose,model_ref,tokens_in,tokens_out,cost) VALUES(?,?,?,?,?,?,?)",
          db.now(), study_id, purpose, model_ref, tokens_in, tokens_out, cost)


def month_start() -> float:
    d = dt.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return d.timestamp()


def month_spent() -> float:
    return db.q1("SELECT COALESCE(SUM(cost),0) AS c FROM usage WHERE ts>=?", month_start())["c"]


def guard() -> dict:
    return {"monthly_cap": db.get_setting("monthly_cap"), "confirm_above": db.get_setting("confirm_above")}


def cap_remaining() -> float | None:
    cap = guard()["monthly_cap"]
    return None if cap in (None, "", 0) else max(0.0, float(cap) - month_spent())


def guard_status(estimate: float) -> dict:
    g = guard()
    left = cap_remaining()
    return {"month_spent": round(month_spent(), 4), "monthly_cap": g["monthly_cap"],
            "over_cap": left is not None and estimate > left,
            "needs_confirm": g["confirm_above"] not in (None, "") and estimate > float(g["confirm_above"])}


def summary() -> dict:
    by_study = db.q("SELECT u.study_id, s.name, s.kind, COUNT(*) AS calls, SUM(u.tokens_in) AS tokens_in, "
                    "SUM(u.tokens_out) AS tokens_out, SUM(u.cost) AS cost, MAX(u.ts) AS last "
                    "FROM usage u LEFT JOIN studies s ON s.id=u.study_id GROUP BY u.study_id, u.purpose "
                    "ORDER BY last DESC")
    by_model = db.q("SELECT model_ref, COUNT(*) AS calls, SUM(tokens_in) AS tokens_in, SUM(tokens_out) AS tokens_out, "
                    "SUM(cost) AS cost FROM usage GROUP BY model_ref ORDER BY cost DESC")
    by_purpose = db.q("SELECT purpose, COUNT(*) AS calls, SUM(cost) AS cost FROM usage GROUP BY purpose")
    by_month = db.q("SELECT strftime('%Y-%m', ts, 'unixepoch', 'localtime') AS month, COUNT(*) AS calls, SUM(cost) AS cost "
                    "FROM usage GROUP BY month ORDER BY month DESC LIMIT 24")
    total = db.q1("SELECT COALESCE(SUM(cost),0) AS c, COUNT(*) AS n FROM usage")
    return {"by_study": by_study, "by_model": by_model, "by_purpose": by_purpose, "by_month": by_month,
            "total": total["c"], "calls": total["n"], "month_spent": month_spent(), **guard()}
