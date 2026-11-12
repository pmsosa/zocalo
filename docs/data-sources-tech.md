# Data sources: technical details for download scripts and loaders

Checked 2026-11-11. **[V]** = verified this pass (URL hit with HEAD/range request, file header or metadata read, or the
official page read). **[U]** = not verified (memory, a search snippet, or an older document). Sizes are compressed
download sizes unless noted. Codes are the stored numeric values; negative or 8/9/98/99-style codes are missing or
refused unless a table says otherwise.

How things were checked: HEAD requests; zip members listed by range-fetching the zip's central directory; CSV and
Stata headers read by inflating only the first bytes of a zip member; Stata value labels read from the last 4 MB of
the CES `.dta`; small files (Afrobarometer R10, Latinobarómetro 2024, codebooks) read with `pyreadstat`/`pypdf` in a
container. About 35 MB was downloaded in total, all under `/tmp/zds`.

---

## 1. US ACS PUMS 1-year

| Item | Detail |
|---|---|
| Latest | **2024** [V]. The `/pums/` index lists folders up to `2024/` only, so 2025 1-year is not out as of 2026-11-11 [V]. The 2024 files are dated 2025-12-04 [V], later than the usual autumn release. |
| National person file | `https://www2.census.gov/programs-surveys/acs/data/pums/2024/1-Year/csv_pus.zip`, 602,847,146 B (575 MB) [V]. Contains `psam_pusa.csv`, `psam_pusb.csv` (split in two; concatenate them) and `ACS2024_PUMS_README.pdf` [V]. |
| National household file | `.../2024/1-Year/csv_hus.zip`, 251.5 MB, `psam_husa.csv` + `psam_husb.csv` [V] |
| Per-state | `.../2024/1-Year/csv_p{st}.zip` (persons) and `csv_h{st}.zip` (housing), `{st}` = lowercase USPS code incl. `dc`, `pr`. E.g. `csv_pca.zip` 70 MB, `csv_pvt.zip` 1.3 MB → `psam_p50.csv` (the member name uses the **FIPS** code, not the letters) [V]. A SAS set is at `sas_*.zip` [V]. |
| Other years | `https://www2.census.gov/programs-surveys/acs/data/pums/{YYYY}/1-Year/csv_{p|h}{st|us}.zip` [V folder pattern 1996–2024]. 2020 1-year has only experimental files [U]. |
| Dictionary | `https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMS_Data_Dictionary_2024.csv` (330 KB; rows `NAME,var,type,len,label` and `VAL,var,type,len,lo,hi,label`) [V]. Also `.txt`, `.pdf`, and `PUMS_Data_Dictionary_2020-2024.*` for the 5-year. |
| API alternative | `https://api.census.gov/data/2024/acs/acs1/pums?get=AGEP,SEX,PWGTP&for=state:06` (a key is needed above 500 calls a day); variable metadata at `https://api.census.gov/data/2024/acs/acs1/pums/variables/SCHL.json` [V]. |
| Access / licence | Open, no login [V]. US government work, public domain. |
| Format | CSV in ZIP; 286 columns in the person file (incl. 80 replicate weights `PWGTP1–80`) [V header] |

Person-building variables (2024 dictionary [V]):

| Field | Variable | Codes |
|---|---|---|
| Link | `SERIALNO` (household id, e.g. `2024HU0000001` / `2024GQ…`), `SPORDER` (person no.) | Join person ↔ housing on `SERIALNO` |
| Age | `AGEP` | 0–99 (top-coded) |
| Sex | `SEX` | 1 Male, 2 Female |
| State | **`STATE`** (2-digit FIPS) | **Renamed from `ST`** (the 2024 file has `STATE`, no `ST`) [V]. Write loaders to accept either. |
| Sub-state | `PUMA` (5-digit, 2020 definitions; unique with STATE), `REGION` 1 NE 2 MW 3 S 4 W 9 PR, `DIVISION` 0–9 | |
| Education | `SCHL` 01–24 (bb = under 3) | Suggested bands: **<HS** 01–15; **HS/GED** 16–17; **Some college/assoc.** 18–20; **Bachelor's** 21; **Graduate** 22–24 |
| Person income | `PINCP` (dollars, can be negative) × `ADJINC`/1e6 | `ADJINC` 2024 = 1015250 (1.015250) |
| Household income | `HINCP` (housing file) × `ADJINC`/1e6 | blank = group quarters/vacant |
| Poverty ratio | `POVPIP` 0–501 | |
| Employment | `ESR` | 1–2 employed, 3 unemployed, 4–5 armed forces, 6 not in labour force, b under 16 |
| Class of worker | `COW` 1–9 | 1 private for-profit … 6–7 self-employed, 9 unemployed 5+ yrs |
| Occupation | `OCCP` (4-digit 2018 Census codes, label prefixed `MGR-`, `EDU-`…), `SOCP` | the prefix gives a ready major group |
| Race | `RAC1P` | 1 White, 2 Black, 3 Am. Indian, 4 Alaska Native, 5 AIAN tribes specified, 6 Asian, 7 NHPI, 8 Other, 9 Two+ |
| Hispanic | `HISP` | 01 = not Hispanic, 02–24 = origin |
| Marital | `MAR` | 1 Married, 2 Widowed, 3 Divorced, 4 Separated, 5 Never married/under 15 |
| Household | `RELSHIPP` (20 = reference person…), `NP` (persons in household) | |
| Urban/rural | **none in PUMS** | Use a PUMA-to-urban crosswalk if needed |
| Weight | `PWGTP` (person), `WGTP` (housing); replicate weights `PWGTP1–80` | |

---

## 2. UK Census 2021: Public Microdata Teaching Sample (England & Wales)

| Item | Detail |
|---|---|
| URL | `https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/publicmicrodatateachingsampleenglandandwalescensus2021/current/upload-publicmicrodatateachingsample.csv` [V, 200, text/csv, page says 36.8 MB] |
| Codes | `https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/microdatasamplecodescensus2021/current/copyofupdatedmicrodatasamplecodes2.zip` → one `.ods`, sheet `Microdata_sample_codes` (columns `Microdata_variable_name, Classification_mnemonic, Category_code, Category_label, …`) [V] |
| Size / rows | 1% sample, about 604k persons [U, UKDS snippet] |
| Access / licence | Open, no login [V]. Open Government Licence v3 [U, from the ONS user guide via search] |
| Coverage | England and Wales only. Scotland and Northern Ireland publish their own files (not checked). |

The CSV has **19 columns** [V header]: `resident_id_m, approx_social_grade, country_of_birth_3a, economic_activity_status_10m,
ethnic_group_tb_6a, health_in_general, hh_families_type_6a, hours_per_week_worked, in_full_time_education, industry_10a,
iol22cd, legal_partnership_status_6a, occupation_10a, region, religion_tb, residence_type, resident_age_7d, sex,
usual_short_student`.

