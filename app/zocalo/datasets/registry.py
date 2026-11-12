"""Every data source Zócalo knows: what it is, its licence, how to get it, and whether it's here.

Files are never bundled with Zócalo. "auto" sources are downloaded by the app from the publisher; "manual" sources
need you to accept terms on the publisher's site (an account or a form), then put the file in the folder shown.
Technical details and verification notes: docs/data-sources-tech.md.
"""
from __future__ import annotations

import asyncio
import re
import shutil
import traceback
import zipfile
from pathlib import Path

import httpx
import markdown as md

from .. import db
from ..config import DATASETS_DIR_DEFAULT, IN_DOCKER, VERSION

UA = f"Zocalo/{VERSION} (open-source survey research tool)"
MARKER = ".zocalo-datasets"

SOURCES: list[dict] = [
    # ---------- people ----------
    {"id": "acs_pums", "group": "population", "access": "auto", "name": "US Census ACS PUMS 2024 (1-year)",
     "description": "About 3.4 million anonymised US census records: age, sex, state, education, work, income, race, household.",
     "licence": "Public domain", "noncommercial": False, "size": "575 MB",
     "urls": ["https://www2.census.gov/programs-surveys/acs/data/pums/2024/1-Year/csv_pus.zip"], "extract": False,
     "check": ["csv_pus.zip"]},
    {"id": "uk_census", "group": "population", "access": "auto", "name": "UK Census 2021 teaching sample (England & Wales)",
     "description": "A 1% sample (about 600,000 people): age band, sex, region, work, occupation, ethnicity, religion. No education or income.",
     "licence": "Open Government Licence v3", "noncommercial": False, "size": "37 MB",
     "urls": ["https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/publicmicrodatateachingsampleenglandandwalescensus2021/current/upload-publicmicrodatateachingsample.csv"],
     "filenames": ["uk_census_2021_teaching_sample.csv"], "check": ["uk_census_2021_teaching_sample.csv"]},
    {"id": "ca_pumf", "group": "population", "access": "auto", "name": "Canada 2021 Census PUMF (individuals)",
     "description": "A 2.7% sample of Canadians: age, gender, province, education, household income, work, visible minority, religion.",
     "licence": "Statistics Canada Open Licence", "noncommercial": False, "size": "182 MB",
     "urls": ["https://www150.statcan.gc.ca/n1/pub/98m0001x/2023001/cen21_ind_98m0001x_part_rec21.zip"], "extract": False,
     "check": ["cen21_ind_98m0001x_part_rec21.zip"]},
    # ---------- opinions ----------
    {"id": "ces", "group": "opinion", "access": "auto", "name": "Cooperative Election Study, cumulative 2006–2025",
     "description": "About 720,000 US adults over 20 years: demographics, party, ideology, votes, religion. Attitudes for US people.",
     "licence": "CC0 (no restrictions)", "noncommercial": False, "size": "144 MB",
     "dataverse": {"doi": "doi:10.7910/DVN/II2DB6", "pattern": r"^cumulative_.*\.feather$"}, "check_glob": "cumulative_*.feather"},
    {"id": "gss", "group": "opinion", "access": "auto", "name": "General Social Survey 1972–2024",
     "description": "About 75,000 US interviews and 6,900 questions over 50 years. Attitudes, and a large bank of real questions.",
     "licence": "NORC terms of use (no redistribution)", "noncommercial": False, "size": "48 MB (600 MB unpacked)",
     "urls": ["https://gss.norc.org/content/dam/gss/get-the-data/documents/stata/GSS_stata.zip"], "extract": True,
     "check_glob": "**/gss*.dta", "indexable": True},
    {"id": "afrobarometer", "group": "opinion", "access": "auto", "name": "Afrobarometer Round 10 (38 countries)",
     "description": "About 51,000 people across Africa: demographics, party closeness, religion, lived poverty, and hundreds of questions.",
     "licence": "Free with attribution", "noncommercial": False, "size": "13 MB",
     "scrape": {"page": "https://www.afrobarometer.org/data/merged-data/", "pattern": r"https://[^\"']+R10[^\"']*Merge[^\"']*release\.sav\.zip"},
     "extract": True, "check_glob": "**/*R10*.sav", "indexable": True},
    {"id": "latinobarometro", "group": "opinion", "access": "auto", "name": "Latinobarómetro 2024 (17 countries)",
     "description": "About 19,000 people across Latin America: demographics, ideology, party, religion, and the full questionnaire.",
     "licence": "Non-commercial research; no redistribution", "noncommercial": True, "size": "6 MB",
     "scrape": {"page": "https://www.latinobarometro.org/latinobarometro-2024", "pattern": r"(?:https://www\.latinobarometro\.org)?/?documents/LAT-2024/latinobarometro-2024-spss-v\d+\.zip",
                "base": "https://www.latinobarometro.org/"},
     "extract": True, "check_glob": "**/*Spss_eng*.sav", "indexable": True},
    {"id": "wvs", "group": "opinion", "access": "manual", "name": "World Values Survey Wave 7 (66 countries)",
     "description": "About 97,000 people in 66 countries: values, trust, religion, politics. Builds people for most of the world.",
     "licence": "Non-profit use; no redistribution", "noncommercial": True, "size": "about 100 MB",
     "folder": "wvs", "check_glob": "**/*.sav", "indexable": True,
     "instructions": """1. Open <https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp>.
2. Under the data files, click **WVS Cross-National Wave 7 spss v6 0.zip** (or the newest version).
3. Fill in the short form (name, institution, intended use) and accept the conditions of use.
4. Unzip the download and put the `.sav` file in the folder **{folder}**.
5. Come back to this page: it shows *ready* when the file is found."""},
    {"id": "ess", "group": "opinion", "access": "manual", "name": "European Social Survey Round 11 (31 countries)",
     "description": "About 50,000 Europeans: politics, trust, religion, wellbeing, immigration. Builds people for Europe.",
     "licence": "CC BY-NC-SA 4.0", "noncommercial": True, "size": "about 40 MB",
     "folder": "ess", "check_glob": "**/*.sav", "indexable": True,
     "instructions": """1. Open the ESS Data Portal: <https://ess.sikt.no/en/datafile/242aaa39-3bbb-40f5-98bf-bfb1ce53d8ef> and sign in (free account).
2. Download the **ESS11 integrated file** in **SPSS** format.
3. Unzip it and put the `.sav` file (named like `ESS11e04_2.sav`) in the folder **{folder}**."""},
    {"id": "arab_barometer", "group": "opinion", "access": "manual", "name": "Arab Barometer Wave IX (9 countries)",
     "description": "People in Egypt, Iraq, Jordan, Lebanon, Mauritania, Morocco, Palestine, Syria and Tunisia (2025–26).",
     "licence": "Free; non-commercial use with citation", "noncommercial": True, "size": "9 MB",
     "folder": "arab_barometer", "check_glob": "**/*.sav", "indexable": True,
     "instructions": """1. Open <https://www.arabbarometer.org/survey-data/data-downloads/>.
2. Click **Arab Barometer Wave IX: Data Sets**, fill in the short form and download.
3. Unzip it and put the English `.sav` file in the folder **{folder}**."""},
    {"id": "pew_atp", "group": "opinion", "access": "manual", "name": "Pew Research Center American Trends Panel",
     "description": "Waves of about 5,000–10,000 US adults on politics, technology, religion and more. The best test material, wave by wave.",
     "licence": "Pew terms: no redistribution of the data in full", "noncommercial": False, "size": "5–20 MB per wave",
     "folder": "pew", "check_glob": "**/*.sav", "indexable": True,
     "instructions": """1. Create a free account at <https://www.pewresearch.org/datasets/> (“My Account”).
2. Open a wave page, for example <https://www.pewresearch.org/dataset/american-trends-panel-wave-169/>, accept the terms and download it.
3. Unzip it and put the `ATP W{{N}}.sav` file in the folder **{folder}**. Add as many waves as you like.
4. For tests, the most useful waves are the newest ones (fielded after your models' training cut-off). As of late 2026 the newest public waves are W161–W169 (Jan–May 2025)."""},
    # ---------- tests ----------
    {"id": "twin2k", "group": "testset", "access": "auto", "name": "Twin-2K-500",
     "description": "2,058 US adults who each answered about 500 questions in four waves. Tests twins of real individuals.",
     "licence": "CC BY 4.0", "noncommercial": False, "size": "27 MB",
     "urls": [f"https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500/resolve/main/question_catalog_and_human_response_csv/{f}"
              for f in ["question_catalog.json", "wave1_3_response_label.csv", "wave4_response_label.csv"]],
     "check": ["question_catalog.json", "wave1_3_response_label.csv", "wave4_response_label.csv"]},
    {"id": "globalopinionqa", "group": "testset", "access": "auto", "name": "GlobalOpinionQA",
     "description": "2,556 Pew Global Attitudes and WVS questions with each country's real answer shares.",
     "licence": "CC BY-NC-SA 4.0", "noncommercial": True, "size": "5 MB",
     "urls": ["https://huggingface.co/datasets/Anthropic/llm_global_opinions/resolve/main/data/global_opinions.csv"],
     "check": ["global_opinions.csv"]},
    {"id": "simbench", "group": "testset", "access": "auto", "name": "SimBench",
     "description": "About 7,000 questions from 20 surveys and experiments, with real answer shares.",
     "licence": "CC BY-NC-SA 4.0", "noncommercial": True, "size": "4 MB",
     "urls": ["https://huggingface.co/datasets/pitehu/SimBench/resolve/main/SimBenchPop.csv"], "check": ["SimBenchPop.csv"]},
]
BY_ID = {s["id"]: s for s in SOURCES}
_tasks: dict[str, asyncio.Task] = {}


