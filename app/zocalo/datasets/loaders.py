"""Reading census and survey files: building people, matching attitudes, indexing real questions, test sets.

People are drawn in proportion to each record's official weight (weighted sampling without replacement), so a
population is self-weighting. Every fact in a person's record comes from a real record; where a source only gives
an age band, an exact age is drawn within that band and the provenance note says so.
"""
from __future__ import annotations

import ast
import json
import math
import random
import re
import zipfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from . import countries as C
from .registry import BY_ID, allowed, files, present

MISSING_RE = re.compile(r"(don.?t know|dont know|refus|no answer|not asked|missing|skipped|not applicable|^n/?a$|"
                        r"dk/|^dk$|no sabe|no contesta|ns/nr|no responde|inapplicable|iap|prefer not|not available|"
                        r"other missing|^-\d|no aplica|sin dato|can.?t choose|not stated|^ref$)", re.I)
ADMIN_RE = re.compile(r"(^EA[-_ ]|interviewer|enumerator|respondent (was|honest|understood|attitude|cooperat)|"
                      r"^int\b|psu|sampling|callback|^time |duration|language of interview|others present|"
                      r"questionnaire|^date|^weight|^wt\b)", re.I)
NOT_MENTIONED_RE = re.compile(r"(not mention|no mencion|not selected|no seleccion|^mentioned$|^menciona$)", re.I)
DK_RE = re.compile(r"(don.?t know|dont know|not sure|^dk|no sabe|unsure|can.?t choose|undecided)", re.I)


# ---------- generic helpers ----------
def weighted_sample(weights: np.ndarray, n: int, seed: int) -> np.ndarray:
    """Indices drawn in proportion to weight. Without replacement when possible (A-ES keys), with replacement when
    more people are asked for than there are records."""
    w = np.nan_to_num(np.asarray(weights, float), nan=0.0)
    w[w < 0] = 0
    if w.sum() <= 0:
        w = np.ones_like(w)
    rng = np.random.default_rng(seed)
    pos = np.flatnonzero(w > 0)
    if n <= len(pos):
        keys = rng.random(len(pos)) ** (1.0 / w[pos])
        return pos[np.argsort(-keys)[:n]]
    return rng.choice(len(w), size=n, replace=True, p=w / w.sum())


def clean_label(s) -> str:
    s = str(s).strip()
    s = re.sub(r"^\(?-?\d+\)?[.:)]\s+", "", s)          # "1. Yes" → "Yes"
    s = re.sub(r"^[A-Z]{2,3}:\s+", "", s)               # "MX: Morena" → "Morena"
    return s


def clean_question(s: str) -> str:
    s = str(s).strip()
    s = re.sub(r"^[A-Z][A-Z0-9_]{1,24}[a-z]?\.\s+", "", s)  # "SATISF. All in all…" → "All in all…"
    s = re.sub(r"^Q\d+[A-Za-z0-9_.]*[.:]\s*", "", s)          # "Q16. …" → "…"
    return s.strip()


def is_missing_label(label: str) -> bool:
    return bool(MISSING_RE.search(str(label)))


def band_age(lo: int, hi: int, rng: random.Random) -> int:
    return rng.randint(lo, hi)


def edu3(text) -> str | None:
    if text is None:
        return None
    t = str(text).lower()
    if re.search(r"bachelor|4-year|post-?grad|graduate|master|doctor|universit|higher|degree|licenciatura|tertiary|isced (5|6|7|8)|^ba\b|^ma\b", t):
        return "high"
    if re.search(r"high school|secondary|hs grad|ged|some college|associate|2-year|vocational|preparatory|a level|realschule|abitur|trade|college|post-secondary|upper|middle|diploma|secundaria|preparatoria", t):
        return "mid"
    return "low"


def age_band(age) -> str:
    if age is None:
        return "?"
    return "18–29" if age < 30 else "30–44" if age < 45 else "45–64" if age < 65 else "65+"


def _sex_from_label(label) -> str | None:
    t = str(label).lower()
    if re.search(r"female|woman|women|mujer|femenino|feminino|femme|frau|^f$", t):
        return "female"
    if re.search(r"\bmale\b|^man$|^men$|hombre|masculino|homme|mann|^m$", t):
        return "male"
    return None


# ---------- labelled files (.sav / .dta / .feather) ----------
def _read(path: Path, **kw):
    """pyreadstat with an encoding fallback (some Stata files, e.g. the GSS, aren't valid UTF-8)."""
    import pyreadstat
    reader = pyreadstat.read_sav if path.suffix.lower() == ".sav" else pyreadstat.read_dta
    try:
        return reader(str(path), **kw)
    except Exception as e:
        if "utf-8" not in str(e).lower() and "decode" not in str(e).lower():
            raise
        return reader(str(path), encoding="LATIN1", **kw)


def read_meta(path: Path):
    return _read(path, metadataonly=True)[1]


def read_cols(path: Path, cols: list[str], row_offset: int = 0, row_limit: int = 0) -> pd.DataFrame:
    if path.suffix.lower() == ".feather":
        return pd.read_feather(path, columns=cols)
    df, _ = _read(path, usecols=cols, row_offset=row_offset, row_limit=row_limit, apply_value_formats=False)
    return df