| Field | Variable | Codes [V from the codes ODS] |
|---|---|---|
| Age | `resident_age_7d` | 1 ≤15, 2 16–24, 3 25–34, 4 35–44, 5 45–54, 6 55–64, 7 65+ |
| Sex | `sex` | **1 Female, 2 Male** (the reverse of most sources) |
| Region | `region` | E12000001 NE … E12000009 SW, E12000007 London, W92000004 Wales |
| Education | **not in the teaching sample** | the closest proxy is `approx_social_grade` 1 AB, 2 C1, 3 C2, 4 DE, -8 n/a |
| Income | **none** | |
| Employment | `economic_activity_status_10m` | 1 employee, 2 self-employed, 3 unemployed, 4 FT student active, 5 retired, 6 student, 7 home/family, 8 sick/disabled, 9 other |
| Occupation | `occupation_10a` | SOC 2020 major groups 1–9 |
| Ethnicity | `ethnic_group_tb_6a` | 1 Asian, 2 Black, 3 Mixed, 4 White, 5 Other |
| Marital | `legal_partnership_status_6a` | 1 never married, 2 married/CP, 3 separated, 4 divorced, 5 widowed |
| Religion | `religion_tb` | 1 none, 2 Christian, 3 Buddhist, 4 Hindu, 5 Jewish, 6 Muslim, 7 Sikh, 8 other, 9 not answered |
| Urban/rural | none | |
| Weight | **none** (self-weighting 1% sample; weight = 100) | |

-8 = does not apply (mostly children). This file is thin: without education and income, UK people need those from
another source (e.g. matched from ESS/WVS UK respondents) or the safeguarded sample via UKDS (needs registration).

---

## 3. Canada 2021 Census PUMF, Individuals file (98M0001X2021001)

| Item | Detail |
|---|---|
| URL | `https://www150.statcan.gc.ca/n1/pub/98m0001x/2023001/cen21_ind_98m0001x_part_rec21.zip`, 181,780,881 B [V]. **Script-friendly: yes**, plain GET, no login. |
| Index of all years | `https://www150.statcan.gc.ca/n1/pub/98m0001x/index-eng.htm` [V]: 2016 `cen16_ind_98m0001x_part_rec16.zip`, 2011 NHS `nhs11_ind_99m0001x_part_enm11.zip`, 2006, 2001, 1996, 1991; hierarchical 2021 `cen21_hier_98M0001X_rec21_hier.zip` (67 MB). All under `.../98m0001x/2023001/`. |
| Contents [V] | `data_donnees_2021_ind.dat` (fixed width, 582 MB), **`data_donnees_2021_ind_v2.csv`** (596 MB unzipped), user guide PDF, questionnaires, reference guides, `English/SAS, SPSS and STATA command files/ipumf_2021_final_en_v2.do` (value labels), `.sps`, `.sas`, `.dct`, licence `.docx` |
| Size | 2.7% sample, 144 variables (+ `WEIGHT` and replicates `WT1–WT16`) [V] |
| Licence | Statistics Canada Open Licence [V, file name in the zip] |

| Field | Variable | Codes [V from the `.do` labels] |
|---|---|---|
| Age | `AGEGRP` | 1 0–4, 2 5–6, 3 7–9, 4 10–11, 5 12–14, 6 15–17, 7 18–19, 8 20–24, 9 25–29 … 20 80–84, 21 85+, 88 n/a |
| Gender | `Gender` | 1 woman+, 2 man+ |
| Province | `PR` | 10 NL, 11 PE, 12 NS, 13 NB, 24 QC, 35 ON, 46 MB, 47 SK, 48 AB, 59 BC, 70 territories |
| Metro | `CMA` | 535 Toronto, 462 Montréal, 933 Vancouver, … 999 other/non-CMA (a rough urban/rural proxy) |
| Education | `HDGREE` | 1 none; 2 HS; 3–7 trades/college; 8 univ. below bachelor; 9 bachelor; 10–13 above bachelor; 88/99 n/a. Bands: <HS 1, HS 2, post-sec non-univ 3–8, bachelor 9, grad 10–13 |
| HH income | `HHInc` | 33 bands: 1 <$2k … 25 $100–110k … 33 $250k+; 88 n/a. Also `TotInc` (person, dollars; 88888888/99999999 = n/a), `EFInc`, `CFInc` |
| Employment | `LFACT` | 1–2 employed, 3–10 unemployed, 11–14 not in labour force, 99 n/a |
| Occupation | `NOC21` | 1–25 NOC 2021 broad groups |
| Race | `VISMIN` | 1 not visible minority, 2 South Asian, 3 Chinese, 4 Black, 5 Filipino, 6 Arab, 7 Latin American, 8 SE Asian, 9 West Asian, 10 Korean, 11 Japanese, 12 n.i.e., 13 multiple; Indigenous: `ABOID` |
| Marital | `MarStH` | 1 never married, 2 married, 3 common law, 4 separated, 5 divorced, 6 widowed |
| Religion | `Relig` | 1–22 (6 Catholic, 19 Muslim, 22 none…) |
| Weight | `WEIGHT` (about 37 per record) | |

The CSV header was read directly [V]: the first columns are `PPSORT,ABOID,AGEGRP,AGEIMM,…`; `WEIGHT,WT1..WT16` are last.

---

## 4. CES/CCES cumulative file (Harvard Dataverse doi:10.7910/DVN/II2DB6)

| Item | Detail |
|---|---|
| List files | `GET https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/II2DB6` → `.data.latestVersion.files[] | {dataFile.id, dataFile.filename, dataFile.filesize}` [V] |
| Current (v12, released 2026-07-14, covers 2006–2025) [V] | id **14076515** `cumulative_2006-2025.dta` 724.8 MB; id **14076522** `cumulative_2006-2025.feather` 144.0 MB; id **14076530** `.rds` 40.5 MB; id **14076560** `guide_cumulative_2006-2025.pdf` |
| Download | `GET https://dataverse.harvard.edu/api/access/datafile/{id}` → 303 to a signed S3 URL (use `curl -L`) [V]. Don't hard-code ids: they change with each version, so pick the file by name from the listing. |
| Licence | **CC0 1.0** [V, API] |
| Size | about 719k rows (2024: 60,000; 2025: 17,000), 109 columns [V] |
| Labels | `.dta` (Stata 118) holds value labels; **feather/rds hold plain strings** [V guide]. Read the `.dta` with `pyreadstat` or `pandas.read_stata` for codes and labels. |