def datasets_dir() -> Path:
    custom = None if IN_DOCKER else db.get_setting("datasets_dir")
    return Path(custom).expanduser() if custom else DATASETS_DIR_DEFAULT


def present() -> bool:
    """The folder exists and is the one we used before. An empty mount point (drive unplugged) has no marker."""
    d = datasets_dir()
    if not d.is_dir():
        return False
    used_before = db.q1("SELECT 1 AS x FROM downloads WHERE status='ready' LIMIT 1") is not None
    return (d / MARKER).exists() or not used_before


def source_dir(sid: str) -> Path:
    s = BY_ID[sid]
    return datasets_dir() / s.get("folder", sid)


def files(sid: str) -> list[Path]:
    s, d = BY_ID[sid], source_dir(sid)
    if not d.is_dir():
        return []
    if "check" in s:
        fs = [d / f for f in s["check"]]
        return fs if all(f.exists() for f in fs) else []
    return sorted(d.glob(s["check_glob"]))


def source_status(sid: str) -> dict:
    row = db.q1("SELECT * FROM downloads WHERE source_id=?", sid) or {}
    if not present():
        return {"status": "missing", "message": "dataset folder not available", "progress": 0}
    if row.get("status") in ("downloading", "indexing") and sid in _tasks and not _tasks[sid].done():
        return {"status": row["status"], "progress": row.get("progress", 0), "message": row.get("message")}
    fs = files(sid)
    if fs:
        return {"status": "ready", "progress": 1, "message": row.get("message") if row.get("status") == "ready" else None,
                "files": [f.name for f in fs]}
    if row.get("status") == "error":
        return {"status": "error", "progress": 0, "message": row.get("message")}
    return {"status": "not downloaded", "progress": 0, "message": None}


