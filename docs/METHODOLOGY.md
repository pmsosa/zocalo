# How Zócalo works

Zócalo asks questions of simulated people, played by language models, and shows the answers together with how far off
they are likely to be. It is a quick, cheap first read of a population's direction. **It is not a replacement for
surveying real people**, and this page says plainly where it falls short.

> **The honest benchmark.** In September 2026 Pew Research Center built a digital twin of each person in its own
> panel, using their real profile, 71 of their real attitudes and a frontier model. On about 300 questions the twins
> were off by **12.4 percentage points** on average, and by more than 15 points on 28% of questions. Every independent
> evaluation we know of lands between about 10 and 20 points. Vendors' headline accuracy numbers usually use
> measures on which random guessing already scores well. Zócalo's job is to beat simple baselines and to say how far
> off it is, question by question.

## The short version

1. **People** are drawn from real census and survey records, in proportion to their official weights.
2. **Each person states a probability for every answer option**, not a single pick. The result is the average of
   those spreads.
3. **Option order is shuffled for every person**, "Not sure" is always offered, and the model sees facts only: no name
   and nothing invented.
4. **Every number carries a labelled error range** taken from measured test results, never a textbook margin of error.
5. **The tests are built in.** You can measure the error yourself on real survey data, and those measurements replace
   the published figures the app starts with.

## 1. Who the people are

A population is a set of person records. Each record is written once and **never changes**. It holds:

- **Demographics** from a real record: age, sex, region, education, work, income band, race or ethnicity, marital
  status, household, religion, where the source has them.
- **Attitudes**, where a source has them: party, ideology, last vote, religiosity, and some of the person's **own past
  survey answers** ("views").
- **Provenance**: which file and which record every fact came from.

### Sources

| Source | What a person is | Where attitudes come from |
|---|---|---|
| US Census ACS PUMS | A real anonymised census record | Matched from a CES (or GSS, or Pew) respondent with the same age band, sex and education level |
| UK Census 2021 teaching sample | A real census record (England & Wales) | Matched from ESS or WVS UK respondents, if downloaded |
| Canada 2021 Census PUMF | A real census record | Matched from WVS Canada respondents, if downloaded |
| CES, GSS, Pew ATP, WVS, ESS, Afrobarometer, Latinobarómetro, Arab Barometer | A real survey respondent | Their own answers |
| Demo | A made-up person from rounded country shares | Made up, and labelled **demo** everywhere |

**Weighting.** People are drawn in proportion to each record's census or survey weight (weighted sampling without
replacement), so a population is self-weighting and needs no further reweighting. If you ask for more people than a
country's survey has respondents, some respondents appear more than once, and the population page says so.

**Age bands.** Some sources only give an age band (UK census, Canada census, Pew). An exact age is then drawn at random
inside the band, and the person's provenance says so. That is the only value Zócalo fills in, and it never leaves
the band.

**Matching attitudes.** A census record has no opinions. Zócalo gives it the party, ideology, religion and past
answers of a real survey respondent who shares its age band, sex and education level. This **adds error of its own**:
two people alike on those three things can still disagree. Nobody has published how much error this matching adds, so
it is one of the things the tests measure.

**What the model may not do.** The model never invents facts or attitudes. Published work found that richer,
model-written backstories push simulated opinion to the left: one study ended up simulating a Democratic sweep of every
state. Zócalo therefore gives the model a list of facts only. **Names are not sent**, because identity-coded names push
models toward stereotypes; names in the app are display labels drawn from per-country lists.

### Branches

Any change to a person (a trait tweak for a "what if", seeing a news story, an interview) is a **branch** layered on
top of the base record. The base never changes, so a panel stays clean from one study to the next, and a person you
interviewed doesn't carry that conversation into their next survey.

## 2. How a person answers

For every question, each person gets one model call. The call contains the person's facts, the question and the
options. **The person states a probability for every option** ("60% yes, 30% no, 10% not sure") and gives a one-line
reason in their own voice.

Why spreads rather than single answers: several studies found that asking a model for one answer per person makes
everyone pick the same option. The spread of answers comes out far too narrow, and options real people choose never
appear. Asking for a probability spread cut that error by roughly 35–50% in three independent studies (Jang et al.
2026; Meister et al. 2024; Prolific 2026). Repeated sampling and raw token probabilities did worse.