def labeller(meta, var: str):
    """code → clean label (None when the code means missing). Unlabelled numbers pass through."""
    vl = (meta.variable_value_labels or {}).get(var, {}) if meta is not None else {}

    def f(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        if isinstance(v, str):
            return None if (not v.strip() or is_missing_label(v)) else clean_label(v)
        key = v
        if isinstance(v, float) and v.is_integer():
            key = int(v)
        lab = vl.get(key, vl.get(float(key), None)) if vl else None
        if lab is None:
            if isinstance(key, (int, float)) and key < 0:
                return None
            return key if not vl else None
        return None if is_missing_label(lab) else clean_label(lab)
    return f


# ---------- survey sources (respondents as people, attitude donors, anchors, twins tests) ----------
# Each entry maps person fields to candidate variable names (first one present wins).
SURVEYS = {
    "ces": {"name": "Cooperative Election Study (US respondents)", "country": "US", "year_var": "year",
            "fields": {"age": ["age"], "sex": ["gender"], "region": ["state"], "education": ["educ"], "income": ["faminc"],
                       "employment": ["employ"], "race": ["race"], "marital": ["marstat"], "party": ["pid3"],
                       "ideology": ["ideo5"], "vote_last": ["voted_pres_24", "voted_pres_20"], "religion": ["religion"],
                       "religiosity": ["relig_imp"]}, "weight": ["weight", "weight_cumulative"], "recent_years": 3,
            # the feather file keeps some columns as numeric codes; labels from the CES guide
            "codes": {"sex": {1: "male", 2: "female"},
                      "education": {1: "no high school", 2: "high school graduate", 3: "some college", 4: "2-year degree",
                                    5: "4-year degree", 6: "post-graduate degree"},
                      "race": {1: "White", 2: "Black", 3: "Hispanic", 4: "Asian", 5: "Native American", 6: "mixed race",
                               7: "other race", 8: "Middle Eastern"},
                      "employment": {1: "working full-time", 2: "working part-time", 3: "temporarily laid off", 4: "unemployed",
                                     5: "retired", 6: "permanently disabled", 7: "homemaker", 8: "student", 9: "other"},
                      "marital": {1: "married", 2: "separated", 3: "divorced", 4: "widowed", 5: "single", 6: "domestic partnership"},
                      "party": {1: "Democrat", 2: "Republican", 3: "independent", 4: "other party"},
                      "ideology": {1: "very liberal", 2: "liberal", 3: "moderate", 4: "conservative", 5: "very conservative"},
                      "religion": {1: "Protestant", 2: "Catholic", 3: "Mormon", 4: "Orthodox Christian", 5: "Jewish", 6: "Muslim",
                                   7: "Buddhist", 8: "Hindu", 9: "atheist", 10: "agnostic", 11: "nothing in particular", 12: "something else"},
                      "religiosity": {1: "very important", 2: "somewhat important", 3: "not too important", 4: "not at all important"}}},
    "gss": {"name": "General Social Survey (US respondents)", "country": "US", "year_var": "year",
            "fields": {"age": ["age"], "sex": ["sex"], "region": ["region"], "education": ["degree"], "income": ["income16"],
                       "employment": ["wrkstat"], "race": ["race"], "marital": ["marital"], "party": ["partyid"],
                       "ideology": ["polviews"], "vote_last": ["pres20"], "religion": ["relig"], "religiosity": ["attend"],
                       "urban": ["xnorcsiz"]}, "weight": ["wtssnrps", "wtssps", "wtssall"], "recent_years": 1},
    "wvs": {"name": "World Values Survey (respondents)", "country_var": ["B_COUNTRY", "B_COUNTRY_ALPHA"],
            "fields": {"age": ["Q262"], "sex": ["Q260"], "region": ["N_REGION_ISO", "N_REGION_WVS"], "education": ["Q275R", "Q275"],
                       "income": ["Q288R", "Q288"], "employment": ["Q279"], "marital": ["Q273"], "urban": ["H_URBRURAL"],
                       "party": ["Q223"], "ideology": ["Q240"], "religion": ["Q289"], "religiosity": ["Q6"]},
            "weight": ["W_WEIGHT", "S018"]},
    "ess": {"name": "European Social Survey (respondents)", "country_var": ["cntry"],
            "fields": {"age": ["agea"], "sex": ["gndr"], "region": ["region"], "education": ["eisced"], "income": ["hinctnta"],
                       "employment": ["mnactic"], "marital": ["maritalb"], "urban": ["domicil"], "ideology": ["lrscale"],
                       "religion": ["rlgdnm"], "religiosity": ["rlgatnd"]}, "party_prefix": "prtvt",
            "weight": ["anweight", "pspwght"]},
    "afrobarometer": {"name": "Afrobarometer (respondents)", "country_var": ["COUNTRY"],
                      "fields": {"age": ["Q1"], "sex": ["Q101"], "region": ["REGION"], "education": ["EDUC_COND", "Q96"],
                                 "employment": ["Q94A"], "urban": ["URBRUR"], "party": ["Q89B"], "religion": ["RELIG_COND", "Q97"]},
                      "weight": ["withinwt_hh", "withinwt_ea", "withinwt"]},
    "latinobarometro": {"name": "Latinobarómetro (respondents)", "country_var": ["IDENPA", "idenpa"],
                        "fields": {"age": ["EDAD", "edad"], "sex": ["SEXO", "sexo"], "region": ["REG", "reg"],
                                   "education": ["REEDUC.1", "REEDUC_1", "reeduc_1"], "income": ["S5", "s5"],
                                   "employment": ["S18.A", "S18_A"], "race": ["S7", "s7"], "party": ["P39STGBS.A", "P39STGBS_A"],
                                   "ideology": ["P16ST", "p16st"], "religion": ["S1", "s1"], "religiosity": ["S1A", "s1a"]},
                        "weight": ["WT", "wt"]},
    "arab_barometer": {"name": "Arab Barometer (respondents)", "country_var": ["COUNTRY", "country"],
                       "fields": {"age": ["Q1001"], "sex": ["Q1002"], "region": ["Q1"], "education": ["Q1003"],
                                  "income": ["Q1016"], "employment": ["Q1005"], "marital": ["Q1010"], "urban": ["Q13"],
                                  "religion": ["Q1012"], "religiosity": ["Q609"]}, "weight": ["WT", "wt"]},
    "pew_atp": {"name": "Pew American Trends Panel (US respondents, newest wave)", "country": "US",
                "fields": {"age": ["F_AGECAT"], "sex": ["F_GENDER", "F_SEX"], "region": ["F_CREGION"],
                           "education": ["F_EDUCCAT2", "F_EDUCCAT"], "income": ["F_INC_SDT1", "F_INC_TIER2"],
                           "race": ["F_RACETHNMOD", "F_RACETHNMOD3", "F_RACECMB2"], "marital": ["F_MARITAL"],
                           "urban": ["F_METRO"], "party": ["F_PARTY_FINAL", "F_PARTYSUM_FINAL"], "ideology": ["F_IDEO"],
                           "religion": ["F_RELIG", "F_RELIG4"], "religiosity": ["F_ATTEND"]},
                "weight_prefix": "WEIGHT_W", "age_bands": {1: (18, 29), 2: (30, 49), 3: (50, 64), 4: (65, 85)}},
}
CENSUS = {"acs_pums": {"name": "US Census ACS 2024 records", "note": "Real anonymised census records, drawn by their census weights. Attitudes are matched from CES (or GSS) respondents with the same age band, sex and education."},
          "uk_census": {"name": "UK Census 2021 records (England & Wales)", "note": "Real census records. Exact age is drawn within the census age band; no education or income in this file. Attitudes are matched from ESS or WVS UK respondents if downloaded."},
          "ca_pumf": {"name": "Canada Census 2021 records", "note": "Real census records drawn by weight. Exact age drawn within the census age band. Attitudes matched from WVS Canada respondents if downloaded."}}
POPULATION_SOURCES = {**{k: {"name": v["name"], "note": v["note"]} for k, v in CENSUS.items()},
                      **{k: {"name": v["name"], "note": "Each person is a real survey respondent: their demographics and some of their own answers. Drawn by the survey's weights."}
                         for k, v in SURVEYS.items()}}


def survey_file(sid: str) -> Path | None:
    fs = files(sid)
    if not fs:
        return None
    if sid == "pew_atp":  # newest wave
        def wave(p):
            m = re.search(r"W(\d+)", p.name)
            return int(m.group(1)) if m else -1
        return max(fs, key=wave)
    return max(fs, key=lambda p: p.stat().st_size)


def _first(names: list[str], cols: set[str]) -> str | None:
    lower = {c.lower(): c for c in cols}
    for n in names:
        if n in cols:
            return n
        if n.lower() in lower:
            return lower[n.lower()]
    return None


@lru_cache(maxsize=8)
def _survey_frame(sid: str, path_str: str, mtime: float):
    """Respondent table with resolved demographic columns, the weight, the country, and the meta."""
    path = Path(path_str)
    cfg = SURVEYS[sid]
    if path.suffix == ".feather":
        cols = set(_feather_cols(path))
        meta = None
    else:
        meta = read_meta(path)
        cols = set(meta.column_names)
    use = {}
    for f, names in cfg["fields"].items():
        c = _first(names, cols)
        if c:
            use[f] = c
    if cfg.get("party_prefix") and "party" not in use:
        party_cols = sorted(c for c in cols if c.lower().startswith(cfg["party_prefix"]))
        if party_cols:
            use["party_cols"] = party_cols
    wcol = _first(cfg.get("weight", []), cols)
    if not wcol and cfg.get("weight_prefix"):
        wc = [c for c in cols if c.upper().startswith(cfg["weight_prefix"]) and re.fullmatch(r"WEIGHT_W\d+", c.upper())]
        wcol = wc[0] if wc else None
    ccol = _first(cfg.get("country_var", []), cols) if cfg.get("country_var") else None
    ycol = _first([cfg["year_var"]], cols) if cfg.get("year_var") else None
    need = [c for c in list(use.values()) if isinstance(c, str)] + use.get("party_cols", []) + [x for x in [wcol, ccol, ycol] if x]
    df = read_cols(path, sorted(set(need)))
    if ycol and cfg.get("recent_years"):
        years = pd.to_numeric(df[ycol], errors="coerce")
        df = df[years >= years.max() - (cfg["recent_years"] - 1)]
    # keep the original row numbers: view and item columns are read later and aligned with .loc
    return df, meta, use, wcol, ccol, sorted(cols)


def _feather_cols(path: Path) -> list[str]:
    import pyarrow.ipc as ipc
    with ipc.open_file(str(path)) as f:
        return f.schema.names


def survey_frame(sid: str, path: Path | None = None):
    path = path or survey_file(sid)
    if not path:
        raise ValueError(f"{BY_ID[sid]['name']} isn't downloaded.")
    return _survey_frame(sid, str(path), path.stat().st_mtime)


def _country_series(sid: str, df: pd.DataFrame, meta, ccol: str | None) -> pd.Series:
    cfg = SURVEYS[sid]
    if cfg.get("country"):
        return pd.Series([cfg["country"]] * len(df), index=df.index)
    lab = labeller(meta, ccol)
    vals = df[ccol]
    out = []
    cache = {}
    for v in vals:
        if v not in cache:
            # The file's own label first: Afrobarometer and Arab Barometer number countries their own way, so
            # code 8 is Jordan there, not ISO 008 (Albania). The bare code is the fallback for unlabelled files.
            label = lab(v)
            a2 = C.to_a2(label) if isinstance(label, str) else None
            if a2 is None:
                a2 = C.to_a2(v if isinstance(v, str) else (int(v) if v == v and v is not None else None))
            cache[v] = a2
        out.append(cache[v])
    return pd.Series(out, index=df.index)


def countries_for(sid: str) -> list[dict]:
    from ..config import DATA_DIR
    fs = files(sid)
    key = f"{sid}:" + ",".join(f"{p.name}:{p.stat().st_mtime:.0f}" for p in fs)
    cache_file = DATA_DIR / "countries-cache.json"
    try:
        cache = json.loads(cache_file.read_text())
    except (OSError, ValueError):
        cache = {}
    if key in cache:
        return cache[key]
    out = _countries_for(sid)
    if out and out[0].get("code"):
        cache[key] = out
        cache_file.write_text(json.dumps(cache))
    return out


def _countries_for(sid: str) -> list[dict]:
    try:
        if sid in CENSUS:
            return [{"code": {"acs_pums": "US", "uk_census": "GB", "ca_pumf": "CA"}[sid],
                     "name": {"acs_pums": "United States", "uk_census": "England & Wales", "ca_pumf": "Canada"}[sid]}]
        df, meta, use, wcol, ccol, _ = survey_frame(sid)
        cs = _country_series(sid, df, meta, ccol).dropna().value_counts()
        return [{"code": c, "name": f"{C.name(c)} ({n:,} respondents)"} for c, n in cs.items()]
    except Exception as e:  # unreadable file: say so instead of crashing the page
        return [{"code": "", "name": f"couldn't read the file: {str(e)[:80]}"}]


def _person_from_row(sid: str, row, meta, use: dict, country: str, rng: random.Random) -> dict:
    rec: dict = {"country": country, "country_name": C.name(country)}
    for f, col in use.items():
        if f == "party_cols":
            for pc in col:
                v = labeller(meta, pc)(row[pc])
                if v not in (None, ""):
                    rec["party"] = f"voted {v} (last national election)"
                    break
            continue
        raw = row[col]
        if f == "age":
            bands = SURVEYS[sid].get("age_bands")
            try:
                if bands:
                    lo, hi = bands[int(raw)]
                    rec["age"] = band_age(lo, hi, rng)
                    rec["age_note"] = f"{lo}–{hi}"
                else:
                    a = int(float(raw))
                    if 15 <= a <= 105:
                        rec["age"] = a
            except (TypeError, ValueError, KeyError):
                pass
            continue
        codes = SURVEYS.get(sid, {}).get("codes", {}).get(f)
        if meta is None and codes is not None and not isinstance(raw, str):
            try:
                val = codes.get(int(float(raw)))
            except (TypeError, ValueError):
                val = None
        elif meta is not None:
            val = labeller(meta, col)(raw)
        else:
            val = None if raw is None or (isinstance(raw, float) and math.isnan(raw)) or is_missing_label(raw) else clean_label(raw)
            if val is not None and re.fullmatch(r"-?\d+(\.0)?", str(val)):
                val = None  # an unlabelled code is no use in a profile
        if val in (None, ""):
            continue
        if f == "sex":
            s = _sex_from_label(val)
            if s:
                rec["sex"] = s
            continue
        if f == "region" and sid in ("wvs",) and re.match(r"^[A-Z]{2}-", str(val)):
            val = str(val)
        rec[f] = str(val)
    return rec


def _views_vars(sid: str, df_cols: list[str], meta, use: dict, k: int, seed: int, exclude: set[str] = frozenset()) -> list[str]:
    if meta is None:
        return []
    demo = {c.lower() for c in (list(v for v in use.values() if isinstance(v, str)) + use.get("party_cols", []))}
    labels = meta.column_names_to_labels or {}
    vls = meta.variable_value_labels or {}
    cands = []
    for c in df_cols:
        lab = labels.get(c) or ""
        if c.lower() in demo or c in exclude or len(lab) < 20 or ADMIN_RE.search(lab):
            continue
        if re.match(r"^(f_|weight|wt|id|case|resp|qkey|interview|date|time|lang|mode|device|form|xtab|[a-z]?_?year)", c, re.I):
            continue
        vl = vls.get(c)
        if not vl:
            continue
        valid = [v for v in vl.values() if not is_missing_label(v)]
        if 2 <= len(valid) <= 7:
            cands.append(c)
    rng = random.Random(seed)
    rng.shuffle(cands)
    return cands[: k * 3]


def _respondents(sid: str, country: str, n: int, seed: int, n_views: int = 12, exclude_vars: set[str] = frozenset(),
                 with_index: bool = False):
    df, meta, use, wcol, ccol, allcols = survey_frame(sid)
    cs = _country_series(sid, df, meta, ccol)
    mask = (cs == country).to_numpy()
    sub = df[mask]
    if not len(sub):
        raise ValueError(f"No {C.name(country)} respondents in this file.")
    w = pd.to_numeric(sub[wcol], errors="coerce").fillna(0).to_numpy() if wcol else np.ones(len(sub))
    idx = weighted_sample(w, n, seed)
    rows = sub.iloc[idx]
    rng = random.Random(seed)
    view_vars = _views_vars(sid, allcols, meta, use, n_views, seed, exclude_vars) if n_views else []
    vdf = read_cols(survey_file(sid), view_vars).loc[sub.index[idx]] if view_vars and meta is not None else None
    labels = (meta.column_names_to_labels or {}) if meta is not None else {}
    out = []
    for j, (ix, row) in enumerate(rows.iterrows()):
        rec = _person_from_row(sid, row, meta, use, country, rng)
        if vdf is not None:
            views = []
            for c in view_vars:
                a = labeller(meta, c)(vdf.iloc[j][c])
                if a not in (None, "") and not NOT_MENTIONED_RE.search(str(a)):
                    views.append({"q": clean_question(labels.get(c, c)), "a": str(a), "var": c})
                if len(views) >= n_views:
                    break
            rec["views"] = views
        rec["provenance"] = {"kind": "respondent", "source": BY_ID[sid]["name"], "ref": f"{sid}:{ix}",
                             "note": f"A real respondent to {BY_ID[sid]['name']}, drawn by the survey weight."
                                     + (" Exact age drawn within their age band." if rec.get("age_note") else "")}
        if with_index:
            rec["_row"] = int(ix)
        out.append(rec)
    return out, len(sub)


# ---------- census sources ----------
SCHL_BANDS = [(1, 15, "less than high school"), (16, 17, "high school graduate"), (18, 20, "some college or associate degree"),
              (21, 21, "bachelor's degree"), (22, 24, "graduate degree")]
RACE = {1: "White", 2: "Black", 3: "American Indian", 4: "Alaska Native", 5: "American Indian/Alaska Native", 6: "Asian",
        7: "Pacific Islander", 8: "other race", 9: "two or more races"}
MAR = {1: "married", 2: "widowed", 3: "divorced", 4: "separated", 5: "never married"}
REGION = {1: "Northeast", 2: "Midwest", 3: "South", 4: "West", 9: "Puerto Rico"}
OCC_GROUPS = [(10, 440, "manager"), (500, 960, "business or finance worker"), (1005, 1240, "computer or math worker"),
              (1305, 1560, "engineer or architect"), (1600, 1980, "scientist"), (2001, 2060, "social or community worker"),
              (2100, 2180, "legal worker"), (2205, 2555, "teacher or education worker"), (2600, 2920, "arts, media or sports worker"),
              (3000, 3550, "healthcare practitioner"), (3601, 3655, "healthcare support worker"), (3700, 3960, "protective service worker"),
              (4000, 4160, "food preparation or serving worker"), (4200, 4255, "cleaning or grounds worker"),
              (4330, 4655, "personal care worker"), (4700, 4965, "sales worker"), (5000, 5940, "office or administrative worker"),
              (6005, 6130, "farming, fishing or forestry worker"), (6200, 6950, "construction or extraction worker"),
              (7000, 7640, "installation or repair worker"), (7700, 8990, "production worker"), (9005, 9760, "transportation worker"),
              (9800, 9830, "military")]


def _occ(code) -> str | None:
    try:
        c = int(float(code))
    except (TypeError, ValueError):
        return None
    for lo, hi, label in OCC_GROUPS:
        if lo <= c <= hi:
            return label
    return None


def _income_band(dollars) -> str | None:
    try:
        d = float(dollars)
    except (TypeError, ValueError):
        return None
    if math.isnan(d):
        return None
    for cut, label in [(0, "no income or a loss"), (15000, "under $15,000"), (30000, "$15,000–29,999"), (50000, "$30,000–49,999"),
                       (75000, "$50,000–74,999"), (100000, "$75,000–99,999"), (150000, "$100,000–149,999")]:
        if d <= cut:
            return label
    return "$150,000 or more"


def _acs(n: int, seed: int) -> list[dict]:
    path = files("acs_pums")[0]
    cols_want = ["SERIALNO", "AGEP", "SEX", "STATE", "ST", "REGION", "SCHL", "PINCP", "ADJINC", "ESR", "COW", "OCCP", "RAC1P",
                 "HISP", "MAR", "NP", "PWGTP"]
    rng = np.random.default_rng(seed)
    best_keys, best_rows = np.empty(0), None
    with zipfile.ZipFile(path) as z:
        members = [m for m in z.namelist() if re.match(r"psam_pus[a-z]?\.csv$|psam_p\d+\.csv$", m.split("/")[-1])]
        for m in members:
            with z.open(m) as f:
                header = pd.read_csv(f, nrows=0).columns
            usecols = [c for c in cols_want if c in header]
            with z.open(m) as f:
                for chunk in pd.read_csv(f, usecols=usecols, chunksize=250_000, dtype={"SERIALNO": str}):
                    chunk = chunk[chunk["AGEP"] >= 18]
                    w = chunk["PWGTP"].clip(lower=0).to_numpy(float)
                    keys = rng.random(len(chunk)) ** (1.0 / np.maximum(w, 1e-9))
                    keys[w <= 0] = -1
                    allk = np.concatenate([best_keys, keys])
                    allr = pd.concat([best_rows, chunk]) if best_rows is not None else chunk
                    top = np.argsort(-allk)[:n]
                    best_keys, best_rows = allk[top], allr.iloc[top]
    pyrng = random.Random(seed)
    out = []
    for _, r in best_rows.iterrows():
        st = int(r.get("STATE", r.get("ST", 0)) or 0)
        schl = int(r["SCHL"]) if not pd.isna(r.get("SCHL")) else None
        edu = next((lab for lo, hi, lab in SCHL_BANDS if schl is not None and lo <= schl <= hi), None)
        esr = int(r["ESR"]) if not pd.isna(r.get("ESR")) else None
        emp = {1: "employed", 2: "employed", 3: "unemployed", 4: "in the armed forces", 5: "in the armed forces",
               6: "not in the labour force"}.get(esr)
        if emp == "employed" and not pd.isna(r.get("COW")) and int(r["COW"]) in (6, 7):
            emp = "self-employed"
        if emp == "not in the labour force" and r["AGEP"] >= 62:
            emp = "not working (likely retired)"
        hisp = int(r["HISP"]) if not pd.isna(r.get("HISP")) else 1
        race = "Hispanic" if hisp > 1 else RACE.get(int(r["RAC1P"]))
        inc = r.get("PINCP")
        if not pd.isna(inc) and not pd.isna(r.get("ADJINC")):
            inc = float(inc) * float(r["ADJINC"]) / 1e6
        rec = {"country": "US", "country_name": "United States", "region": C.US_STATES.get(st, REGION.get(int(r.get("REGION", 0) or 0))),
               "age": int(r["AGEP"]), "sex": "male" if int(r["SEX"]) == 1 else "female", "education": edu,
               "employment": emp, "occupation": _occ(r.get("OCCP")) if emp in ("employed", "self-employed") else None,
               "income": f"personal income {_income_band(inc)}" if _income_band(inc) else None, "race": race,
               "marital": MAR.get(int(r["MAR"])) if not pd.isna(r.get("MAR")) else None,
               "household": f"{int(r['NP'])} people in the household" if not pd.isna(r.get("NP")) else None,
               "_census_region": REGION.get(int(r.get("REGION", 0) or 0)),
               "provenance": {"kind": "census", "source": "US Census ACS PUMS 2024", "ref": f"ACS-{r['SERIALNO']}",
                              "note": "A real, anonymised ACS 2024 census record, drawn by its census weight."}}
        out.append({k: v for k, v in rec.items() if v is not None})
    pyrng.shuffle(out)
    return out


UK_AGE = {2: (18, 24), 3: (25, 34), 4: (35, 44), 5: (45, 54), 6: (55, 64), 7: (65, 90)}
UK_REGION = {"E12000001": "North East", "E12000002": "North West", "E12000003": "Yorkshire and The Humber",
             "E12000004": "East Midlands", "E12000005": "West Midlands", "E12000006": "East of England",
             "E12000007": "London", "E12000008": "South East", "E12000009": "South West", "W92000004": "Wales"}
UK_ECON = {1: "employee", 2: "self-employed", 3: "unemployed", 4: "student (working or looking)", 5: "retired", 6: "student",
           7: "looking after home or family", 8: "long-term sick or disabled", 9: "other"}
UK_ETH = {1: "Asian", 2: "Black", 3: "Mixed", 4: "White", 5: "other ethnic group"}
UK_MAR = {1: "never married", 2: "married or civil partnership", 3: "separated", 4: "divorced", 5: "widowed"}
UK_REL = {1: "no religion", 2: "Christian", 3: "Buddhist", 4: "Hindu", 5: "Jewish", 6: "Muslim", 7: "Sikh", 8: "other religion"}
UK_OCC = {1: "manager or director", 2: "professional", 3: "associate professional", 4: "administrative or secretarial worker",
          5: "skilled trades worker", 6: "caring, leisure or service worker", 7: "sales or customer service worker",
          8: "process, plant or machine operative", 9: "elementary occupation"}
UK_GRADE = {1: "AB (higher or intermediate managerial/professional)", 2: "C1 (supervisory, clerical, junior managerial)",
            3: "C2 (skilled manual)", 4: "DE (semi-skilled, unskilled, or not working)"}


def _uk(n: int, seed: int) -> list[dict]:
    df = pd.read_csv(files("uk_census")[0])
    df = df[df["resident_age_7d"].isin(UK_AGE.keys())]
    idx = weighted_sample(np.ones(len(df)), n, seed)
    rng = random.Random(seed)
    out = []
    for _, r in df.iloc[idx].iterrows():
        lo, hi = UK_AGE[int(r["resident_age_7d"])]
        rec = {"country": "GB", "country_name": "United Kingdom", "region": UK_REGION.get(str(r["region"]), str(r["region"])),
               "age": rng.randint(lo, hi), "age_note": f"{lo}–{hi}", "sex": "female" if int(r["sex"]) == 1 else "male",
               "employment": UK_ECON.get(int(r["economic_activity_status_10m"])), "occupation": UK_OCC.get(int(r["occupation_10a"])),
               "race": UK_ETH.get(int(r["ethnic_group_tb_6a"])), "marital": UK_MAR.get(int(r["legal_partnership_status_6a"])),
               "religion": UK_REL.get(int(r["religion_tb"])), "income": f"social grade {UK_GRADE[int(r['approx_social_grade'])]}"
               if int(r["approx_social_grade"]) in UK_GRADE else None,
               "provenance": {"kind": "census", "source": "ONS Census 2021 teaching sample", "ref": f"UK-{r['resident_id_m']}",
                              "note": "A real census record (England & Wales). Exact age drawn within the census age band."}}
        out.append({k: v for k, v in rec.items() if v is not None})
    return out


CA_AGE = {7: (18, 19), 8: (20, 24), 9: (25, 29), 10: (30, 34), 11: (35, 39), 12: (40, 44), 13: (45, 49), 14: (50, 54),
          15: (55, 59), 16: (60, 64), 17: (65, 69), 18: (70, 74), 19: (75, 79), 20: (80, 84), 21: (85, 95)}
CA_PR = {10: "Newfoundland and Labrador", 11: "Prince Edward Island", 12: "Nova Scotia", 13: "New Brunswick", 24: "Quebec",
         35: "Ontario", 46: "Manitoba", 47: "Saskatchewan", 48: "Alberta", 59: "British Columbia", 70: "the territories"}
CA_EDU = {1: "no certificate", 2: "high school", 3: "trades or college", 4: "trades or college", 5: "trades or college",
          6: "trades or college", 7: "trades or college", 8: "university below bachelor", 9: "bachelor's degree",
          10: "graduate degree", 11: "graduate degree", 12: "graduate degree", 13: "graduate degree"}
CA_MAR = {1: "never married", 2: "married", 3: "common-law", 4: "separated", 5: "divorced", 6: "widowed"}
CA_VM = {1: "not a visible minority", 2: "South Asian", 3: "Chinese", 4: "Black", 5: "Filipino", 6: "Arab", 7: "Latin American",
         8: "Southeast Asian", 9: "West Asian", 10: "Korean", 11: "Japanese", 12: "other visible minority", 13: "multiple visible minorities"}


def _ca(n: int, seed: int) -> list[dict]:
    path = files("ca_pumf")[0]
    cols = ["AGEGRP", "Gender", "PR", "CMA", "HDGREE", "HHInc", "LFACT", "MarStH", "VISMIN", "WEIGHT", "PPSORT"]
    with zipfile.ZipFile(path) as z:
        member = next(m for m in z.namelist() if m.lower().endswith(".csv") and "ind" in m.lower())
        with z.open(member) as f:
            df = pd.read_csv(f, usecols=lambda c: c in cols)
    df = df[df["AGEGRP"].isin(CA_AGE.keys())]
    idx = weighted_sample(df["WEIGHT"].to_numpy(float), n, seed)
    rng = random.Random(seed)
    out = []
    for _, r in df.iloc[idx].iterrows():
        lo, hi = CA_AGE[int(r["AGEGRP"])]
        lf = int(r["LFACT"])
        rec = {"country": "CA", "country_name": "Canada", "region": CA_PR.get(int(r["PR"])), "age": rng.randint(lo, hi), "age_note": f"{lo}–{hi}",
               "sex": "female" if int(r["Gender"]) == 1 else "male", "education": CA_EDU.get(int(r["HDGREE"])),
               "employment": "employed" if lf in (1, 2) else "unemployed" if 3 <= lf <= 10 else "not in the labour force" if 11 <= lf <= 14 else None,
               "marital": CA_MAR.get(int(r["MarStH"])), "race": CA_VM.get(int(r["VISMIN"])),
               "urban": "a large city" if int(r["CMA"]) in (535, 462, 933, 825, 835, 505) else "a smaller city, town or rural area" if int(r["CMA"]) == 999 else "a city",
               "provenance": {"kind": "census", "source": "Statistics Canada 2021 Census PUMF", "ref": f"CA-{r['PPSORT']}",
                              "note": "A real census record, drawn by its weight. Exact age drawn within the census age band."}}
        out.append({k: v for k, v in rec.items() if v is not None})
    return out


# ---------- attitude matching ----------
ATTITUDE_FIELDS = ["party", "ideology", "vote_last", "religion", "religiosity"]


def match_attitudes(people: list[dict], country: str, seed: int) -> str | None:
    """Give census people attitudes from real survey respondents with the same age band, sex and education level."""
    donor_sources = {"US": ["ces", "gss", "pew_atp"], "GB": ["ess", "wvs"], "CA": ["wvs"]}.get(country, ["ess", "wvs"])
    for sid in donor_sources:
        if not files(sid) or not allowed(BY_ID[sid]):
            continue
        try:
            donors, _ = _respondents(sid, country, 6000, seed + 7, n_views=8)
        except Exception:
            continue
        cells: dict = {}
        for d in donors:
            for key in [(age_band(d.get("age")), d.get("sex"), edu3(d.get("education"))), (age_band(d.get("age")), d.get("sex")), (age_band(d.get("age")),)]:
                cells.setdefault(key, []).append(d)
        rng = random.Random(seed)
        for p in people:
            keys = [(age_band(p.get("age")), p.get("sex"), edu3(p.get("education"))), (age_band(p.get("age")), p.get("sex")), (age_band(p.get("age")),)]
            for k in keys:
                if k in cells:
                    d = rng.choice(cells[k])
                    on = ["age band", "sex", "education level"][: len(k)]
                    for f in ATTITUDE_FIELDS:
                        if d.get(f) and not p.get(f):
                            p[f] = d[f]
                    if d.get("views"):
                        p["views"] = d["views"]
                    p["provenance"]["attitudes"] = (f"Attitudes and past answers matched from {BY_ID[sid]['name']} respondent "
                                                    f"{d['provenance']['ref']} (same {', '.join(on)}). Matching adds error of its own.")
                    break
        return BY_ID[sid]["name"]
    return None


def build_population(source: str, country: str, n: int, seed: int, options: dict) -> tuple[list[dict], dict]:
    if not present():
        raise ValueError("The dataset folder isn't available (drive unplugged?).")
    if not allowed(BY_ID[source]):
        raise ValueError("Non-commercial data is switched off in Settings.")
    if source in CENSUS:
        people = {"acs_pums": _acs, "uk_census": _uk, "ca_pumf": _ca}[source](n, seed)
        matched = match_attitudes(people, country, seed)
        for p in people:
            p.pop("_census_region", None)
        meta = {"description": CENSUS[source]["note"], "attitudes_from": matched,
                "weights": "Drawn in proportion to census weights, so the population is self-weighting."}
        if not matched:
            meta["warning"] = "No opinion survey downloaded for matching: these people have demographics only."
        return people, meta
    if source in SURVEYS:
        people, available = _respondents(source, country, n, seed)
        meta = {"description": POPULATION_SOURCES[source]["note"], "respondents_available": available,
                "weights": "Drawn in proportion to the survey's weights."}
        if n > available:
            meta["warning"] = f"Only {available:,} respondents for this country, so some appear more than once."
        return people, meta
    raise ValueError("Unknown source.")


# ---------- question index (anchors) ----------
def _survey_year(path: Path) -> int | None:
    """The year in the file or folder name: "ESS11 2023.sav", or Pew's "W169_May25/ATP W169.sav"."""
    for name in (path.name, path.parent.name):
        m = re.search(r"(19|20)\d\d", name)
        if m:
            return int(m.group(0))
    m = re.search(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d\d)$", path.parent.name)
    return 2000 + int(m.group(1)) if m else None


def _items_from_survey(sid: str, country_filter: str | None = None, max_items: int = 4000, path: Path | None = None):
    """Every labelled categorical question with its real, weighted answer shares, per country."""
    path = path or survey_file(sid)
    meta = read_meta(path)
    df, _, use, wcol, ccol, allcols = survey_frame(sid, path)
    labels = meta.column_names_to_labels or {}
    vls = meta.variable_value_labels or {}
    demo = {c for c in use.values() if isinstance(c, str)} | set(use.get("party_cols", []))
    cands = []
    for c in allcols:
        lab = labels.get(c) or ""
        vl = vls.get(c)
        if not vl or c in demo or len(lab) < 12 or c in (wcol, ccol):
            continue
        if re.match(r"^(weight|wt|id$|case|resp|qkey|interview|date|time|lang|mode|device|form|xtab)", c, re.I):
            continue
        valid = [(k, v) for k, v in vl.items() if not is_missing_label(v) or DK_RE.search(str(v))]
        sub = [(k, v) for k, v in valid if not DK_RE.search(str(v))]
        if 2 <= len(sub) <= 8:
            cands.append(c)
    cands = cands[:max_items]
    year = _survey_year(path)
    countries = _country_series(sid, df, meta, ccol)
    weights = pd.to_numeric(df[wcol], errors="coerce").fillna(0).to_numpy() if wcol else np.ones(len(df))
    items = []
    for i in range(0, len(cands), 300):
        batch = cands[i:i + 300]
        vals = read_cols(path, batch)
        if len(vals) != len(df):  # recent-years filter (GSS/CES) applied to the frame: align by row number
            vals = vals.loc[df.index]
        for c in batch:
            vl = vls[c]
            opts_codes = [k for k, v in vl.items() if not is_missing_label(v) and not DK_RE.search(str(v))]
            dk_codes = [k for k, v in vl.items() if DK_RE.search(str(v))]
            options = [clean_label(vl[k]) for k in opts_codes]
            col = pd.to_numeric(vals[c], errors="coerce").to_numpy()
            for cc in ([country_filter] if country_filter else sorted(set(countries.dropna()))):
                mask = (countries == cc).to_numpy()
                v, w = col[mask], weights[mask]
                counts = [float(w[v == k].sum()) for k in opts_codes]
                dk = float(sum(w[v == k].sum() for k in dk_codes))
                tot = sum(counts) + dk
                if tot <= 0 or (sum(counts) / max(w[~np.isnan(v)].sum(), 1e-9)) < 0.3:
                    continue
                answered = (~np.isnan(v)).sum()
                if answered < 100:
                    continue
                opts, dist = list(options), counts
                if dk / tot >= 0.01:
                    opts, dist = options + ["Don't know / not sure"], counts + [dk]
                dist = [x / sum(dist) for x in dist]
                items.append({"source": sid, "ref": c, "country": cc, "year": year, "text": clean_question(labels[c]),
                              "options": opts, "dist": dist, "has_dk": len(opts) > len(options),
                              "ordered": _looks_ordered(options), "n": int(answered)})
    return items


def _looks_ordered(options: list[str]) -> bool:
    t = " ".join(o.lower() for o in options)
    return bool(re.search(r"strongly|somewhat|very|fairly|not at all|a great deal|always|never|often|agree|disagree|"
                          r"satisf|likely|important|approve|better|worse|more|less|good|bad|trust", t)) and len(options) >= 3


def index_questions(sid: str) -> int:
    from ..calibration import add_anchors
    from .. import db
    if sid == "pew_atp":  # every wave, not just the newest
        items = [it for p in files(sid) for it in _items_from_survey(sid, path=p)]
    else:
        items = _items_from_survey(sid)
    db.ex("DELETE FROM anchors WHERE source=?", sid)
    return add_anchors(items)


# ---------- test sets ----------
def testsets() -> list[dict]:
    out = [
        {"id": "globalopinionqa", "name": "GlobalOpinionQA", "kind": "aggregate", "ready": bool(files("globalopinionqa")),
         "description": "Pew Global Attitudes and WVS questions with each country's real answer shares. The population method needs a population of that country."},
        {"id": "simbench", "name": "SimBench", "kind": "aggregate", "ready": bool(files("simbench")),
         "description": "Questions from 20 surveys with real answer shares (only items naming a country are used for the population method)."},
        {"id": "twin2k", "name": "Twin-2K-500 (twins)", "kind": "twins", "ready": bool(files("twin2k")),
         "description": "Twins of 2,058 real people: demographics and some of their own wave 1–3 answers predict their wave 4 answers. Measures individual accuracy too."},
    ]
    for sid, cfg in SURVEYS.items():
        if sid == "ces":
            continue
        out.append({"id": f"survey:{sid}", "name": f"{BY_ID[sid]['name']} (twins of respondents)", "kind": "twins",
                    "ready": bool(files(sid)) and allowed(BY_ID[sid]),
                    "description": "Pew-style test: each simulated person is a twin of a real respondent (demographics and some of their other answers); "
                                   "the real result is the survey's own weighted answer shares."})
    for t in out:
        t["ready"] = t["ready"] and present()
    return out


def _population_people(country: str, n: int, seed: int) -> list[dict]:
    from .. import db
    pop = db.q1("SELECT id FROM populations WHERE country=? ORDER BY (source='demo'), id DESC LIMIT 1", country)
    if not pop:
        return []
    rows = db.q("SELECT id, base_json, weight FROM people WHERE population_id=?", pop["id"])
    rng = random.Random(seed)
    rows = rng.sample(rows, min(n, len(rows)))
    return [{"ref": f"p{r['id']}", "record": json.loads(r["base_json"]), "weight": r["weight"]} for r in rows]


def testset_items(tsid: str, cfg: dict) -> list[dict]:
    n_items, n_people, seed = int(cfg.get("n_items") or 10), int(cfg.get("n_people") or 30), int(cfg.get("seed") or 7)
    want_country = cfg.get("country")
    method = cfg.get("method", "population")
    rng = random.Random(seed)
    if tsid == "globalopinionqa":
        df = pd.read_csv(files("globalopinionqa")[0])
        rows = df.sample(frac=1, random_state=seed)
        items = []
        for _, r in rows.iterrows():
            try:
                sel = ast.literal_eval(re.sub(r"^defaultdict\(<class 'list'>,\s*", "", r["selections"]).rstrip(")"))
                opts = ast.literal_eval(r["options"])
            except (ValueError, SyntaxError):
                continue
            for cname, dist in sel.items():
                a2 = C.to_a2(cname)
                if not a2 or (want_country and a2 != want_country) or len(dist) != len(opts) or len(opts) > 8:
                    continue
                people = _population_people(a2, n_people, seed) if method == "population" else []
                if method == "population" and not people:
                    continue
                items.append({"ref": f"goqa:{hash(r['question']) & 0xffffff}:{a2}", "text": r["question"], "options": [str(o) for o in opts],
                              "real": [float(x) for x in dist], "country": a2, "country_name": C.name(a2), "qtype": "opinion",
                              "people": people, "ordered": _looks_ordered([str(o) for o in opts])})
                break
            if len(items) >= n_items:
                break
        return items
    if tsid == "simbench":
        df = pd.read_csv(files("simbench")[0])
        rows = df.sample(frac=1, random_state=seed)
        items = []
        for i, r in rows.iterrows():
            gp = str(r.get("group_prompt_template", ""))
            m = re.search(r"You are from (?:the )?([A-Z][A-Za-z .'-]+?)[.,]", gp)
            a2 = C.to_a2(m.group(1)) if m else None
            if method == "population" and (not a2 or (want_country and a2 != want_country)):
                continue
            try:
                human = ast.literal_eval(str(r["human_answer"]))
            except (ValueError, SyntaxError):
                continue
            if not isinstance(human, dict) or not 2 <= len(human) <= 8:
                continue
            text = str(r["input_template"])
            letters = sorted(human)
            opts = []
            for L in letters:
                mm = re.search(rf"\(?{L}\)?[.:)]\s*([^\n]+)", text)
                opts.append(mm.group(1).strip() if mm else L)
            q = re.split(r"\n\s*\(?A\)?[.:)]", text)[0].strip()
            people = _population_people(a2, n_people, seed) if method == "population" else []
            if method == "population" and not people:
                continue
            items.append({"ref": f"simbench:{i}", "text": q, "options": opts, "real": [float(human[L]) / 100 for L in letters],
                          "country": a2, "country_name": C.name(a2) if a2 else None, "qtype": "opinion", "people": people})
            if len(items) >= n_items:
                break
        return items
    if tsid == "twin2k":
        return _twin_items(n_items, n_people, seed, method)
    if tsid.startswith("survey:"):
        return _survey_items(tsid.split(":", 1)[1], want_country, n_items, n_people, seed, method)
    raise ValueError("Unknown test set.")


TWIN_DEMO = {"QID11": "region", "QID12": "sex", "QID13": "age", "QID14": "education", "QID15": "race", "QID17": "marital",
             "QID18": "religion", "QID19": "religiosity", "QID20": "party", "QID21": "income", "QID22": "ideology", "QID24": "employment"}
TWIN_AGE = {"18-29": (18, 29), "30-49": (30, 49), "50-64": (50, 64), "65+": (65, 85)}


def _twin_items(n_items: int, n_people: int, seed: int, method: str) -> list[dict]:
    d = files("twin2k")[0].parent
    cat = json.loads((d / "question_catalog.json").read_text())
    cat = cat if isinstance(cat, list) else cat.get("questions", list(cat.values()))
    by_col = {}
    for q in cat:
        for col in (q.get("csv_columns") or [q.get("QuestionID")]):
            by_col[col] = q
    w13 = pd.read_csv(d / "wave1_3_response_label.csv", dtype=str)
    w4 = pd.read_csv(d / "wave4_response_label.csv", dtype=str)
    rng = random.Random(seed)

    def single(q):
        # Qualtrics multiple choice with a single-answer selector (MAVR/MACOL are multi-answer)
        return (q and q.get("QuestionType") == "MC" and not str((q.get("Settings") or {}).get("Selector", "")).startswith("MA")
                and 2 <= len(q.get("Options") or []) <= 8)

    targets = [c for c in w4.columns if c != "pid" and single(by_col.get(c))]
    rng.shuffle(targets)
    view_cols = [c for c in w13.columns if c not in ("pid",) and c not in TWIN_DEMO and single(by_col.get(c))]
    merged = w13.merge(w4[["pid"] + targets], on="pid", suffixes=("", "_w4"))
    items = []
    for tc in targets[: n_items * 2]:
        q = by_col[tc]
        opts = [str(o) for o in q["Options"]]
        col = tc if tc in merged.columns and tc not in w13.columns else f"{tc}_w4"
        if col not in merged.columns:
            continue
        answers = merged[col]
        valid = answers[answers.isin(opts)]
        if len(valid) < 200:
            continue
        real = [float((valid == o).mean()) for o in opts]
        sample = merged[answers.isin(opts)].sample(n=min(n_people, len(valid)), random_state=seed)
        same_text = {c for c in view_cols if by_col[c].get("QuestionText") == q.get("QuestionText")}
        vcols = [c for c in view_cols if c not in same_text]
        random.Random(seed + 1).shuffle(vcols)
        vcols = vcols[:12]
        people, pool = [], []
        for _, r in merged[answers.isin(opts)].iterrows():
            rec = {"country": "US", "country_name": "United States"}
            for qc, f in TWIN_DEMO.items():
                v = r.get(qc)
                if isinstance(v, str) and v:
                    if f == "age":
                        lo, hi = TWIN_AGE.get(v.replace("–", "-"), (None, None))
                        if lo:
                            rec["age"] = rng.randint(lo, hi)
                    elif f == "sex":
                        rec["sex"] = _sex_from_label(v)
                    else:
                        rec[f] = v
            entry = {"ref": f"twin{r['pid']}", "record": rec, "weight": 1.0, "actual": opts.index(r[col]), "pid": r["pid"]}
            pool.append(entry)
        sample_pids = set(sample["pid"])
        for e in pool:
            if e["pid"] in sample_pids:
                row = merged[merged["pid"] == e["pid"]].iloc[0]
                e = dict(e)
                e["record"] = dict(e["record"], views=[{"q": by_col[c]["QuestionText"][:200], "a": row[c]} for c in vcols if isinstance(row[c], str)],
                                   provenance={"kind": "twin", "note": "Twin of a real Twin-2K-500 participant"})
                people.append(e)
        items.append({"ref": f"twin:{tc}", "text": clean_question(q.get("QuestionText", tc)), "options": opts, "real": real,
                      "country": "US", "qtype": "opinion", "people": people, "pool": pool, "ordered": _looks_ordered(opts)})
        if len(items) >= n_items:
            break
    return items


def _survey_items(sid: str, country: str | None, n_items: int, n_people: int, seed: int, method: str) -> list[dict]:
    df, meta, use, wcol, ccol, allcols = survey_frame(sid)
    countries = _country_series(sid, df, meta, ccol)
    if not country:
        country = countries.value_counts().index[0]
    items = _items_from_survey(sid, country)
    rng = random.Random(seed)
    rng.shuffle(items)
    items = items[:n_items]
    out = []
    path = survey_file(sid)
    for it in items:
        target = it["ref"]
        people, _ = _respondents(sid, country, n_people, seed, n_views=10, exclude_vars={target}, with_index=True)
        vl = meta.variable_value_labels[target]
        codes = [k for k, v in vl.items() if not is_missing_label(v) and not DK_RE.search(str(v))]
        dk_codes = [k for k, v in vl.items() if DK_RE.search(str(v))]
        col = pd.to_numeric(read_cols(path, [target])[target], errors="coerce")
        twins = []
        for rec in people:
            v = col.loc[rec.pop("_row")]
            actual = codes.index(v) if v in codes else (len(codes) if it["has_dk"] and v in dk_codes else None)
            twins.append({"ref": rec["provenance"]["ref"], "record": rec, "weight": 1.0, "actual": actual})
        people = twins
        pool = []
        if method == "knn":
            mask = (countries == country).to_numpy()
            sub = df[mask]
            for ix, r in sub.sample(n=min(3000, len(sub)), random_state=seed).iterrows():
                v = col.loc[ix] if ix in col.index else None
                a = codes.index(v) if v in codes else (len(codes) if it["has_dk"] and v in dk_codes else None)
                if a is None:
                    continue
                rec = _person_from_row(sid, r, meta, use, country, random.Random(1))
                pool.append({"record": rec, "actual": a, "ref": f"{sid}:{ix}"})
        out.append({"ref": f"{sid}:{target}:{country}", "anchor_ref": target, "source": sid, "text": it["text"],
                    "options": it["options"], "real": it["dist"], "country": country, "country_name": C.name(country),
                    "qtype": "opinion", "people": people, "pool": pool, "ordered": it["ordered"], "has_dk": it["has_dk"]})
    return out


def knn_predict(item: dict, k: int = 25) -> tuple[list[float], list[tuple[int, int]]]:
    """Non-AI baseline: each test person gets the answer shares of the most similar other respondents."""
    pool = [p for p in item.get("pool") or [] if p.get("actual") is not None]
    test_refs = {p["ref"] for p in item["people"]}
    pool = [p for p in pool if p["ref"] not in test_refs]
    n = len(item["options"])
    if not pool:
        return [1 / n] * n, []
    keyf = lambda r: (age_band(r.get("age")), r.get("sex"), edu3(r.get("education")), r.get("party"), r.get("region"), r.get("race"))
    preds, individual = [], []
    for p in item["people"]:
        pk = keyf(p["record"])
        scored = sorted(pool, key=lambda q: -sum(a == b and a is not None for a, b in zip(pk, keyf(q["record"]))))[:k]
        dist = np.bincount([q["actual"] for q in scored], minlength=n)[:n].astype(float)
        dist /= max(dist.sum(), 1)
        preds.append(dist)
        if p.get("actual") is not None:
            individual.append((p["actual"], int(np.argmax(dist))))
    return np.mean(preds, axis=0).tolist(), individual
