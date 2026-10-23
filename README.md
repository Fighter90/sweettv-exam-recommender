# sweet.tv TV-program recommender — LLM4Rec final exam (AVITO cohort)

Sergey Emelyanov (Kaggle: `pochtasergeia`). Competition: <https://www.kaggle.com/competitions/sweettv-tv-program-recommender> (late submission).

**Final submission** [`submission/sub_final.csv`](submission/sub_final.csv): public MAP@5 **0.46135**, private 0.44801
(screenshot: [`screenshots/kaggle_submissions.png`](screenshots/kaggle_submissions.png)).
First submission `submission/sub_bin3.csv`: public 0.45892, private 0.44756.

## Task and metric

For each of 1,260 users, predict the 5 programmes (`tv_show_id`) they will watch most in weeks 31–42.
The competition's Data page defines the answer: drop `tv_show_id = 0`, compute per user and airing
*screen time = watched seconds / programme duration*, keep airings with screen time ≥ 0.8, count them per
programme, take the 5 most frequent. Metric: MAP@5 (`src/common.py: apk`, the Kaggle / ml_metrics formula
`sum_k P@k·rel(k) / min(|truth|, 5)`).

## Pipeline

| Step | File | What it does |
|---|---|---|
| 1 | `src/prep.py` | Reads the 4 CSVs, drops `tv_show_id = 0`, joins views to the schedule (same channel, overlapping interval, per-channel `searchsorted`), sums the overlap of view fragments per (user, airing). |
| 2 | `src/common.py` | Temporal split, official top-5 truth rule, MAP@5. |
| 3 | `src/methods.py` | Popularity baseline, personal frequency, ALS (implicit MF), item-kNN, Personalized PageRank, association rules, CBF (TF-IDF over category/genres/director/actors/channel). |
| 4 | `src/run_attempts.py` | Single-method attempts 1–10, 61–92 on the hold-out. |
| 5 | `src/features.py`, `src/ranker.py`, `src/hp_search*.py`, `src/ensemble.py`, `src/exp_len.py` | Hybrid: candidate generation (own history + top-30 of PPR/ALS/AR/CBF + top-20 popular) and LightGBM re-ranking; attempts 11–60, 93–124. |
| 6 | `src/make_submission.py final submission/sub_final.csv` | Trains the final ensemble on all hold-out users and scores weeks 31–42 from weeks 11–30 history. |
| 7 | `src/examples.py 123`, `src/figure.py`, `src/data_stats.py` | Two-user examples, Fig. 1, data accounting for the report. |

Validation: history weeks 11–20 → truth weeks 21–30 (official rule). Single methods are scored directly;
the hybrid uses 3-fold cross-validation **by user** (a user's rows are never in the training folds that score it);
extra temporal splits (11–24 → 25–30, 11–17 → 18–24) are used only as additional training rows, without the held-out users.
All 124 attempts with both user sets are in [`results/attempts_table.csv`](results/attempts_table.csv).
The attempts were run in chronological order while feature groups were being added (habit/slot features from #23,
stickiness/near-term airings from #29, full-pair PPR from #93, weekly lags from #106); `src/features.py` now builds all
groups, so re-running an early hybrid attempt uses the full feature set and can differ from its logged value by noise-level amounts.

## Results (hold-out MAP@5)

| Method (best setting) | Attempt | Test users (1150) | All users (4030) |
|---|---|---|---|
| Popularity baseline | 1 | 0.305 | 0.279 |
| CBF TF-IDF | 89 | 0.204 | 0.190 |
| Item-kNN CF | 92 | 0.218 | 0.207 |
| ALS matrix factorisation | 66 | 0.235 | 0.227 |
| Association rules | 82 | 0.320 | 0.300 |
| Personal frequency | 61 | 0.392 | 0.356 |
| Personalized PageRank, α = 0.5 | 77 | 0.394 | 0.361 |
| Hybrid LightGBM (binary, 5 seeds) | 107 | 0.446 | 0.412 |
| **Final ensemble** | **123** | **0.447** | **0.413** |

## Reproduce

```bash
pip install -r requirements.txt
# put the competition files (dataset11-30.csv, export_arh_*.csv, submission.csv) into data/
python src/prep.py data cache                 # ~45 s
python src/run_attempts.py $(seq 1 10) $(seq 61 92)   # single methods
python src/ranker.py 11 12                    # hybrid attempts (builds and caches features on first run)
python src/hp_search3.py 106 107 121 122      # final components
python src/ensemble.py 123 "final" 107 121 122
python src/make_submission.py final submission/sub_final.csv   # ~12 min on 4 vCPU
```

Seeds: LightGBM 1–5 (component seed bags), fold assignment `RandomState(0)`, ALS `random_state=42`.
Environment: Python 3.13.16, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, scikit-learn 1.9.1, lightgbm 4.7.0,
implicit 0.7.3, matplotlib 3.11.2; 4 vCPU Intel Xeon 2.1 GHz, 15 GB RAM, Linux.

The data files are not redistributed here (competition rules); download them from the competition page after accepting its rules.
