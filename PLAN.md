# Zócalo — plan

Status: planning (2026-11-11). Evidence behind the decisions is in
[`docs/research.md`](docs/research.md).

## Goal
An open-source tool that simulates survey respondents with language models. It covers surveys, A/B tests, persistent
panels, and digital twins you can interview, put in a focus group or set to debate.

It is built to be **honest**: a quick, cheap read of direction, with its likely error measured and shown. It is not a
replacement for surveying real people.

**The bar to beat.** Pew's Sep 2026 "silicon samples" study built a twin of each real panelist (real profile, 71 real
attitudes, Claude Opus 4.6) and still averaged **12.4 points** off, with 28% of questions more than 15 points off.
Every independent evaluation found lands at roughly 10–20 points. Vendors' headline scores use metrics where random
guessing already scores well. Our job is to beat the baselines and say plainly how far off we are, question by
question.

## Principles
- **Tests before features.** Nothing ships without a score on questions the model can't already know.
- **The crowd is the product, not the person.** Realism comes from who is in the population and from calibration.
- **Reproducible.** Every answer records the exact person version, prompt, model version, settings and seed, and can
  be rerun.
- **Pin model versions.** Results have drifted within 3 months in published studies. A model change is a new
  version of every result.
- **Every result shows its error** (see "Showing error" below). There is never a bare number.
- **No significance tests on raw simulated data.** Simulated answers vary far less than real ones, so p-values would
  be wrong. Significance is reported only with a real human sample (Calibration, step 3).
- **Free data first.** Paid data only if testing shows it is needed.
- **No datasets in the repo.** Download scripts only; each user accepts each source's terms themselves.

## Decisions (confirmed 2026-11-11)

**Product**
- Apache-2.0. Open source, for anyone to deploy anywhere: docs and code never assume one particular machine or lab.
  Non-commercial data sources are on by default, and a setting switches them off for commercial use.
- Our own core. EDSL and TinyTroupe are sources of ideas and comparison baselines, not dependencies.
- Python with FastAPI and plain HTML/JS, in Docker. Light theme by default, plus a dark theme. English and Spanish,
  switchable any time in Settings. Installable as a PWA.
- **International from v1**, not US-only (see Data).
- v1 scope: Phases 0–4 and 6. Phase 5 (fine-tuning) is out. Phase 7 gets the import format and maths, but no paid
  panel.
- All app features in v1: the population explorer, surveys, A/B tests, information treatments, persistent panels,
  twin chat, focus groups and debates, the tests and scoreboard page, the Methodology page, Settings, the Usage page,
  CSV export. Customer-list upload comes later.

**Models (Settings → Models)**
- A form to add a provider: Gemini, Anthropic, OpenAI, LiteLLM (any OpenAI-compatible endpoint, which also covers
  Ollama), and others.
- Paste a key: it's checked at once (valid or not), the provider's models are listed, and you pick from a dropdown.
- Add as many providers as you like. They show in a list with their health and can be removed any time. Keys are
  stored encrypted, never shown again in full, and never logged.
- Each study picks how many and which models to use, with a cost estimate before running.
- Model quality matters a lot (Pew: 11.4 points with Opus, 17.4 with a small model). The UI says so when a cheap
  model is picked, and the scoreboard shows the difference.

**Money**
- Spending guard in Settings: unlimited by default, with an optional monthly cap and an optional per-run
  confirmation threshold.
- A **Usage** page shows spending per study, per model and per month.
- Panel size: no hard limit. Above 10,000 people a warning says it may cost a lot, with the estimate.

**Data**
- The dataset folder is a setting. By default it's a local `./datasets` folder; it can point anywhere, e.g. an
  external drive. If the folder is missing (drive unplugged), the app says so plainly and doesn't re-download
  anything elsewhere.
- Manual-download sources (Pew, WVS and others) have their own page in the docs and in the app: what to download,
  from where, and which folder to put it in. The app checks what's present.