| Field | Variable | Codes [V from `.dta` labels] |
|---|---|---|
| Year / id | `year`, `case_id` | |
| Weight | `weight` (year-specific), `weight_cumulative` (pooled), `weight_post`, `vvweight`, `vvweight_post` | |
| Geography | `state` (FIPS, labelled names), `st` (FIPS, labelled abbreviations), `cd`, `dist`, `zipcode`, `county_fips` | |
| Age | `age` (`birthyr` too) | 18–109 |
| Sex | `gender` | 1 Male, 2 Female; `gender4` 1 Man 2 Woman 3 Non-binary 4 Other |
| Education | `educ` | 1 No HS, 2 HS grad, 3 Some college, 4 2-year, 5 4-year, 6 Post-grad |
| Race | `race` | 1 White, 2 Black, 3 Hispanic, 4 Asian, 5 Native American, 6 Mixed, 7 Other, 8 Middle Eastern; also `hispanic` 1 Yes 2 No, `race_h` |
| Income | `faminc` | 1 <10k, 2 10–20k … 9 80–100k, 10 100–120k, 11 120–150k, 12 150k+, 13 prefer not to say, 14 skipped |
| Employment | `employ` | 1 FT, 2 PT, 3 temp laid off, 4 unemployed, 5 retired, 6 disabled, 7 homemaker, 8 student, 9 other |
| Marital | `marstat` | 1 Married, 2 Separated, 3 Divorced, 4 Widowed, 5 Single, 6 Domestic partnership |
| Party | `pid3` 1 D, 2 R, 3 Ind, 4 Other, 5 Not sure; `pid7` 1 Strong D … 7 Strong R, 8 Not sure; `pid3_leaner` | |
| Ideology | `ideo5` | 1 Very liberal … 5 Very conservative, 6 Not sure |
| 2024 vote | `voted_pres_24` | 1 Harris, 2 Trump, 3 Stein, 4 RFK Jr., 5 West, 6 Oliver, 7 Other, 8 Undervote; also `voted_pres_20`, `voted_pres_party`, `intent_pres_24` |
| Religion | `religion` 1 Protestant, 2 Catholic, 3 Mormon, 4 Orthodox, 5 Jewish, 6 Muslim, 7 Buddhist, 8 Hindu, 9 Atheist, 10 Agnostic, 11 Nothing in particular, 12 Something else; `relig_imp` 1–4; `relig_church` 1 >weekly … 6 never; `relig_bornagain` | |
| Urban/rural | none (derive from `county_fips`/`zipcode`) | |

Questions beyond these ~100 are in the yearly Common Content files (separate Dataverse datasets), joined on `year` + `case_id`.

---

## 5. GSS cumulative file (NORC)

| Item | Detail |
|---|---|
| Stata | `https://gss.norc.org/content/dam/gss/get-the-data/documents/stata/GSS_stata.zip`, 47,562,980 B, Last-Modified 2026-07-14 [V]. The old `https://gss.norc.org/Documents/stata/GSS_stata.zip` 301-redirects there [V]. |
| SPSS | `https://gss.norc.org/content/dam/gss/get-the-data/documents/spss/GSS_spss.zip`, 111,661,090 B [V] |
| Contents [V] | `GSS_stata/gss7224_r3a.dta` (598 MB, **75,699 rows × 6,943 vars**, Stata 118), `GSS 2024 Codebook R3a.pdf`, `GSS 2024 Release Variables R3a.pdf`, `Release Notes 7224 R3a.pdf`, `GSS 2024 - Whats New R3a.pdf`, `ReadMe.txt` |
| Name pattern | `gss72{YY}_r{N}{a}.dta`: **changes with every release**. Find the `.dta` inside the zip by glob, not by name. |
| Access / licence | No login [V]. No open licence; NORC terms of use (see research.md) [U] |
| Labels | Value labels in the `.dta`; missing values are Stata extended missings (`.d` DK, `.i` IAP, `.n` NA, `.s` skipped on web) [V codebook] |

| Field | Variable | Codes [V from the 2024 codebook] |
|---|---|---|
| Year / id | `year`, `id` | |
| Weight | **`wtssnrps`** (recommended when present, 2004–2024), `wtssps` (1972–2024); `wtssall` legacy [V codebook] | |
| Age | `age` | 18–89 (89 = 89+) |
| Sex | `sex` | 1 Male, 2 Female (web 2024: recoded from `sexbirth1`/`sexnow2`) |
| Region | `region` | **2024 release: 4 census regions only** (1 NE, 2 MW, 3 S, 4 W); divisions and `srcbelt`/`size` moved to sensitive data [V]. Check whether earlier years were recoded too [U]. |
| Urban/rural | `xnorcsiz` | 1 large central city … 10 open country |
| Education | `degree` | 0 <HS, 1 HS, 2 Associate/junior college, 3 Bachelor's, 4 Graduate; `educ` = years |
| Income | `income16` | 26 bands, 1 <$1k … 26 $170k+ (band set varies by year: `income`, `income16`, `income06`…); `realinc`, `coninc` in constant dollars |
| Employment | `wrkstat` | 1 FT, 2 PT, 3 temp not working, 4 unemployed, 5 retired, 6 school, 7 keeping house, 8 other; `occ10`, `prestg10` |
| Race | `race` 1 White, 2 Black, 3 Other; `hispanic` 1 not Hispanic, 2–5 origin; `racecen1` | |
| Marital | `marital` | 1 Married, 2 Widowed, 3 Divorced, 4 Separated, 5 Never married |
| Party | `partyid` | 0 Strong D, 1 Not strong D, 2 Ind-near D, 3 Ind, 4 Ind-near R, 5 Not strong R, 6 Strong R, 7 Other |
| Ideology | `polviews` | 1 Extremely liberal … 7 Extremely conservative |
| Last vote | `pres20` 1 Biden, 2 Trump, 3 Other, 4 Didn't vote; `vote20`. **No 2024 vote yet** (`pres24` absent; it arrives with the 2026 GSS) [V] | |
| Religion | `relig` 1 Protestant, 2 Catholic, 3 Jewish, 4 None, 5 Other, 6–13 …; `attend` 0 never … 8 several times a week; `reliten` | |

---

## 6. BLS Consumer Expenditure PUMD 2024, Interview

| Item | Detail |
|---|---|
| URLs | CSV `https://www.bls.gov/cex/pumd/data/csv/intrvw24.zip` (53.6 MB) [V]; Stata `https://www.bls.gov/cex/pumd/data/stata/intrvw24.zip` (62.9 MB, 2025-12-19) [V]; SAS `.../sas/intrvw24.zip` [V]; Diary `.../{csv,stata,sas}/diary24.zip` [V]. The old `.../data/comma/` path is **404** [V]. |
| Other years | `https://www.bls.gov/cex/pumd/data/{csv|stata|sas}/intrvw{YY}.zip`; 2025 (`intrvw25`) is not out [V 404]. Older years have also used `.../data/csv/cex{YY}_xlsx.zip` research files [V links on the page]. |
| **User-Agent** | Without a UA → 403; with a browser UA (`Mozilla/5.0`) → **403**; with a descriptive UA carrying a contact (`Zocalo/0.1 (open-source survey research tool; contact: <project address>)`) → 200 [V]. Use a project address, never a personal one. |
| Contents [V] | `intrvw24/fmli241x, fmli242, 243, 244, fmli251` (consumer-unit files by quarter, about 22 MB each as `.dta`), `memi*` (members), `mtbi*`, `itbi*`, `itii*`, `expn24/*` (detailed expenditures), `para24/` |
| Dictionary | `https://www.bls.gov/cex/pumd/ce-pumd-interview-diary-dictionary.xlsx` (1.35 MB; sheets Cover, Variables, Codes; columns `Survey, File, Variable Name, …, First year, Last year`) [V] |
| Licence | US government work, public domain [U] |
| Unit | Consumer unit (household), reference person; join `memi` on `NEWID` for every member |

