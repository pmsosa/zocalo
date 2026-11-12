"""Building populations in the background, from the demo generator or from downloaded microdata."""
from __future__ import annotations

import asyncio
import traceback

from .. import db
from . import demo, save_population

_jobs: dict[str, dict] = {}


def available_sources() -> list[dict]:
    """Every way to build a population right now, with the countries each one covers."""
    from ..datasets import population_sources
    out = [{"id": "demo", "name": "Demo (made-up people)", "kind": "demo", "countries":
            [{"code": k, "name": v["name"]} for k, v in demo.COUNTRIES.items()], "ready": True}]
    out.extend(population_sources())
    return out


def _build_sync(source: str, country: str, n: int, seed: int, options: dict) -> tuple[list[dict], dict]:
    if source == "demo":
        return demo.build(country, n, seed), {"note": "demo"}
    from ..datasets import build_population
    return build_population(source, country, n, seed, options)


async def start(name: str, source: str, country: str, n: int, seed: int, options: dict | None = None) -> str:
    job_id = f"pop-{source}-{country}-{int(db.now())}"
    _jobs[job_id] = {"status": "running", "message": "Reading records…", "population_id": None}

    async def work():
        try:
            records, meta = await asyncio.to_thread(_build_sync, source, country, n, seed, options or {})
            if not records:
                raise ValueError("No people matched. Check the country and the dataset.")
            pid = await asyncio.to_thread(save_population, name, country, source, records, seed, meta)
            _jobs[job_id].update(status="done", message=f"{len(records)} people", population_id=pid)
        except Exception as e:  # shown to the user on the Populations page
            traceback.print_exc()
            _jobs[job_id].update(status="error", message=str(e)[:400])

    asyncio.get_event_loop().create_task(work())
    return job_id


def job(job_id: str) -> dict | None:
    return _jobs.get(job_id)