**Deploy and access**
- One script: `deploy.sh` with `--port` (default 8730), `--data-dir`, `--datasets-dir` and `--personal-no-pass`.
- `--personal-no-pass` runs without any login, for one person on their own machine. A closable banner says it's
  running with no authentication and that a login can be turned on in Settings.
- With authentication: user accounts with passwords, the first account is the admin, and the admin invites others.

**Process**
- A private GitHub repo `zocalo`, committing as the work goes.
- At the end of the build, a UX specialist agent reviews the phone experience and its feedback gets applied.
- The README is written last and follows Vizsla's structure (see `docs/readme-structure.md`).

## Architecture

### The person
- **Base record:** immutable. Demographics from a real anonymised Census record, attitudes matched from real
  opinion-survey records (GSS, CES, Pew).
- **The model never invents facts or attitudes.** LLM-written backstories measurably skew answers left; one study
  ended up simulating a Democratic sweep of every state. Background prose may only paraphrase real fields.
- **Branches:** changes layered on top of the base (a trait tweak, "saw the news", a side interview). A branch never
  edits the base. Panels stay clean, and counterfactuals ("same people, double the income") come almost free.
- **Two modes:** stateless for surveys (no leakage between questions, flat cost) and stateful for interviews, focus
  groups and debates. Stateful history is summarised as it grows.
- **Drift control:** personas slide back to the model's default within about 8 turns. In stateful mode the core
  traits are restated every turn, and anchor questions are re-asked (e.g. turns 1, 10, 50) to measure drift.

### Answering
- **Default: each person states their own probability spread over the options** (e.g. 60% yes, 30% no, 10% not
  sure). The result is the average of those spreads. Three or four studies agree this beats a single reply, repeated
  sampling and raw token probabilities, cutting error by roughly 35–50%.
- Token probabilities only for open models, and only after calibration against a benchmark.
- 1–5 scales and purchase intent: the person answers in words, which are matched to the scale by meaning (semantic
  similarity rating).
- Option order is randomised every time. "Not sure" is always offered; real people chose it 4× more often than
  simulated ones in Pew's study.
- Temperature is treated as a nuisance setting, not a way to add variety. The evidence says it doesn't fix
  collapse onto one answer.

### Studies
- Typed questions with checked answers (multiple choice, scale, numeric, free text) and blanks filled per run
  (`{{price}}`).
- Runs are a grid of questions × people × models, cached, with results as one queryable table.
- A/B tests use matched halves of one panel.
- **Information treatments** (e.g. "would you buy Y for $X" after news):
  - Between-group by default: branch the people, show news, placebo or nothing, ask once.
  - Always include a placebo arm (irrelevant news, e.g. "the CEO adopted a puppy") and a no-news re-ask.
  - Report treatment minus placebo, never the raw change.
  - Optional same-person mode, always run next to the between-group version; the gap measures the "you're hinting
    I should change" effect.
  - Test prompts that do and don't tell the model it's in an experiment.
  - Models get the direction mostly right but exaggerate effect sizes, and react to things people ignore.
- **Consumer questions** (willingness to pay, price, purchase intent):
  - Labelled "directional" unless calibrated with real people.
  - Every demand curve is checked automatically (price up should mean demand down). Models sometimes get the sign
    wrong, and set prices too high in 81% of cases in one study.
  - Willingness-to-pay estimates come with a human calibration sample, or are labelled uncalibrated.
- **Focus groups and debates:**
  - Each side has a stance pinned in its profile and an instruction to hold it.
  - Simulated groups reach full agreement 85–96% of the time, against 51% for real people. Every discussion result
    is compared with a branch of the same people that didn't discuss.
  - "Stubbornness" settings are an experiment, validated before use.
  - A group's consensus is never presented as a forecast.

### Calibration
1. **Weighting** to the real population: basic hygiene, not a fix. Pew weighted and was still 12 points off.
2. **Anchoring** to the nearest real poll questions: an **experiment**. Nobody has tested it; we measure whether it
   helps and how fast the help fades as questions get less similar.