| Field | Variable (FMLI) | Codes [V dictionary] |
|---|---|---|
| Id | `NEWID`, `QINTRVYR`, `QINTRVMO` | |
| Age | `AGE_REF` (`AGE2` spouse) | years |
| Sex | `SEX_REF` | 1 male, 2 female |
| Geography | `REGION` 1 NE, 2 MW, 3 S, 4 W; `STATE` FIPS (suppressed for some), `PSU`, `POPSIZE` 1 >5M … 5 <100k | |
| Urban/rural | `BLS_URBN` | 1 Urban, 2 Rural |
| Education | `EDUC_REF` | 00 never, 10 grades 1–8, 11 HS no diploma, 12 HS grad, 13 some college, 14 associate, 15 bachelor's, 16 master's/prof./doctorate |
| Income | `FINCBTXM` (before tax, imputed), `FINCBTAX`, `INC_RANK` (weighted percentile) | |
| Occupation | `OCCUCOD1` | 01 manager/professional … 15 armed forces |
| Race | `REF_RACE` 1 White, 2 Black, 3 Native American, 4 Asian, 5 Pacific Islander, 6 Multi; `HISP_REF` 1 Hispanic, 2 Non-Hispanic | |
| Marital | `MARITAL1` | 1 Married, 2 Widowed, 3 Divorced, 4 Separated, 5 Never married |
| Household | `FAM_SIZE` | |
| Spending | `TOTEXPCQ` (current quarter; 2024+), plus `*CQ`/`*PQ` summary variables | |
| Weight | `FINLWT21` | For annual estimates, weight by `FINLWT21 × months in scope / 12` (BLS method) [U] |

---

## 7. World Values Survey Wave 7 (2017–2022), v6.0

| Item | Detail |
|---|---|
| Page | `https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp` (the list loads from `AJDocumentationSmpl.jsp`, POST `SAID=0&CndWAVE=7`) [V] |
| Files [V] | "WVS Cross-National Wave 7 {csv, spss, stata, sas, R (rdata), R (rds)} v6 0.zip", plus an "Inverted" set (scales flipped so high = positive). Version 6.0, 66 countries/territories, last survey India July 2023. Citation doi:10.14281/18241.24. |
| Human step | Click the file → registration form: title, full name, institution, e-mail, project title, intended use (instruction / academic research / dissertation / policy / other), short description, tick "Conditions of use" → download. Every download goes through `AJDownloadLicense.jsp` with this form [V]. They get, e.g., the SPSS zip with the cross-national `.sav` (exact member name [U]; it has been `WVS_Cross-National_Wave_7_spss_v6_0.sav` in the past). |
| Licence | Free for non-profit use; citation required; **no redistribution** [V conditions text] |
| Docs | Codebook "WVS7 Codebook Variables report V6.0.pdf" and the master questionnaire are listed as free documents, but the download POST returned an empty body without a browser session [V]. Per-country DDI XML with full value labels is open at IHSN, e.g. `https://catalog.ihsn.org/metadata/export/12279/ddi` (GBR 2022) [V]: a good machine-readable codebook. |
| Labels | `.sav`/`.dta` value labels; missing codes -1 DK, -2 NA, -3 n/a, -4 not asked, -5 missing [U for -3/-4 here; -1/-2/-5 V] |

| Field | Variable | Codes [V from the IHSN DDI of the WVS7 GBR file] |
|---|---|---|
| Country | `B_COUNTRY` (ISO 3166-1 numeric, e.g. 826), `B_COUNTRY_ALPHA` (ISO3), `A_YEAR` | |
| Region | `N_REGION_ISO` (ISO 3166-2), `N_REGION_WVS` [U] | |
| Urban/rural | `H_URBRURAL` (spelled this way, not `H_URRURAL`) 1 Urban, 2 Rural; `H_SETTLEMENT` 1 capital … 5 village; `G_TOWNSIZE` 1–8 | |
| Sex | `Q260` | 1 Male, 2 Female |
| Age | `Q262` | years; `X003R` age bands [U] |
| Education | `Q275` ISCED 2011 0–8; `Q275R` 1 Lower, 2 Middle, 3 Higher | |
| Income | `Q288` 1–10 income step (within country); `Q288R` 1 Low, 2 Medium, 3 High | |
| Employment | `Q279` | 1 FT, 2 PT, 3 self-employed, 4 retired, 5 homemaker, 6 student, 7 unemployed, 8 other |
| Occupation | `Q281` (respondent), 0 never had a job, 1 professional … | |
| Ethnicity | `Q290` (country-prefixed codes, e.g. 826100 = GB White British) | |
| Marital | `Q273` | 1 Married, 2 Living together, 3 Divorced, 4 Separated, 5 Widowed, 6 Single |
| Party | `Q223` vote intention (codes `{ISO}{nnn}`, e.g. 826001 Conservative, 826002 Labour, 826015 Reform UK) | |
| Ideology | `Q240` | 1 Left … 10 Right |
| Religion | `Q289` 0 none, 1 Catholic, 2 Protestant, 3 Orthodox, 4 Jew, 5 Muslim, 6 Hindu, 7 Buddhist, 8 other Christian, 9 other; `Q6` importance of religion 1–4; `Q164` importance of God 1–10; `Q171` attendance 1–7 | |
| Weight | `W_WEIGHT` (within-country design/post-strat weight), `S018` (equilibrated to N=1000), `PWGHT` (population-size weight for pooled estimates) | |

---

## 8. European Social Survey Round 11, integrated file

