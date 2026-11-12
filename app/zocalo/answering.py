"""How a simulated person answers one question.

Default method ("spread"): the person states their own probability for every option, as JSON. Several studies
found this beats a single sampled reply, repeated sampling and raw token probabilities (Jang et al. 2026, Meister
et al. 2024, Prolific 2026; see docs/research.md). Rules applied to every call:
  * option order is shuffled per person (unordered lists) or flipped at random (ordered scales);
  * "Not sure" is always offered, last;
  * the profile holds facts only, and the model is told not to invent any;
  * the person's name is not sent (names push models toward stereotypes).
Alternative method ("words"): the person answers in their own words, and a separate neutral call maps those words
onto the options (used for scales and purchase intent; see METHODOLOGY.md).
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field

from . import providers
from .population import profile_text

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
UNSURE = {"en": "Not sure", "es": "No estoy seguro/a"}

SYSTEM = """You are taking part in a survey as one specific person, described by the facts below.
Answer the way THIS person most plausibly would: their age, place, work, beliefs and circumstances matter.
Real people disagree, hesitate and are often unsure, and people like this one often answer differently from
each other. Do not give the answer an expert, an AI assistant or a well-informed person would give unless this
person would. Be neither more positive nor more negative, more polite nor more agreeable than they would be.
If they would not know something, say so through your answer. Give the reason in their own words, not a stock
phrase.
Use only the facts given. Do not invent other facts about them.

THE PERSON
{profile}"""

SPREAD_INSTRUCTIONS = """{context}Question: {question}
Options:
{options}

How likely is this person to choose each option? Give a probability for every option letter (they sum to 1),
then the single option they would most likely pick, then one short sentence in their own voice explaining it.
Reply with JSON only: {{"probabilities": {{"A": 0.0, ...}}, "answer": "A", "reason": "..."}}"""

WORDS_INSTRUCTIONS = """{context}Question: {question}

Answer as this person would, in one or two sentences, in their own words. Do not pick from a list.
Reply with JSON only: {{"reply": "..."}}"""

JUDGE_SYSTEM = """You map a survey respondent's own words onto answer options. You are neutral and literal:
judge only what the words say, not what you think the person should feel."""

JUDGE_INSTRUCTIONS = """Question: {question}
Respondent said: "{reply}"
Options:
{options}

