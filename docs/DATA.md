# Data guide

Zócalo never ships survey or census data. Each file comes from its publisher, under its own licence. There are two
kinds:

- **Automatic.** Press *download* on the Data page. Zócalo fetches the file from the publisher.
- **By hand.** The publisher asks you to sign in or fill in a short form first. Download the file yourself and put it
  in the folder shown below; the Data page shows *ready* once it finds it.

All files go in the **dataset folder**, set when Zócalo is deployed (`./deploy.sh --datasets-dir PATH`; by default
`./datasets` next to the app). It can sit on an external drive. If the drive is unplugged, Zócalo says so and waits:
it never downloads everything again somewhere else. Everything in the folder can be downloaded again, so it doesn't
need a backup. Back up the **data folder** instead (the database and encrypted keys).

## What each source is for

| Source | Gets you | How | Licence |
|---|---|---|---|
| US Census ACS PUMS 2024 | US people from real census records | automatic, 575 MB | public domain |
| UK Census 2021 teaching sample | England & Wales people | automatic, 37 MB | Open Government Licence |
| Canada 2021 Census PUMF | Canadian people | automatic, 182 MB | Statistics Canada Open Licence |
| Cooperative Election Study | US people, and attitudes for US census people | automatic, 144 MB | CC0 |
| General Social Survey | US people, attitudes, real questions for the index and tests | automatic, 48 MB | NORC terms |
| Afrobarometer Round 10 | People in 38 African countries, questions, tests | automatic, 13 MB | free, with attribution |
| Latinobarómetro 2024 | People in 17 Latin American countries, questions, tests | automatic, 6 MB | **non-commercial** |
| World Values Survey Wave 7 | People in 66 countries, questions, tests | **by hand** | **non-profit** |
| European Social Survey Round 11 | People in 31 European countries | **by hand** | **CC BY-NC-SA** |
| Arab Barometer Wave IX | People in 9 Arab countries | **by hand** | non-commercial |
| Pew American Trends Panel | US people, and the best test material | **by hand**, wave by wave | Pew terms |
| Twin-2K-500 | Test: twins of 2,058 real people | automatic, 27 MB | CC BY 4.0 |
| GlobalOpinionQA | Test: country answer shares | automatic, 5 MB | **CC BY-NC-SA** |
| SimBench | Test: 20 surveys' answer shares | automatic, 4 MB | **CC BY-NC-SA** |

Sources marked non-commercial can be switched off in Settings → Data, for anyone using Zócalo commercially.

After downloading an opinion survey, press **index questions** on the Data page. Its questions and real answer shares
then show up as "closest real polls" next to your results, and become available to the *closest other poll* test
baseline.

## Getting the by-hand sources

In each path below, `DATASETS` is your dataset folder.

### World Values Survey Wave 7 → `DATASETS/wvs/`

1. Open <https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp>.
2. Click **WVS Cross-National Wave 7 spss v6 0.zip** (or the newest version).
3. Fill in the short form (name, institution, intended use) and accept the conditions of use.
4. Unzip it and put the `.sav` file in `DATASETS/wvs/`.

Free for non-profit use. Don't share the file itself.

### European Social Survey Round 11 → `DATASETS/ess/`

1. Sign in, with a free account, at the ESS Data Portal: <https://ess.sikt.no/en/datafile/242aaa39-3bbb-40f5-98bf-bfb1ce53d8ef>
2. Download the **ESS11 integrated file** in **SPSS** format.
3. Unzip it and put the `.sav` file (named like `ESS11e04_2.sav`) in `DATASETS/ess/`.

### Arab Barometer Wave IX → `DATASETS/arab_barometer/`

1. Open <https://www.arabbarometer.org/survey-data/data-downloads/>.
2. Click **Arab Barometer Wave IX: Data Sets** and fill in the short form.
3. Unzip it and put the English `.sav` file in `DATASETS/arab_barometer/`.

### Pew Research Center American Trends Panel → `DATASETS/pew/`

Pew's panel waves are the best material for honest tests, because each wave is a large, carefully weighted sample of
US adults with full question wording.

1. Create a free account at <https://www.pewresearch.org/datasets/> ("My Account").
2. Open a wave page, for example <https://www.pewresearch.org/dataset/american-trends-panel-wave-169/>, accept the terms
   and download it.
3. Unzip it and put `ATP W169.sav` (or whichever wave) in `DATASETS/pew/`. Add as many waves as you like. The newest
   wave is used to build Pew populations.

**Which waves.** For tests, the most useful waves were fielded **after your model's training cut-off**, so the model
can't have seen the results. As of November 2026 the newest public waves are:

| Wave | Fielded | Topic |
|---|---|---|
| W169 | Apr 28 – May 4, 2025 | climate and energy |
| W168 | Apr 14–20, 2025 | online fraud, journalists |
| W167 | Apr 7–13, 2025 | politics |
| W166 | Mar 24–30, 2025 | Global Attitudes (US) |
| W165 | Mar 10–16, 2025 | media brands, social trust |
| W164 | Feb 24 – Mar 2, 2025 | omnibus |
| W163 | Feb 10–17, 2025 | social trends |
| W161 | Jan 27 – Feb 2, 2025 | politics |
| W159 | Nov 12–17, 2024 | post-election (includes the 2024 vote) |

Pew releases datasets 12–18 months after fieldwork. Check the wave pages for W170 and later; a page that used to say
"not found" will start working.

Pew's terms forbid sharing the data "in full or substantially in full". Keep the files to yourself; scores and
summaries you make from them are fine.

## Updating

Publishers release new waves under new file names. The automatic downloads find the current file on the publisher's
page or API. If one stops working because the publisher moved it, download the file by hand into the source's folder
and the Data page will find it. Technical details for each source (URLs, variable names, quirks) are in
`docs/data-sources-tech.md`.