def _set(sid: str, status: str, progress: float = 0, message: str | None = None) -> None:
    db.ex("INSERT INTO downloads(source_id,status,progress,message,updated_at) VALUES(?,?,?,?,?) "
          "ON CONFLICT(source_id) DO UPDATE SET status=excluded.status, progress=excluded.progress, "
          "message=excluded.message, updated_at=excluded.updated_at", sid, status, progress, message, db.now())


def allowed(s: dict) -> bool:
    return not s["noncommercial"] or bool(db.get_setting("allow_noncommercial", True))


def overview(lang: str = "en") -> dict:
    out = []
    indexed = {r["source"] for r in db.q("SELECT DISTINCT source FROM anchors")}
    for s in SOURCES:
        st = source_status(s["id"])
        item = {k: s[k] for k in ["id", "group", "access", "name", "description", "licence", "noncommercial", "size"]}
        item.update(st, indexable=bool(s.get("indexable")), indexed=s["id"] in indexed, allowed=allowed(s),
                    folder=str(source_dir(s["id"])))
        if s.get("instructions"):
            item["instructions_html"] = md.markdown(s["instructions"].format(folder=str(source_dir(s["id"])))
                                                    + "\n\nOr press **upload file** on this page and choose the downloaded `.zip` or `.sav`.")
        out.append(item)
    return {"sources": out, "path": str(datasets_dir()), "present": present()}


def population_sources() -> list[dict]:
    from .loaders import POPULATION_SOURCES, countries_for
    out = []
    for sid, info in POPULATION_SOURCES.items():
        s = BY_ID[sid]
        ready = bool(files(sid)) and present() and allowed(s)
        out.append({"id": sid, "name": info["name"], "kind": "real", "ready": ready, "note": info["note"],
                    "countries": countries_for(sid) if ready else []})
    return out