For each option letter, how well does it match what the respondent said? Give probabilities that sum to 1.
Reply with JSON only: {{"probabilities": {{"A": 0.0, ...}}}}"""


@dataclass
class Asked:
    """One question as asked to one person, with the option order used."""
    text: str
    options: list[str]          # canonical order, "Not sure" last
    order: list[int]            # order[k] = canonical index shown at letter k
    context: str = ""           # news / stimulus shown before the question
    lang: str = "en"


@dataclass
class Answer:
    spread: list[float]         # canonical order
    answer_idx: int
    reason: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    prompt_hash: str = ""
    extra: dict = field(default_factory=dict)


def with_unsure(options: list[str], lang: str = "en") -> list[str]:
    opts = [o.strip() for o in options if o.strip()]
    lowered = {o.lower() for o in opts}
    if not ({"not sure", "don't know", "no estoy seguro/a", "no sé", "unsure"} & lowered):
        opts.append(UNSURE.get(lang, UNSURE["en"]))
    return opts


def option_order(n: int, ordered: bool, seed_parts: tuple, last_fixed: bool = True) -> list[int]:
    """Shuffle the options (keeping a final "Not sure" last); for ordered scales only flip direction."""
    h = int(hashlib.sha256(repr(seed_parts).encode()).hexdigest()[:12], 16)
    rng = random.Random(h)
    m = n - 1 if last_fixed else n
    body = list(range(m))
    if ordered:
        if rng.random() < 0.5:
            body.reverse()
    else:
        rng.shuffle(body)
    return body + ([n - 1] if last_fixed else [])


def _options_block(asked: Asked) -> str:
    return "\n".join(f"{LETTERS[k]}. {asked.options[ci]}" for k, ci in enumerate(asked.order))


def _context_block(asked: Asked, design_informed: bool) -> str:
    if not asked.context:
        return ""
    if design_informed:
        return (f"This survey is an experiment. You were randomly chosen to read the following before answering. "
                f"Treat it the way this person would actually treat it:\n\"{asked.context}\"\n\n")
    return f"Before the question, this person read:\n\"{asked.context}\"\n\n"


def _normalise(probs: dict, asked: Asked) -> list[float]:
    n = len(asked.options)
    spread = [0.0] * n
    for k, ci in enumerate(asked.order):
        v = probs.get(LETTERS[k], probs.get(LETTERS[k].lower(), 0))
        try:
            spread[ci] = max(0.0, float(v))
        except (TypeError, ValueError):
            spread[ci] = 0.0
    total = sum(spread)
    if total <= 0:
        raise ValueError("no probabilities")
    return [s / total for s in spread]


def _letter_to_canon(letter: str, asked: Asked) -> int | None:
    letter = (letter or "").strip().upper()[:1]
    k = LETTERS.find(letter)
    if 0 <= k < len(asked.order):
        return asked.order[k]
    return None


async def ask(model_ref: str, record: dict, asked: Asked, *, method: str = "spread", design_informed: bool = False,
              temperature: float | None = None, history: list[dict] | None = None) -> Answer:
    system = SYSTEM.format(profile=profile_text(record))
    ctx = _context_block(asked, design_informed)
    lang_note = "" if asked.lang == "en" else "\nWrite the reason in Spanish." if asked.lang == "es" else ""
    if method == "words":
        user = WORDS_INSTRUCTIONS.format(context=ctx, question=asked.text) + lang_note
        turns = (history or []) + [{"role": "user", "content": user}]
        comp, m = await providers.complete_ref(model_ref, system, turns, max_tokens=300, temperature=temperature)
        reply = str(providers.parse_json(comp.text).get("reply", "")).strip() or comp.text.strip()
        judge = JUDGE_INSTRUCTIONS.format(question=asked.text, reply=reply.replace('"', "'"), options=_options_block(asked))
        comp2, _ = await providers.complete_ref(model_ref, JUDGE_SYSTEM, judge, max_tokens=200, temperature=0)
        spread = _normalise(providers.parse_json(comp2.text).get("probabilities", {}), asked)
        tin, tout = comp.tokens_in + comp2.tokens_in, comp.tokens_out + comp2.tokens_out
        return Answer(spread, max(range(len(spread)), key=spread.__getitem__), reply, tin, tout,
                      providers.cost_of(m, tin, tout), _hash(system, user), {"method": "words"})
    user = SPREAD_INSTRUCTIONS.format(context=ctx, question=asked.text, options=_options_block(asked)) + lang_note
    turns = (history or []) + [{"role": "user", "content": user}]
    comp, m = await providers.complete_ref(model_ref, system, turns, max_tokens=400, temperature=temperature)
    data = providers.parse_json(comp.text)
    spread = _normalise(data.get("probabilities") or data.get("probs") or {}, asked)
    idx = _letter_to_canon(str(data.get("answer", "")), asked)
    if idx is None:
        idx = max(range(len(spread)), key=spread.__getitem__)
    return Answer(spread, idx, str(data.get("reason", ""))[:400], comp.tokens_in, comp.tokens_out,
                  providers.cost_of(m, comp.tokens_in, comp.tokens_out), _hash(system, user), {"method": "spread"})


def _hash(system: str, user: str) -> str:
    return hashlib.sha256((system + "\n---\n" + user).encode()).hexdigest()[:16]


def estimate_tokens(record: dict, question: str, options: list[str], method: str = "spread") -> tuple[int, int]:
    """Rough token counts for cost estimates: about 4 characters per token."""
    chars = len(SYSTEM) + len(profile_text(record)) + len(SPREAD_INSTRUCTIONS) + len(question) + sum(len(o) + 4 for o in options)
    tin, tout = chars // 4 + 20, 90 + 12 * len(options)
    if method == "words":
        tin, tout = tin * 2, tout + 80
    return tin, tout


def dumps(x) -> str:
    return json.dumps(x, ensure_ascii=False)