Rules applied to every call:

- **Option order is shuffled per person.** For scales ("strongly agree" to "strongly disagree") the order is flipped
  at random instead, so the scale stays in order. Models have strong position and label biases otherwise.
- **"Not sure" is always offered, last.** Real people say "not sure" about four times as often as simulated ones.
- **The prompt asks for this person's answer**: not an expert's, not more positive or more negative, polite or
  agreeable than they would be.
- **Temperature is left at the provider default.** Raising it does not fix answers that are too alike.

**Own-words option.** For scales and purchase intent you can choose *own words → options*: the person answers in a
sentence, and a separate, neutral model call maps those words onto the options as probabilities. This follows the idea
of semantic similarity rating (Maier et al. 2025), which used text embeddings for the mapping. Zócalo uses a judge
call instead, so treat this as an option to test, not an established improvement.

**Several models.** Pick more than one model and every person is asked by each. Results show the models together (each
person's spreads are averaged across models) and separately. Pew found one frontier model shows the public as too
extreme and another as too moderate, so mixing may help. That is untested, so the tests compare a mix against single
models.

## 3. Kinds of study

**Survey.** Everyone answers every question. Questions are asked separately, so no answer sees another.

**A/B test.** The people are split into **matched halves**: sorted into groups by age band, sex, region and education,
shuffled within each group, then dealt out alternately. Half A sees version A of each question (and optionally a text
to read first), half B sees version B. The result is B minus A.

**News test (information treatment).** "Would you buy Y at $X?", after reading a piece of news. The people are split
into **matched thirds**:

- **control:** no news
- **treatment:** the news
- **placebo:** neutral news of similar length

**The effect shown is treatment minus placebo, never the raw change.** Models react to being shown *anything*; the
placebo measures that reaction, so it can be subtracted. Optionally, a **same-person group** also answers, reads the
news, then answers again in the same conversation. That is how people often run these tests by hand, and it
exaggerates effects, because being asked twice signals that the answer should change. The gap between the two designs
shows how much. You can also tell the model it is in an experiment, which reduced over-reaction in one study.

Published evidence: models usually get the **direction** of an effect right but **overstate its size** (Hewitt et al.
2024: r = 0.85 between predicted and real effects, with sizes systematically too large), and they react to changes
people ignore (Tjuatja et al. 2024). Read news-test results as direction, not size.

**Focus groups and debates.** A few people and you, the moderator; or two people with pinned positions. Simulated
groups reach full agreement far more often than real ones (85–96% against 51% in one study). So each debate first asks
every side the question alone (the "no-discussion branch") and again at the end, and shows how far each moved. **Never
read a simulated consensus as a forecast.** Personas also drift back toward the model's default voice in long
conversations, within about 8 turns in one study. Zócalo restates each person's facts on every turn, keeps recent
turns plus a summary, and every 10 turns quietly re-asks one of the person's own recorded answers to check for drift.

## 4. How error is estimated and shown

Every number in Zócalo carries an error range, labelled with **what kind** of estimate it is:

| Label | Meaning |
|---|---|
| **measured in your tests** | The error for this type of question, measured by your own test runs (20+ questions of that type) |
| **estimate from published evaluations** | Until your tests cover a question type, figures from published evaluations |
| **flat estimate** | The question type is "other": the overall error across types, not specific to this question |
| **human-calibrated** | A real 95% confidence interval, because you added a real human sample (section 5) |

It is shown as **"usually within ±a points, 1 in 5 times more than ±b"**: the median and the 80th percentile of the
absolute error per answer option.

**Question types** set the error: *opinion*, *behaviour*, *consumer/price* and *knowledge*, each either evergreen or
about recent news. Zócalo guesses the type from the wording, and you can change it. Starting figures, in percentage
points:

| Type | Typical | 1 in 5 over | Main sources |
|---|---|---|---|
| Opinion | 7 | 15 | Pew 2026; Verasight 2025 (about 4 on common political toplines) |
| Opinion, topical | 10 | 22 | Pew 2026 ("heard a lot about data centers": 3% simulated vs 25% real) |
| Behaviour | 9 | 18 | Pew 2026 |
| Consumer / price | 12 | 25 | Verasight 2025 (19.8 on consumer questions); Harris/AAPOR 2024 |
| Knowledge / awareness | 18 | 40 | Pew 2026 (+43 to +46 on knowledge items) |
| Other (flat) | 12 | 25 | All of the above |

**Adjustments.**

- **Subgroups** get a larger error: ×1.3, plus more for small groups. Simulated subgroups err more than the whole
  (Pew: 16.1 for Republicans and 15.1 for Black adults against 12.4 overall), and the gaps between segments are
  exaggerated 2–4× (Chen et al. 2026).
- **Outside the US**, errors are widened by 25% until tested, because nearly all published evidence is American.
- **Demo populations** carry a warning that they are made up.

**Never a sampling margin of error.** The textbook "±3% for 1,000 people" is not shown anywhere. It measures random
sampling noise, and adding simulated people does nothing about the model's own bias, which is the larger error.

**Do the ranges hold?** Each test run records how often the real error was inside the shown 1-in-5 range. It should be
about 80%. This "ranges held" figure is on the Tests page. It is most meaningful on survey waves released after the
model's training cut-off, because older polls may have been memorised.

**No significance tests on simulated data.** Simulated answers vary far less than real ones (too narrow on 154 of 164
outcomes in one large study), so p-values computed on them would be wrong. Zócalo reports none, except with a human
sample.

## 5. Calibration

1. **Weighting.** Done by drawing people in proportion to their weights (section 1). This is basic hygiene, not a fix:
   Pew weighted its twins and was still 12 points off.
2. **Closest real polls (anchors).** When you download an opinion survey, Zócalo indexes its questions and their real,
   weighted answer shares by country. A new question is matched to its closest real questions by word similarity
   (TF-IDF), and those are shown next to your results. **Anchors are shown, not applied**: whether shifting simulated
   answers toward the nearest real poll helps is unknown, and the *anchor* baseline in the tests measures how well the
   nearest poll alone predicts. The similarity also decides whether a question counts as "close" to real data.
3. **Human-sample correction (prediction-powered inference).** Upload real answers to the same question from a small
   human sample, with demographics if you have them. Each real person is paired with the most similar simulated person.
   The average gap between real and simulated answers corrects the simulated result, and the error bars become a real
   95% confidence interval (Broska et al. 2025; Zhang et al. 2025 found about 10% human data fixed demand estimates).
   This is the only route to statistically valid results. Without it, read results as direction.

## 6. The tests

The Tests page runs the same machinery on questions with known real answers:

| Test set | What it checks |
|---|---|
| **Twins of survey respondents** (Pew, GSS, WVS, ESS, Afrobarometer, Latinobarómetro, Arab Barometer) | Pew-style: each simulated person is a twin of a real respondent (demographics plus some of their *other* answers); the real answer is the survey's own weighted result |
| **Twin-2K-500** | Twins of 2,058 people built from their wave 1–3 answers, predicting their wave 4 answers. Also measures individual accuracy |
| **GlobalOpinionQA** | Pew Global Attitudes and WVS questions, with each country's real shares |
| **SimBench** | Questions from 20 surveys and experiments |

Every test can be run with the real method or a baseline:

| Method | What it is |
|---|---|
| **Simulated people** | Zócalo's method |
| **Ask for the shares** | The model is asked directly for the country's answer shares, with no people |
| **Closest other real poll** | The real answer shares of the most similar *other* question in the index |
| **Every option equal** | A uniform split |
| **Similar real respondents** | No AI: each test person gets the answers of the 25 most similar other respondents (twins tests only) |

The non-AI baseline matters. One 2026 study found that no language model beat the best non-AI baseline at predicting
individuals (Chen et al. 2026). It sees other respondents' real answers to the same question, so its *overall* error
is a ceiling for questions that have already been asked, not a fair rival. Its *individual accuracy* is the fair
comparison. If Zócalo can't beat the uniform and "ask for the shares" baselines on your kind of question, its answers
aren't adding anything. If it can't come near "similar respondents" on individuals, that is expected: so far no
model does.

**First results on this install (November 2026, Gemini 3.1 Flash-Lite, 20 people per question; small samples).**

| Test | Simulated people | Uniform | Closest other poll | Similar respondents (no AI) |
|---|---|---|---|---|
| Latinobarómetro 2024, Mexico, 8 questions | 18.5 pts mean (11.5 median); individual accuracy 59% | 27.1 pts | 9.5 pts (5 questions) | individual accuracy 71% |
| Twin-2K-500, 6 questions | 17.7 pts mean (13.2 median); individual accuracy 36% | — | — | individual accuracy 45% |

These match the published range (about 10–20 points). The starting error ranges held on 62–67% of questions instead of
80%, so they were too optimistic for these sets. Measured values replace them as tests accumulate.

**Second batch (November 2026, 8 questions × 20 people per set, same seed for comparisons).**

| Set | Flash-Lite: simulated people | Flash-Lite: ask for the shares | Gemini 3.6 Flash: simulated people | Uniform |
|---|---|---|---|---|
| Afrobarometer, Kenya | 9.4 | 9.0 | 8.2 | 17.6 |
| Latinobarómetro, Brazil | 12.6 | 9.1 | 8.5 | 19.8 |
| Afrobarometer: Nigeria, South Africa, Ghana | 10.2, 8.9, 12.5 | | | |
| Latinobarómetro: Argentina, Colombia | 16.5, 16.5 | | | |
| GSS (US) | 7.7 | | | |
| Twin-2K-500 | 11.4 | | | |

Mean absolute error per question, in points. What it shows:

- Measured opinion error is now **about ±9.6 typical and ±17.3 at the 80th percentile** (102 questions), wider than the
  published starting figures of ±7 / ±15, and results now use it.
- **With the cheapest model, simulated people did no better than simply asking the model for the country's shares.**
  The stronger model's simulated people did better than both (8.2–8.5). Model quality matters more than method.
- Individual accuracy against the no-AI baseline was mixed: lower in Kenya (43% vs 51%), higher in Brazil
  (61% vs 53%).
- The measured figures pool every model tested. Per-model figures are the next improvement.

**Third batch (November 2026, same design, new sources: ESS Round 11, WVS Wave 7, Arab Barometer Wave IX, Pew ATP W169).**

| Set | Simulated people (3.6 Flash) | Ask for the shares (3.6 Flash) | Similar respondents (no AI) | Closest other poll | Uniform |
|---|---|---|---|---|---|
| ESS, Germany | 5.1 | 3.6 | 1.8 | 28.5 | 33.9 |
| ESS, United Kingdom | 10.6 | 8.1 | 1.6 | 28.6 | 31.1 |
| WVS, Japan | 10.8 | 8.6 | 2.5 | none close | 25.1 |
| WVS, India | 14.6 | 10.1 | 1.8 | none close | 14.6 |
| Arab Barometer, Egypt | 16.9 | 16.0 | 1.5 | 8.0 | 21.5 |
| Arab Barometer, Morocco | 16.8 | 24.2 | 2.2 | 21.5 | 31.8 |
| Pew W169, US | 10.9 | 4.8 | 5.2 | 10.4 | 18.9 |

Smarter models on three of the sets (simulated people):

| Set | 3.6 Flash | 3.8 Flash | 3.1 Pro |
|---|---|---|---|
| ESS, Germany | 5.1 | 4.1 | 4.4 |
| Arab Barometer, Egypt | 16.9 | 16.2 | 14.9 |
| Pew W169, US | 10.9 | 11.6 | 11.5 |
| Cost per set | $0.10–0.13 | $0.11–0.14 | $0.66–0.80 |

Mean absolute error per question, in points. What it shows:

- **Asking the same model for the shares beat simulated people in six of seven sets** (mean 10.8 vs 12.2); simulated
  people only won in Morocco. The second batch compared the stronger model's people against the *cheaper* model's
  shares, which flattered the people. With the same model on both sides, simulated people are not yet adding accuracy
  on whole-population shares. Their value is subgroups, individuals and conversations, which shares can't give.
- **India: simulated people were no better than uniform** (14.6 vs 14.6). Egypt and Morocco were 16–17 points off.
  The 25% widening for countries outside the US is, if anything, too small there.
- **Germany was the best result so far** (5.1, individual accuracy 90%), the UK and US about 11.
- **A smarter model barely helped**: 3.1 Pro was 0–2 points better or slightly worse, at six to seven times the cost,
  and 3.8 Flash was level with 3.6 Flash. Below the Flash tier model quality mattered (second batch); above it, it
  hasn't yet.
- **The closest other poll** was poor in Europe (different questions match badly across surveys) and found nothing
  close for Japan or India, but good in Egypt (8.0), where other Arab Barometer-style questions exist.
- Measured opinion error is now **about ±8.8 typical and ±16.5 at the 80th percentile** (206 questions), and results
  use it. The error ranges held on 63–100% of questions per set (target 80%); they were too narrow for Egypt and
  Morocco.
- Each row is 8 questions: treat any single number as rough. "Similar respondents" uses the same survey's own
  respondents and is a ceiling, not a rival (see above).

**Measures.**

- **Mean absolute error per question**, in points, across answer options.
- **Share of questions with an option more than 15 points off.**
- **Options real people chose (5% or more) that the simulation almost never did** (under 1%).
- **Spread ratio** on scales: simulated over real. Below 1 means answers are too bunched.
- **Individual accuracy** for twins.
- **Ranges held** (section 4).

Results by question type replace the published starting figures once 20 or more questions of a type are tested.

**Memorisation.** Famous, older polls may be in a model's training data, which flatters every method. Prefer survey
waves fielded after the model's training cut-off. The Data page explains how to add the newest Pew waves.

## 7. Known failure modes

Ranked by how much they hurt, from the published evidence (sources in `docs/research.md`):

1. **Stereotyped subgroups.** Majorities become near-unanimous (Pew: 97% simulated against 43% real for Hispanic
   adults' World Cup interest), and gaps between segments come out 2–4× too large. Subgroup results get larger error
   ranges and a warning.
2. **Answers too alike.** Spreads too narrow, real options never chosen, so p-values would be invalid. Addressed with
   stated probabilities, "Not sure" and a check on each result for options almost nobody chose. The answers stay too
   alike all the same, so no significance tests are shown.
3. **A good topline hiding bad subgroups and new topics.** Subgroup and topical errors are labelled separately.
4. **Inflated treatment effects.** Placebo arms, and a note that direction is more reliable than size.
5. **Knowledge questions answered far too well.** "Have you heard of…" questions get the knowledge label, the widest
   errors and a warning.
6. **Left-leaning invented backstories.** The model never invents facts.
7. **Positivity and social desirability.** The prompt asks for this person's real answer; consumer results are
   labelled directional unless calibrated with a human sample.
8. **Position, label and wording artefacts, and model drift.** Options are shuffled, model versions are pinned to
   what you chose, and every answer records the model, option order, prompt fingerprint and seed.
9. **Groups that agree too easily, and personas that drift.** No-discussion branches, restated facts and drift checks.
10. **Flattering validation.** Baselines, measured error by question type, and "ranges held".

## 8. What we don't know yet

These have no published evidence. Your test runs are how to find out:

- How much error attitude matching (census record + survey respondent) adds compared with a person's own answers.
- Whether anchoring to the nearest real poll improves new or topical questions.
- Whether mixing models beats the best single model.
- How much the same-person design inflates effects, and whether the placebo reaction predicts it.
- Whether branching keeps twins more faithful than one long conversation.
- How well any of this works outside the US, and for consumer questions beyond single product categories.
- How stable results are across model versions over months.

## 9. Reproducibility

Every answer is stored with:

- the person and branch;
- the arm;
- the model;
- the option order shown;
- a fingerprint of the exact prompt;
- the study's seed;
- the token counts and the cost.

Duplicate a study to rerun it. Changing the model makes it a different study: results have drifted within three months
in published work, so compare runs only on the same model version.

## 10. Data and licences

Zócalo never ships survey data. The Data page downloads each file from its publisher, or explains how to get it when
the publisher asks you to sign in or fill in a form. Each source keeps its own licence. Some allow non-commercial use
only (WVS, ESS, Latinobarómetro, GlobalOpinionQA, SimBench), and a setting switches those off for commercial use.
Anything you publish that is derived from a source, such as scores or fine-tuned weights, inherits that source's
terms. Models receive one person's profile at a time, never whole datasets.