# ---------- downloading ----------
async def _stream(client: httpx.AsyncClient, url: str, dest: Path, sid: str, part: tuple[int, int]) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    async with client.stream("GET", url) as r:
        if r.status_code >= 400:
            raise RuntimeError(f"{url} returned {r.status_code}")
        total = int(r.headers.get("content-length") or 0)
        done = 0
        with open(tmp, "wb") as f:
            async for chunk in r.aiter_bytes(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    _set(sid, "downloading", (part[0] + done / total) / part[1], f"{done >> 20} of {total >> 20} MB")
    tmp.replace(dest)


async def _resolve_urls(client: httpx.AsyncClient, s: dict) -> list[tuple[str, str]]:
    if "dataverse" in s:
        dv = s["dataverse"]
        r = await client.get("https://dataverse.harvard.edu/api/datasets/:persistentId/", params={"persistentId": dv["doi"]})
        r.raise_for_status()
        fs = r.json()["data"]["latestVersion"]["files"]
        match = [f["dataFile"] for f in fs if re.match(dv["pattern"], f["dataFile"]["filename"])]
        if not match:
            raise RuntimeError("The data file wasn't found in the Dataverse listing.")
        return [(f"https://dataverse.harvard.edu/api/access/datafile/{match[0]['id']}", match[0]["filename"])]
    if "scrape" in s:
        sc = s["scrape"]
        r = await client.get(sc["page"])
        r.raise_for_status()
        found = re.findall(sc["pattern"], r.text)
        if not found:
            raise RuntimeError("The download link wasn't found on the publisher's page; it may have moved. Download it by hand.")
        url = found[0]
        if not url.startswith("http"):
            url = sc.get("base", "") + url.lstrip("/")
        return [(url, url.rsplit("/", 1)[-1])]
    names = s.get("filenames") or [u.rsplit("/", 1)[-1].split("?")[0] for u in s["urls"]]
    return list(zip(s["urls"], names))


async def _download(sid: str) -> None:
    s = BY_ID[sid]
    d = source_dir(sid)
    try:
        d.mkdir(parents=True, exist_ok=True)
        (datasets_dir() / MARKER).touch(exist_ok=True)
        _set(sid, "downloading", 0, "starting")
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=20), follow_redirects=True,
                                     headers={"User-Agent": UA}) as client:
            targets = await _resolve_urls(client, s)
            for i, (url, name) in enumerate(targets):
                await _stream(client, url, d / name, sid, (i, len(targets)))
                if s.get("extract") and name.endswith(".zip"):
                    _set(sid, "downloading", (i + 1) / len(targets), "unpacking")
                    await asyncio.to_thread(_unzip, d / name, d)
        _set(sid, "ready", 1, None)
    except Exception as e:
        traceback.print_exc()
        _set(sid, "error", 0, str(e)[:300])


def _unzip(path: Path, dest: Path) -> None:
    with zipfile.ZipFile(path) as z:
        for m in z.infolist():
            if m.is_dir() or ".." in m.filename or m.filename.startswith("/") or "__MACOSX" in m.filename:
                continue
            target = dest / m.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    path.unlink()


def start_download(sid: str, options: dict | None = None) -> None:
    if sid not in BY_ID:
        raise ValueError("Unknown source.")
    s = BY_ID[sid]
    if s["access"] != "auto":
        raise ValueError("This source must be downloaded by hand; see its instructions.")
    first_time = db.q1("SELECT 1 AS x FROM downloads WHERE status='ready' LIMIT 1") is None
    if first_time and not datasets_dir().exists():
        datasets_dir().mkdir(parents=True, exist_ok=True)
    if not present():
        raise ValueError("The dataset folder isn't available (drive unplugged?).")
    if not allowed(s):
        raise ValueError("Non-commercial data is switched off in Settings.")
    if sid in _tasks and not _tasks[sid].done():
        return
    _tasks[sid] = asyncio.get_event_loop().create_task(_download(sid))


UPLOAD_TYPES = (".sav", ".dta", ".zip", ".csv")


def save_upload(sid: str, filename: str, fileobj) -> list[str]:
    """Put a hand-downloaded file in the source's folder (unzipping archives). Returns the data files now present."""
    if sid not in BY_ID:
        raise ValueError("Unknown source.")
    name = Path(filename or "").name
    if not name.lower().endswith(UPLOAD_TYPES):
        raise ValueError("Upload the .sav, .dta or .zip file you downloaded.")
    first_time = db.q1("SELECT 1 AS x FROM downloads WHERE status='ready' LIMIT 1") is None
    if first_time and not datasets_dir().exists():
        datasets_dir().mkdir(parents=True, exist_ok=True)
    if not present():
        raise ValueError("The dataset folder isn't available (drive unplugged?).")
    d = source_dir(sid)
    d.mkdir(parents=True, exist_ok=True)
    (datasets_dir() / MARKER).touch(exist_ok=True)
    dest = d / name
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "wb") as out:
        shutil.copyfileobj(fileobj, out, 1 << 20)
    tmp.replace(dest)
    if name.lower().endswith(".zip"):
        _unzip(dest, d)
    found = [f.name for f in files(sid)]
    _set(sid, "ready" if found else "error", 1 if found else 0,
         None if found else "The upload didn't contain a file this source can use.")
    return found


def start_indexing(sid: str) -> None:
    from .loaders import index_questions
    if not files(sid):
        raise ValueError("Download it first.")

    async def work():
        try:
            _set(sid, "indexing", 0.1, "reading questions")
            n = await asyncio.to_thread(index_questions, sid)
            _set(sid, "ready", 1, f"{n} questions indexed")
        except Exception as e:
            traceback.print_exc()
            _set(sid, "ready", 1, f"indexing failed: {str(e)[:200]}")

    _tasks[sid] = asyncio.get_event_loop().create_task(work())