| Item | Detail |
|---|---|
| Current | **ESS11 integrated file, edition 4.2**, first issued 2026-07-02, 31 countries [V data.norge.no record] |
| Where | `https://ess.sikt.no/en/datafile/242aaa39-3bbb-40f5-98bf-bfb1ce53d8ef` [V, 200, single-page app] |
| Direct download? | **No.** "Can be downloaded after authentication/login on the ESS data portal" [V]. The portal is a SPA on `api.nsd.no/graphql` with SSO at `sso.nsd.no`; downloads go through `startDownloadJob`/`pollDownloadJob` mutations that need a session [V schema]. No script without a user account. |
| Human step | Register/log in (free) on the ESS Data Portal → ESS11 integrated file → choose CSV, SPSS (`.sav`) or Stata (`.dta`) → zip like `ESS11e04_2.zip` containing `ESS11e04_2.sav/.dta` [file name U: the pattern `ESS{round}e{edition}` is standard] |
| Licence | **CC BY-NC-SA 4.0** for data per the ESS conditions-of-use page [V search snippet of europeansocialsurvey.org]. Note: the Norwegian catalogue record says CC BY 4.0 [V]. They conflict; go with the ESS's own page (NC-SA) until confirmed. |
| Labels | Value labels in `.sav`/`.dta`; codebook and questionnaires on the portal |

Variable names are standard across ESS rounds [U, not read from an R11 file this pass]:

| Field | Variable | Codes |
|---|---|---|
| Country | `cntry` (ISO2) | |
| Region | `region` (NUTS code, country-specific) | |
| Sex | `gndr` | 1 Male, 2 Female |
| Age | `agea` | years |
| Education | `eisced` | 1 ES-ISCED I … 7 ES-ISCED V2, 55 other; detailed `edulvlb` |
| Income | `hinctnta` | household income decile 1–10 (national deciles) |
| Employment | `mnactic` (main activity, 1 paid work … 9 other), `isco08` occupation | |
| Ethnicity | `blgetmg` (belongs to an ethnic minority, 1 yes 2 no) | |
| Marital | `maritalb` | 1 married … 6 never married |
| Urban/rural | `domicil` | 1 big city, 2 suburbs, 3 town, 4 village, 5 farm/countryside |
| Party / vote | `prtvt??{cc}` (last national vote; letters change by round and country, e.g. `prtvtdgb` style) and `prtcl??{cc}` (party closeness). Find them by prefix and the `cntry` suffix. | country-specific party codes |
| Ideology | `lrscale` | 0 Left … 10 Right |
| Religion | `rlgblg`, `rlgdnm`, `rlgdgr` (how religious 0–10), `rlgatnd` (attendance 1–7) | |
| Weight | `anweight` (analysis weight = pspwght × pweight × 10,000, recommended since R9), `pspwght`, `dweight`, `pweight` | |

---

## 9. Afrobarometer, Arab Barometer, Latinobarómetro

### 9a. Afrobarometer Round 10 merged (and R9)

| Item | Detail |
|---|---|
| R10 merged (38 countries) | `https://www.afrobarometer.org/wp-content/uploads/2026/10/AB_R10.Merge-Dataset_25Feb26.38ctry.release.sav.zip` (12.5 MB → `AB_R10.Merge Dataset_25Feb26.38ctry.release.sav`, 68.7 MB, **50,961 rows × 425 cols**) [V, downloaded and read]. French: `...release.Fr_.sav.zip`. Codebook: `.../2026/10/Merge_Round_10_Codebook_09.09.26.pdf` (3.6 MB) [V]. |
| R9 merged (39 countries) | `https://www.afrobarometer.org/wp-content/uploads/2025/06/R9.Merge_39ctry.20Nov23.final_.release_Updated.4Jun25-3.sav` (70.6 MB) [V]; codebook `.../2025/07/AB_R9.MergeCodebook_25Jun24.final_.pdf` [V] |
| Access | **Plain GET, no form** [V]. Links are on `https://www.afrobarometer.org/data/merged-data/`. WordPress upload paths and file names change with every release: scrape that page for `.sav` links. |
| Licence | Free, with attribution [U: terms not found on the page] |

| Field | Variable (R10) | Codes [V] |
|---|---|---|
| Country | `COUNTRY` (1 Algeria … 54 Zimbabwe; the label set covers all AB countries) | |
| Region | `REGION` (country-prefixed codes, e.g. 100–111 Benin) | |
| Urban/rural | `URBRUR` 1 Urban, 2 Rural, 3 Peri-urban; `URBRUR_COND` 1 urban/peri, 2 rural | |
| Age | `Q1` | years; 998 refused, 999 DK |
| Sex | `Q101` | 1 Man, 2 Woman |
| Education | `Q96` 0 none … 9 post-grad; `EDUC_COND` 0 none, 1 primary, 2 secondary, 3 post-secondary | |
| Income | none; `LivedPoverty` index, `Q7A–E` going without (e.g. `Q7E` cash income) | |
| Employment | `Q94A` 0 no (not looking), 1 no (looking), 2 PT, 3 FT; `Q94B` occupation 0–… | |
| Ethnicity | `Q83A` (country-prefixed) | |
| Marital | **not in the R10 merged file** [V: no matching variable] | |
| Party | `Q89A` close to a party (0/1), `Q89B` which party; `Q98` vote intention (country-prefixed party codes) | |
| Religion | `Q97` (detailed), `RELIG_COND` 1 Christian, 2 Muslim, 3 Other | |
| Weight | `withinwt_hh` (new, household-level; within-country), `withinwt_ea` (old); `Combinwt_new_hh` / `Combinwt_old_ea` for pooled multi-country | |

### 9b. Arab Barometer Wave IX (Aug 2025 – May 2026)

| Item | Detail |
|---|---|
| Page | `https://www.arabbarometer.org/survey-data/data-downloads/` [V]. Wave IX: Egypt, Iraq, Jordan, Lebanon, Morocco, Palestine, Tunisia, Syria, Mauritania. |
| Human step | Click "Arab Barometer Wave IX: Data Sets" → short form (name, e-mail, institution, purpose of download) → download. "Publicly available at no charge"; the form is for monitoring use [V]. They get `ArabBarometer_WaveIX_English_Datasets_OCT_2026.zip` (8.8 MB, 2026-10-27) [V HEAD]. The file URL sits in the page's `data-file` attribute, so a script could fetch it, but the form is the requested route: have the human do it once. |
| Other waves | `ArabBarometer_WaveVIII_English_v2.zip`, `AB7_English_Version6.zip`, `ArabBarometer_WaveV_ENG.zip`, `ABIV_English.{sav,dta,csv}_.zip` … [V names] |
| Questionnaire | `https://www.arabbarometer.org/wp-content/uploads/ENG-Arab-Barometer-Wave-IX-Release-Questionnaire_OCT_2026-1.pdf` (1.1 MB, no form) [V, read] |
| Licence | Free for non-commercial use with citation [U] |