3. **Human-sample correction** (optional, central for consumer use): a small real sample corrects the simulated
   results (prediction-powered inference). About 10% human data fixed demand estimates in one study. This is also
   the only route to valid significance tests and honest confidence intervals.

### Showing error
Every number the app shows carries its error, labelled with which kind it is:
- **Per-question error (preferred):** estimated for this question from the tests, by question type (knowledge,
  opinion, behaviour or consumer; topical or evergreen), how close the nearest real data is, and subgroup size.
  Shown as the typical and the 80th-percentile error, e.g. "usually within ±6 pts, 1 in 5 times more than ±14".
- **Flat error (fallback):** when the question doesn't match a tested type well enough, a clearly labelled overall
  ±error from all tests. It is never presented as if it were question-specific.
- **Human-calibrated interval:** when a real sample exists, a proper confidence interval, labelled as such.
- **Not a sampling margin of error.** The textbook ±MOE for N simulated people is never shown as the error; adding
  more simulated people doesn't reduce the model's bias.
- Ranges are checked on survey waves released later than the test data (a time split, not a random split), and the
  measured coverage ("these ranges held 78% of the time") is published.
- Subgroup results show their own, larger error. Awareness and knowledge questions ("have you heard of…") carry a
  warning; models score 40+ points too high on them.

## Methodology
A plain-language explanation of how Zócalo works, which commercial tools in this space rarely publish. It is a
living document, not a release chore.
- **One source, two places:** `docs/METHODOLOGY.md` in the repo, shown as a **Methodology** page in the app.
- **Started in Phase 0 and updated by every phase.** A change to how people are built, how they answer, how results
  are calibrated or how error is shown isn't done until the methodology says so.
- **Contents:**
  - How people are built: data sources, how attitudes are matched, what the model may and may not invent.
  - How they answer: stated probability spreads, option order, "not sure", word-to-scale matching.
  - Studies: A/B tests, information treatments with placebo arms, focus groups and debates, and their limits.
  - Calibration: weighting, anchoring to real polls, human-sample correction.
  - How error is estimated and shown: per-question, flat and human-calibrated, and how often the ranges held.
  - Test results: the scoreboard, baselines, and comparison with Pew's silicon-samples study.
  - Known failure modes and what we do about each.
  - What we don't know yet: the open experiments, and results where none exist.
  - Data sources and licences, and the models and versions in use.
- **Every result links to it.** A "How was this made?" card on each study names the model and version, the person
  fields used, the answering method, the calibration anchors and the kind of error shown, each linked to its
  section of the methodology.
- **Written for a non-expert first**, with technical detail and references to `docs/research.md` below.

## Data

| Tier | Sources | Used for |
|---|---|---|
| Automatic download | ACS PUMS, Census CPS, CES/CCES (CC0), GSS, BLS consumer spending (CE PUMD), UK Census teaching sample, Canada PUMF, Twin-2K-500 (CC BY), GlobalOpinionQA, SimBench | People, attitudes, spending, tests |
| User logs in, scripts do the rest | IPUMS (own API key) | Harmonised historic and US data |
| Manual download, with instructions | Pew ATP and Global Attitudes, WVS, ESS, Arab Barometer, Afrobarometer, ANES | Richest question bank; global coverage |
| Paid, only if needed | Gallup World Poll (~$35k/yr), GWI, Statista; Prolific or similar for real human samples | Human samples are optional |
| Off limits | Roper Center, YouGov, Statista (for AI use), ICPSR-restricted, Add Health | Their terms ban AI use |

Licence rules:
- A source registry records each licence. One setting switches off the non-commercial sources for anyone using the
  tool commercially.
- Published outputs (scores, calibration settings, fine-tuned weights) inherit their sources' terms, e.g. NC-SA from
  ESS, GlobalOpinionQA and SimBench. Keep them separated by source.
