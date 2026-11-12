# Research notes

Collected 2026-11-11 by two research passes: data sources, and published work on simulated respondents. **Most papers
were read at abstract or summary level only.** Check every number against the paper before it goes into public docs or
the README. Tags: **[R]** the page itself was read, **[S]** search snippet or secondary summary, **[M]** background
knowledge, not re-checked.

## Key papers

| Paper | Finding | What it means for us |
|---|---|---|
| Pew Research Center, 30 Sep 2026, ["Can AI stand in for human survey-takers?"](https://www.pewresearch.org/data-labs/2026/09/30/can-ai-stand-in-for-human-survey-takers-not-really/) ([methods](https://www.pewresearch.org/data-labs/2026/09/30/methodology-silicon-samples/)) [R] | A twin per ATP panelist, Claude Opus 4.6 with 71 attitudes: mean error 12.4 pts, 28% of questions over 15. Profile only 16.0 → + attitudes 13.7 → + reflection 13.1. Opus 11.4, GPT-5.1 13.3, GPT-5 nano 17.4. Hispanic World Cup interest 97% vs 43%; First Amendment knowledge +46; "heard a lot about data centers" 3% vs 25%; humans 4× more "not sure"; half of questions had an option no twin chose. | The bar to beat; the closest analogue to our design. |
| Jang, Lee & Kim 2026, EMNLP Findings, [arXiv 2607.25292](https://arxiv.org/abs/2607.25292) [R abstract] | Same persona and question gives the same answer on over half of items; instruction-tuned models worse than base models; one stated-distribution call more than halves error. | Default elicitation: stated spreads. |
| Meister, Guestrin & Hashimoto 2024, [arXiv 2411.05403](https://arxiv.org/abs/2411.05403) [S] | Stated (JSON) distributions beat token probabilities and sampling. A follow-up (2507.00439) finds calibrated token probabilities best in 10 of 24 settings. | Token probabilities only after calibration. |
| Gordon et al. (Prolific) 2026 preprint, [news report](https://www.research-live.com/article/news/synthetic-respondents-cant-replace-human-measurement-finds-prolific-study/id/5152227) [R news only] | Per-person spreads cut error 35–48%; transcripts halve variance collapse but don't beat a zero-context baseline; MRP weighting didn't fix the remaining error. | Elicitation; weighting is not a fix. |
| Toubia et al. 2025, Mega-study of digital twins, [arXiv 2509.19088](https://arxiv.org/html/2509.19088v2) [R partial] | Accuracy 0.748 vs human retest 0.817 vs random 0.629. Full persona no better than demographics only. Spread too low in 154/164 outcomes. "Blue shift" with richer personas. | Variance collapse; no p-values on raw output. |
| Li, Chen, Namkoong & Peng 2025, NeurIPS position, [arXiv 2503.16527](https://arxiv.org/abs/2503.16527) [S] | More LLM-written persona detail drifts results left, up to a simulated Democratic sweep of every state in 2024. | The model never invents backgrounds. |
| Moon et al. 2024, EMNLP, "Anthology", [arXiv 2407.06576](https://arxiv.org/abs/2407.06576) [S] | LLM-written life stories up to 18% better than demographic prompts. | Counterpoint to Li et al.; we test it. |
| Park et al. 2024, [arXiv 2411.10109](https://arxiv.org/abs/2411.10109) [S] | Agents from 2-hour interviews: 0.85 of human retest accuracy on GSS, vs about 0.71 for demographic agents. | Real per-person data helps most; ours is matched, not interviewed. |
| Chen, Zhu & Zheng 2026, [arXiv 2607.26348](https://arxiv.org/abs/2607.26348) [R abstract] | No LLM beats the best non-AI baseline at individual prediction; gaps between segments inflated 2–4×; wrong segment picked in half of US cases. | Non-AI baseline; subgroup warnings. |
| Lukauskas & Šarkauskaitė 2026, [arXiv 2608.14606](https://arxiv.org/abs/2608.14606) [R abstract] | A Gaussian copula fit on other respondents matches the best of 37 LLMs; within-person spread 0.79 vs 1.19. | Statistical baseline. |
| Hewitt, Ashokkumar, Ghezae & Willer 2024, [Stanford WP](https://www.gsb.stanford.edu/faculty-research/publications/large-language-models-can-predict-results-social-science-experiments) [S] | 70 experiments: predicted vs actual effects r=0.85 (0.90 unpublished), but effect sizes systematically overestimated. | Treatments: direction yes, size inflated. |
| Pohl et al. 2026, [arXiv 2607.28347](https://arxiv.org/abs/2607.28347) [R abstract] | Belief updates "more frequent but smaller" than humans'; faithful only when given the real starting stance. | Information treatments. |
| Tjuatja et al. 2024, TACL [S] | Models are sensitive to perturbations humans ignore. | The puppy placebo. |
| Gui & Toubia 2023–25, [arXiv 2312.15524](https://arxiv.org/abs/2312.15524) [S] | Changing price in the prompt shifts unstated beliefs too; telling the model the experimental design improved all models. | Test design-informed prompts. |
| Dominguez-Olmedo, Hardt & Mendler-Dünner 2024, NeurIPS [S] | Strong option-order and label bias; after randomising, answers trend to uniform. | Randomise option order. |
| Bisbee et al. 2024, *Political Analysis* 32(4) [S] | Means close, spread too low; 48% of regression coefficients differ from ANES; results change over 3 months. | Pin model versions; no inference from raw data. |
| Wang, Morgenstern & Dickerson 2024/25, [arXiv 2402.01908](https://arxiv.org/abs/2402.01908) [S] | Models misportray and flatten identity groups; temperature only partly helps. | Stereotype canaries; temperature isn't a fix. |
| Suh et al. 2025, ACL, SubPOP, [arXiv 2502.16761](https://arxiv.org/abs/2502.16761) [S] | Fine-tuning on Pew answer spreads cuts the gap 32–46%, generalises to GSS. Code: github.com/JosephJeesungSuh/subpop | Phase 5. |
| Kim & Lee 2023/24, [arXiv 2305.09620](https://arxiv.org/abs/2305.09620) [S] | Fine-tuned on GSS: asked questions AUC 0.86 / ρ 0.98; unasked questions AUC 0.73 / ρ 0.67. | New questions are much harder. |
| Zhang, Hortaçsu, Chernozhukov et al. 2025, [arXiv 2510.25743](https://arxiv.org/abs/2510.25743) [R abstract] | Raw LLM choices worsen demand estimates; correcting with 10% human data fixes it. | Human-sample correction. |
| Broska, Howes & van Loon 2025, *Sociological Methods & Research* 54(3) [S] | Prediction-powered inference gives valid results from LLM data plus a human subsample. | Human-calibrated intervals. |
| Brand, Israeli & Ngwe, HBS WP 23-062, [SSRN](https://papers.ssrn.com/abstract=4395751) [S] | Willingness to pay sometimes comparable, often wrong, sometimes wrong-signed. | Demand-curve checks. |
| Harris Poll / AAPOR 2024 [R] | LLM "optimal price" higher than the survey's in 81% of cases. | Consumer results labelled directional. |
| Maier et al. 2025, [arXiv 2510.08338](https://arxiv.org/abs/2510.08338) [S] | Free text matched to scale anchors reaches about 90% of human retest reliability (purchase intent, one category). | Word-to-scale matching. |
| Shao 2026, [arXiv 2609.20543](https://arxiv.org/pdf/2609.20543) [S] | Full consensus: humans 51% vs agents 85–96%. | Debates over-converge. |
| Chuang et al. 2024, NAACL Findings, [arXiv 2311.09618](https://arxiv.org/abs/2311.09618) [S] | Agent networks tilt toward scientific consensus. | Debates. |
| Li et al. 2024 ([arXiv 2402.10962](https://arxiv.org/abs/2402.10962)); Luz de Araujo et al. 2026, EACL ([arXiv 2512.12775](https://arxiv.org/abs/2512.12775)) [S] | Persona drift within 8 rounds; long dialogues converge to the model's default. | Drift control. |
| Hu et al., ICLR 2026, SimBench, [arXiv 2510.17516](https://arxiv.org/abs/2510.17516) [R abstract] | Best model 40.8/100; instruction tuning hurts questions where people disagree. | Test set. |
| Toubia et al. 2025, Twin-2K-500, [arXiv 2505.17479](https://arxiv.org/abs/2505.17479) | 2,058 people, 500 questions, retest wave, CC BY. | Test set. |
| Santurkar et al. 2023 (OpinionQA), Durmus et al. (GlobalOpinionQA), Argyle et al. 2023, Aher et al. 2023, Horton 2023, Hu & Collier 2024, Salecha et al. 2024 | Older foundations: group misalignment, US-leaning defaults, hyper-accurate knowledge answers, social-desirability bias. | Background. |

## Industry
Every vendor headline uses its own metric ("1−MAE", "% of retest"), where random guessing already scores well.
Independent evaluations (Pew, Verasight, Prolific, Harris/AAPOR, Kantar) land at roughly 10–20 points of error, or
"directional only". Verasight: about 4 pts topline on common political questions, 10–30 on subgroups, 19.8 on
consumer (coffee) questions. Vendors seen: Aaru, Simile (Gallup partnership, no numbers yet), Electric Twin (study
funded by the company), Artificial Societies, Synthetic Users, Qualtrics Edge Audiences, GWI, Ipsos, Kantar, Fairgen.
Several commercial tools publish only their own accuracy pages, with no independent validation.

## Failure modes, worst first
1. Subgroup stereotyping and inflated gaps between segments.
2. Variance collapse: options nobody picks, spreads too narrow, invalid p-values.
3. A good topline hiding bad subgroups and new topics.
4. Inflated or spurious treatment effects.
5. Hyper-accurate knowledge and awareness answers.
6. Invented backstories skewing left.
7. Positivity and social-desirability bias.
8. Option order, labels, wording, and model-version drift.
9. Over-convergence and drift in stateful twins and debates.
10. Misleading single metrics and validation on memorised polls.

## Data sources
Summary in the plan's Data section. Licence details found:
- CES cumulative file: CC0. Twin-2K-500: CC BY 4.0.
- ESS, GlobalOpinionQA and SimBench: CC BY-NC-SA.
- WVS: non-profit use, no redistribution.
- Pew: redistributing "substantially in full" is banned; nothing on AI.
- GSS: no open licence; download scripts only.
- AI use banned: Roper Center (policy of Nov 2025), YouGov, Statista; ICPSR counts giving data to a model that keeps
  or trains on it as redistribution.
- Prices: Gallup World Poll $35k/yr (AWS listing); Roper $644–$865 per dataset.
- Not checked: ANES, ICPSR and GESIS terms (their sites blocked the fetch).