| Field | Variable (Wave IX questionnaire) [V] | Codes |
|---|---|---|
| Country | `COUNTRY` | 5 Egypt, 7 Iraq, 8 Jordan, 10 Lebanon, 12 Mauritania, 13 Morocco, 15 Palestine, 20 Syria, 21 Tunisia |
| Region | `Q1` governorate | |
| Urban/rural | `Q13` | 1 Urban, 2 Rural, 3 Camp |
| Age | `Q1001` | years |
| Sex | `Q1002` | 1 Male, 2 Female |
| Education | `Q1003` | 1 none, 2 elementary, 3 preparatory/basic, 4 secondary, 5 mid-level diploma, 6 BA, 7 MA+ |
| Income | `Q1016` | 1 covers expenses and can save, 2 covers without difficulty, 3 doesn't cover with some difficulty, 4 significant difficulty |
| Employment | `Q1005` 1 employed, 2 self-employed, 3 retired, 4 housewife, 5 student, 6 unemployed looking, 7 unemployed not looking; `Q1006` FT/PT; `Q1006A` sector | |
| Marital | `Q1010` | 1 single, 2 living with partner, 3 engaged, 4 married, 5 divorced, 6 separated, 7 widowed |
| Vote | `Q301A` voted in last parliamentary election; `QPAL9` (Palestine). No general party-ID item. | |
| Religion | `Q1012` religion (+ `Q1012A_*` sect); `Q609` 1 religious, 2 somewhat, 3 not religious | |
| Weight | `WT` | |

### 9c. Latinobarómetro 2024 (latest released wave)

| Item | Detail |
|---|---|
| Files | `https://www.latinobarometro.org/documents/LAT-2024/latinobarometro-2024-{spss,stata,csv,csvtext,excel,exceltext}-v20250817.zip` (SPSS 5.9 MB, Stata 6.7 MB) [V]. **Plain GET, no login.** The SPSS zip holds `Latinobarometro_2024_Spss_eng_v20250817.sav` and `..._esp_...sav` plus questionnaires [V]. **19,214 rows × 332 cols, 17 countries** [V]. |
| Pattern | Page `https://latinobarometro.org/latinobarometro-{YYYY}` lists `documents/LAT-{YYYY}/latinobarometro-{yyyy}-{fmt}-v{date}.zip`; the version date changes, so scrape the page. The 2025/26 wave has a published report (Oct 2026) but no data file listed yet [V]. |
| Licence | Non-commercial research, teaching and publication; **redistribution prohibited** [V study-level page] |

| Field | Variable [V] | Codes |
|---|---|---|
| Country | `IDENPA` (ISO numeric: 32 AR, 76 BR, 484 MX …) | |
| Region / city | `REG` (country-prefixed), `CIUDAD`; city size `TAMCIUD` 1 <5k … 7 100k+, 8 capital | |
| Age | `EDAD`; `REEDAD` 1 16–25, 2 26–40, 3 41–60, 4 61+ | |
| Sex | `SEXO` | 1 Man, 2 Woman |
| Education | `REEDUC.1` 1 illiterate … 7 complete higher (`S11` detailed) | |
| Income | `S5` 1 enough and can save … 4 not enough, big problems; `S2` subjective class 1–5 | |
| Employment | `S18.A` 1 self-employed, 2 public employee, 3 private employee, 4 temporarily out of work, 5 retired, 6 home, 7 student; `S19` job type | |
| Race | `S7` | 1 Asian, 2 Black, 3 Indigenous, 4 Mestizo, 5 Mulatto, 6 White, 7 Other |
| Marital | not found in the 2024 file [V: no label matched] | |
| Party / vote | `P39STGBS.A` party they would vote for this Sunday (country-prefixed); `P38STGBS` feels close to a party; `FAMPART` party family | |
| Ideology | `P16ST` | 0 Left … 10 Right, 97 none |
| Religion | `S1` (1 Catholic, 2–5 Evangelical…, 97 none); `S1A` devoutness 1–4 | |
| Weight | `WT` | |

In the `.sav`, variable names contain dots (`REEDUC.1`); the Stata version turns them into underscores [U, UCSD guide].

---

## 10. Pew American Trends Panel (ATP)

| Item | Detail |
|---|---|
| Wave pages | `https://www.pewresearch.org/dataset/american-trends-panel-wave-{N}/` [V]; index `https://www.pewresearch.org/datasets/` |
| Human step | Sign in to a free Pew account ("My Account", e-mail login) on the wave page → accept the terms → download the zip. It holds `ATP W{N}.sav` (e.g. `ATP W132.sav` [V SubPOP README]), plus the questionnaire and topline (`.docx`/`.pdf`) and a readme [U]. The download block shows only when logged in [V page CSS]. |
| Latest public waves [V] | W161 Jan 27–Feb 2 2025 (politics); W162 Feb 3–9 (Catholics); W163 Feb 10–17 (social trends); W164 Feb 24–Mar 2 (omnibus); W165 Mar 10–16 (media brands, social trust); W166 Mar 24–30 (Global Attitudes US); W167 Apr 7–13 (politics); W168 Apr 14–20 (online fraud, journalists); **W169 Apr 28–May 4 2025 (climate and energy)**. W160 page 404; **no W170+ yet**. Datasets appear about 12–18 months after fieldwork. |
| Post-cutoff test material | Nothing fielded in 2026 is public yet. For a model with an early-2025 cutoff, W161–W169 are the newest. For Opus-class models with later cutoffs, wait for W170+; check the wave pages monthly (a 404→200 flip). W159 (Nov 12–17 2024, post-election) carries 2024 vote. |
| Licence | Pew terms: no redistribution "substantially in full" (see research.md); account required |
| Labels | Value labels in the `.sav` (read with `pyreadstat`; Pew warns converting to CSV loses them [V codebook]) |
| Weight | `WEIGHT_W{N}` (e.g. `WEIGHT_W169`) [U per-wave name; naming standard] |

Standard profile ("frame") variables, from Pew's "Codebook and instructions for working with ATP data" (Dec 2019)
`https://www.pewresearch.org/wp-content/uploads/2018/05/Codebook-and-instructions-for-working-with-ATP-data.pdf` [V].
Recent waves keep most names; some carry new suffixes (e.g. `F_RACETHNMOD`, `F_RELIG`, `F_PARTY_FINAL`) [U for 2025 waves].