- Fine-tuning uses clearly licensed data only (CES, Twin-2K-500) until Pew and NORC confirm otherwise.
- Hosted models get a person's profile, never whole datasets, and run with no-retention settings where offered.
- BLS needs a User-Agent with contact details: use a project address, never the user's personal email.

## Phases

**0. Foundations**
- Repo, README with banner, licence, favicon once there's a UI.
- Source registry and download scripts in the three tiers.
- Model layer (hosted and Ollama) that pins versions, records every call and can replay it.
- `docs/METHODOLOGY.md` started, with an outline matching the Methodology section above.

**1. Testing harness**
- Test sets: Twin-2K-500 (individual twins), SubPOP and SimBench (group spreads), and Pew waves released after each
  model's training cutoff.
- Baselines:
  - "aggregate guess" with no persona
  - demographics only
  - closest past poll
  - **a plain statistical model with no AI** (one 2026 study found no model beat the best non-AI baseline at
    predicting individuals)
  - plain EDSL with the same personas, a TinyTroupe focus group
- Metrics, Pew-style so results compare:
  - error per question, share of questions more than 15 points off
  - options nobody chose, real vs simulated spread
  - error by subgroup, wording and repeated runs
- Canaries:
  - awareness questions
  - stereotype checks (Pew: 97% simulated vs 43% real on one subgroup question)
  - the puppy placebo
  - leading wording
- Error tables by question type, for "Showing error". Publish a scoreboard across models.

**2. Population**
- US people from ACS records, keeping real combinations of traits together. Attitudes matched from GSS, CES and Pew.
  Measure how much error the matching adds; nothing published tests that.
- International in v1: UK and Canada from their open census samples. Elsewhere, people come from the opinion surveys'
  own respondents (WVS, ESS, the Barometers), since each one is a real person with demographics and attitudes, then
  weighted to the country. Each country's methodology section says which source and how good it is. All strong
  evidence so far is US-only, so non-US results carry larger, clearly labelled error until tested.

**3. Answering**
- Per-person probability spreads, word-to-scale matching for scales, randomised order, "not sure".
- Background styles compared in tests: traits only, real attitudes, paraphrased real-data background.

**4. Calibration and error**
- Weighting, the anchoring experiment, human-sample correction.
- Per-question and flat error, coverage checks on later waves.

**5. Fine-tuning (high value)**
- Fine-tuning on real answer spreads is the most consistently supported improvement (32–46% less error on group
  results in SubPOP).
- Start from SubPOP's code, on a rented GPU, with licensed data only.
- Compare base and instruction-tuned models (instruction-tuned ones were worse in every family tested). Test on
  survey sources held back from training.

**6. The app**
- Surveys, A/B tests, information treatments, persistent panels, twins, interviews, focus groups, debates.
- Every result shows its labelled error, anchors and warnings, and a "How was this made?" card. Export.
- Methodology page, rendered from `docs/METHODOLOGY.md`.
- README with screenshots from a demo with made-up data.

**7. Checking against real people**
- Import a real panel (e.g. Prolific, paid) to feed the human-sample correction and to measure the error for a
  user's own kind of question.
- Uploaded customer data stays local and is never used for training without opt-in.

**8. Release**
- Methodology reviewed end to end and checked against the code, tests anyone can rerun, the scoreboard, measured
  error coverage.

## Experiments (no published evidence; our tests decide)
- Anchoring to the nearest real poll.
- Multi-model mixing vs the best single model. Pew found GPT-5.1 too extreme and Opus too moderate, which is
  promising for a mix.
- Error added by statistically matched attitudes vs real per-person attitudes.
- Same-person vs between-group demand effects; whether the placebo shift predicts how inflated a real effect is.
- Branching vs long-running state for twin fidelity.
- Stubbornness settings for debates.
- Consumer accuracy beyond single product categories, and how much human data calibration needs.
- Stability across model versions over months.
- Non-US populations.

## Open decisions
- The logo: variations of the speech-square mark, with a dark-theme version and a simpler small-size version.