| Field | Variable | Codes [V 2019 codebook] |
|---|---|---|
| Age | `F_AGECAT` | 1 18–29, 2 30–49, 3 50–64, 4 65+, 99 Ref |
| Sex/gender | `F_GENDER` 1 man, 2 woman, 3 other; older `F_SEX` 1 M 2 F | |
| Region | `F_CREGION` 1 NE, 2 MW, 3 S, 4 W; `F_CDIVISION` 1–9 | |
| Urban | `F_METRO` | 1 Metropolitan, 2 Non-metro |
| Education | `F_EDUCCAT` 1 college grad+, 2 some college, 3 HS or less; `F_EDUCCAT2` 6-way | |
| Income | `F_INC_SDT1` 1 <$30k, 2 30–40k … 8 90–100k, 9 $100k+; `F_INC_TIER2` 1 lower, 2 middle, 3 upper | |
| Race | `F_RACETHNMOD3`/`F_RACETHNMOD` 1 White NH, 2 Black NH, 3 Hispanic, 4 Other, 5 Asian NH; `F_RACECMB2`, `F_HISP` | |
| Marital | `F_MARITAL` | 1 Married, 2 Living with partner, 3 Divorced, 4 Separated, 5 Widowed, 6 Never married |
| Party | `F_PARTY_FINAL` 1 Rep, 2 Dem, 3 Ind, 4 Something else; `F_PARTYLN_FINAL`; `F_PARTYSUM_FINAL` 1 R/lean R, 2 D/lean D, 9 DK | |
| Ideology | `F_IDEO` | 1 Very conservative … 5 Very liberal |
| Religion | `F_RELIG4`/`F_RELIG` 1 Protestant, 2 Catholic … 9 Atheist, 10 Agnostic …; `F_ATTEND` 1 >weekly … 6 never; `F_BORN` (born-again) | |
| Other | `F_REG` (registered), `F_CITIZEN`, `F_INTFREQ`, `F_VOLSUM`, `F_BIRTHPLACE2` | |

---

## 11. Test sets on Hugging Face

All three are **ungated**, no token needed [V `gated:false`]. Base URLs:
`https://huggingface.co/api/datasets/{id}` (metadata, `siblings` = file list),
`https://huggingface.co/api/datasets/{id}/tree/main/{path}` (files with sizes),
`https://huggingface.co/datasets/{id}/resolve/main/{path}` (download),
`https://datasets-server.huggingface.co/{info|splits|first-rows|parquet}?dataset={id}[&config=&split=]`.

### 11a. Twin-2K-500 (`LLM-Digital-Twin/Twin-2K-500`), CC BY 4.0 [V]

| Item | Detail [V] |
|---|---|
| Configs | `full_persona` (2,058 rows; cols `pid, persona_text, persona_summary, persona_json`) and `wave_split` (2,058 rows; `pid, wave1_3_persona_text, wave1_3_persona_json, wave4_Q_wave1_3_A, wave4_Q_wave4_A`). Download 203 MB / 189 MB, about 635 MB in memory. |
| Parquet | Repo files `full_persona/chunks/persona_chunk_00{1..7}.parquet`, `wave_split/chunks/wave_persona_chunk_00{1..7}.parquet`; auto-converted `https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500/resolve/refs%2Fconvert%2Fparquet/{config}/data/000{0..6}.parquet` (about 29 MB each) |
| Flat CSVs (best for loaders) | `question_catalog_and_human_response_csv/question_catalog.json` (214 KB; 256 QuestionIDs with `QuestionID, QuestionText, QuestionType, Options, Rows, Columns, Statements, Range, BlockName, csv_columns`), `wave1_3_response.csv` (5.5 MB, numeric: `pid, QID11 … QID53_TEXT`), `wave1_3_response_label.csv` (21 MB), `wave4_response.csv` (0.6 MB), `wave4_response_label.csv` (4.7 MB) |
| Raw | `raw_data/wave_{1..4}_{numbers,labels}_anonymized.csv` (6–14 MB each), `raw_data/wave {1..3} scores.csv`, questionnaires as `.docx` |
| Example row | `pid=574`; `persona_text` starts "Which part of the United States do you currently live in? Question Type: Single Choice Options: …"; `persona_json` is a Qualtrics-style list of blocks (`ElementType, BlockName "Demographics", Questions[…]`). |
| Demographics (QIDs, 1-based option index in the numeric CSV) | QID11 region (1 NE, 2 MW, 3 South, 4 West, 5 Pacific HI/AK), QID12 sex at birth (1 M 2 F), QID13 age (1 18–29, 2 30–49, 3 50–64, 4 65+), QID14 education (6 levels), QID15 race (White/Black/Asian/Hispanic/Other), QID16 citizen, QID17 marital (Pew 6-way), QID18 religion (12), QID19 attendance (6), QID20 party (R/D/Ind/Other), QID21 income (5 bands), QID22 ideology (5), QID23 household size, QID24 employment (7). These mirror Pew's ATP items. |

### 11b. GlobalOpinionQA (`Anthropic/llm_global_opinions`), CC BY-NC-SA 4.0 [V]

| Item | Detail [V] |
|---|---|
| Files | `data/global_opinions.csv` (4.7 MB); parquet `https://huggingface.co/datasets/Anthropic/llm_global_opinions/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet` (1.4 MB) |
| Rows | 2,556 (split `train`) |
| Columns | `question` (str), `selections` (str), `options` (str), `source` (`GAS` = Pew Global Attitudes, `WVS`) |
| Gotcha | `selections` is a Python repr: `"defaultdict(<class 'list'>, {'Belgium': [0.21, 0.07, 0.69, 0.03], …})"`; `options` is a Python list repr. Parse with `ast.literal_eval` after stripping `defaultdict(<class 'list'>, ` and the closing `)`. |
| Example | "When it comes to Germany's decision-making in the EU, does Germany have too much / too little / about the right influence?" options `['Has too much influence','Has too little influence','Has about the right amount of influence','DK/Refused']`, Greece `[0.86,0.04,0.10,0.0]`, source `GAS`. |

### 11c. SimBench (`pitehu/SimBench`), CC BY-NC-SA 4.0 [V]

| Item | Detail [V] |
|---|---|
| Files | `SimBenchPop.csv` (4.4 MB), `SimBenchGrouped.csv` (4.3 MB), `.pkl` copies (2–4 MB) |
| Splits | `SimBenchPop` (7,167 rows, 20 source datasets), `SimBenchGrouped` (6,343 rows; Afrobarometer, ESS, ISSP, Latinobarómetro, OpinionQA) [V README] |
| Viewer | `datasets-server` `splits` works, but `info`/`first-rows` **fail** (config-info failed, `viewer:false`) [V]: read the CSVs directly. |
| Pop columns | `(index), group_prompt_template, group_prompt_variable_map, input_template, auxiliary, group_size, human_answer, dataset_name` |
| Grouped columns | `group_prompt_template, group_prompt_variable_map, input_template, input_variable_map, output_format, answer_options, auxiliary, group_size, human_answer, wave, group_prompt_variable_list, num_grouping_vars, grouping_keys, is_allowed_vars, dataset_name` |
| Gotchas | Dict and set columns are Python reprs (`frozenset()`, `set()`), so use `ast.literal_eval`. `human_answer` is in **percent (0–100)**, though the README says proportions. Multi-line question text sits inside quoted CSV fields. |
| Example (Grouped) | "You are from the United States. The year is 2017." / "Whether someone is a man or a woman is determined by sex at birth (A) vs can differ (B) vs Refused (C)" / `human_answer {'A': 54.4, 'B': 44.0, 'C': 1.6}`, `group_size 4553`, `wave 29.0`, `dataset_name OpinionQA`. |

---

## 12. OpinionQA and SubPOP

| Set | Access |
|---|---|
| **OpinionQA** | **Not actually gated** [V]. CodaLab worksheet `0x6fb693719477478aac73fc07db333f69` ("OpinionsQA Dataset"). Bundles: `model_input` `0xa6f81cc62d7d4ccb93031a72d2043669` (0.5 MB, 1,498 questions), `human_resp` `0x050b7e72abb04d1f9b493c1743e580cf` (210 MB), `runs` `0xd70e…ee9` (4.4 GB, skip). Download: `GET https://worksheets.codalab.org/rest/bundles/{uuid}/contents/blob/` → `model_input.tar.gz` / `human_resp.tar.gz` [V headers]. List bundles: `https://worksheets.codalab.org/rest/worksheets/0x6fb693719477478aac73fc07db333f69?include=items,items.bundle` [V]. Derived from Pew ATP waves, so Pew's terms carry over. Unofficial HF mirrors exist (e.g. `timchen0618/OpinionQA`); not recommended. |
| **SubPOP** | HF `jjssuh/subpop`, **`gated: manual`** (authors approve each request), CC BY-NC-SA 4.0, files `subpop_train.jsonl`, `subpop_eval.jsonl` [V API]. Human step: log in to HF → open the dataset page → accept the terms / request access → wait for approval → create a read token → the script downloads with `Authorization: Bearer $HF_TOKEN`. Alternative: rebuild from raw `ATP W61…W132.sav` (Pew, account needed) and GSS 2022 with the code at `github.com/JosephJeesungSuh/subpop` [V README]. |

---

## Script-friendly vs manual

| Source | Script can fetch? | Human step | Licence (short) |
|---|---|---|---|
| ACS PUMS | Yes | none | Public domain |
| UK Census 2021 teaching sample | Yes | none | OGL v3 [U] |
| Canada 2021 PUMF | Yes | none | StatCan Open Licence |
| CES cumulative | Yes (Dataverse API) | none | CC0 |
| GSS | Yes | none | NORC terms |
| BLS CE PUMD | Yes, with a contact User-Agent | none | Public domain |
| Afrobarometer R9/R10 | Yes (scrape the page for links) | none | Free, attribution [U] |
| Latinobarómetro 2024 | Yes (scrape the page for links) | none | Non-commercial, no redistribution |
| Arab Barometer IX | URL is in the HTML, but a usage form is requested | Fill the form once | Free, non-commercial [U] |
| WVS 7 | No (form on every download) | Fill the form, download the zip | Non-profit, no redistribution |
| ESS 11 | No (login) | Free ESS portal account | CC BY-NC-SA 4.0 |
| Pew ATP | No (login) | Free Pew account, per wave | Pew terms, no redistribution |
| Twin-2K-500, GlobalOpinionQA, SimBench | Yes (HF, no token) | none | CC BY / NC-SA / NC-SA |
| OpinionQA | Yes (CodaLab) | none | Pew-derived |
| SubPOP | After approval | HF access request + token | CC BY-NC-SA |

## Per-country population source

| Country / area | Best person source | Weight | Notes |
|---|---|---|---|
| United States | ACS PUMS 2024 (people, households) | `PWGTP` (`WGTP` households) | Attitudes matched from CES (`weight`), GSS (`wtssnrps`), Pew (`WEIGHT_W##`) |
| England & Wales | Census 2021 teaching sample | none (×100) | No education/income; enrich from ESS GB / WVS GB |
| UK (whole) | ESS 11 GB, WVS 7 GB (2022) and NI | `anweight`; `W_WEIGHT` | Opinion-survey respondents as people |
| Canada | 2021 Census PUMF | `WEIGHT` | Attitudes: WVS 7 Canada 2020 (`W_WEIGHT`) |
| ESS countries (31 in R11: most of the EU plus UK, CH, NO, IS, IL, RS, ME, UA…) | ESS 11 | `anweight` | Exact R11 country list on the portal [U] |
| WVS 7 countries (66; e.g. AR, BR, CN, IN, ID, JP, KR, MX, NG, PK, TR, US…) | WVS 7 v6.0 | `W_WEIGHT` (`PWGHT` for pooled) | Fieldwork 2017–2023, so the data is dated |
| Africa (38 countries, R10) | Afrobarometer R10 | `withinwt_hh` (`Combinwt_new_hh` pooled) | No marital status; income only as lived-poverty |
| Arab world (EG, IQ, JO, LB, MA, PS, TN, SY, MR) | Arab Barometer IX | `WT` | Plus WVS 7 for EG, IQ, JO, LB, LY, MA, TN |
| Latin America (17) | Latinobarómetro 2024 | `WT` | Plus WVS 7 for AR, BO, BR, CL, CO, EC, GT, MX, NI, PE, PR, UY, VE |

## Caveats

- **Names that change each release:** GSS `gss72{YY}_r{N}{a}.dta`; Afrobarometer and Arab Barometer WordPress paths
  (`/wp-content/uploads/{yyyy}/{mm}/…`) and dated names; Latinobarómetro `-v{YYYYMMDD}`; CES Dataverse file ids (change
  with each version); ESS `ESS{r}e{edition}`. Find files by pattern on the index page or API, never hard-code them.
- **Renamed variables:** ACS `ST` → `STATE` (2024 file has only `STATE`). GSS 2024 `REGION` is now 4 regions;
  `SRCBELT`/`SIZE` gone. WVS urban/rural is `H_URBRURAL`, not `H_URRURAL`.
- **Opposite or odd codes:** UK teaching sample `sex` 1 = Female; GSS `partyid` starts at 0; WVS `Q164` 1 = not
  important; Pew `F_IDEO` 1 = very conservative; SimBench `human_answer` in percent.
- **Broken or moved:** BLS `.../pumd/data/comma/` is 404 (use `/csv/`); the old GSS `/Documents/...` URLs 301-redirect
  (follow redirects). The WVS free-document download returned an empty body to curl (needs a browser session).
- **Not out yet (as of 2026-11-11):** ACS 2025 1-year; BLS `intrvw25`; GSS 2024 has no 2024-vote item; Pew waves
  after W169 (May 2025); Latinobarómetro 2025/26 data; anything fielded in 2026 from Pew.
- **Not verified this pass:** ESS R11 variable names and file name (login wall); Pew per-wave names for 2025 waves
  (the codebook read is from 2019); WVS data file member names and its codebook PDF; OGL for the UK file; BLS
  annualisation formula; licences of Afrobarometer and Arab Barometer.
- **Licence conflict:** ESS: the ESS's own page says CC BY-NC-SA 4.0; the Norwegian catalogue says CC BY 4.0. Treat
  it as NC-SA.
- **Gaps for building people:** the UK teaching sample has no education, income or weight. Afrobarometer R10 and
  Latinobarómetro 2024 have no marital status. ACS has no urban/rural. Most opinion surveys give income only as
  deciles, steps or "does income cover expenses", not money.
