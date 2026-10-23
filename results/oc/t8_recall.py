"""Why personal-history methods (attempts 2, 78) beat model-based CF (66, 92), assoc rules (82)
and CBF (89) on the hold-out. (1) Share of each test user's true top-5 (weeks 21-30, official rule)
that already appears in the user's own weeks 11-20 history, counted with any overlap and with
screen time >= 0.8. (2) Recall of the true top-5 inside each method's own top-5 and top-30
(unpadded method lists; same functions and parameters as src/run_attempts.py, imported for its
data and settings). MAP@5 (1150) from results/attempts_table.csv shown for context.
Usage: python results/oc/t8_recall.py"""
import sys, os, time
import numpy as np
import pandas as pd

sys.path.insert(0, 'src')
import run_attempts as RA  # module-level setup only: h, truth, USERS, ALL, CAND, POP, ITEMS

t0 = time.time()
USERS, truth = RA.USERS, RA.truth
K = 5

# ---- (1) how much of the truth is already the user's own history
hi_rows = RA.h[RA.h.ov >= 0.8 * RA.h.pdur]
hist_any = RA.h.groupby('user_id').tv_show_id.agg(set)      # join rows are overlap>0 rows
hist_hi = hi_rows.groupby('user_id').tv_show_id.agg(set)
sh_any = [len(set(truth[u]) & hist_any.get(u, set())) / K for u in USERS]
sh_hi = [len(set(truth[u]) & hist_hi.get(u, set())) / K for u in USERS]
print(f'[history] test users with full truth: {len(USERS)}')
print(f'  share of true top-5 already in own weeks 11-20 history: '
      f'any overlap {np.mean(sh_any):.4f}   screen time >= 0.8 {np.mean(sh_hi):.4f}')
print(f'  users with zero of their true top-5 in own history:    '
      f'any overlap {np.mean([s == 0 for s in sh_any]):.2%}   screen time >= 0.8 {np.mean([s == 0 for s in sh_hi]):.2%}')

# ---- (2) recall of the true top-5 within each method's top-5 / top-30
def rec(sc, k):
    d = sc.sort_values(['user_id', 'score'], ascending=[True, False])
    top = d.groupby('user_id').tv_show_id.apply(lambda x: list(x[:k])).to_dict()
    r = np.mean([len(set(top.get(u, [])) & set(truth[u])) / K for u in USERS])
    cov = np.mean([len(top.get(u, [])) > 0 for u in USERS])
    return float(r), float(cov)

def pop_rec(k):
    p = set(RA.POP[:k])
    return float(np.mean([len(p & set(truth[u])) / K for u in USERS]))

T = {int(r['attempt']): r for r in __import__('csv').DictReader(open('results/attempts_table.csv'))}

rows = []
def add(aid, name, sc):
    r5, c5 = rec(sc, 5)
    r30, _ = rec(sc, 30)
    rows.append((aid, name, r5, r30, c5, float(T[aid]['MAP@5_test_users_1150'])))

rows.append((1, 'popularity (shared padding list)', pop_rec(5), pop_rec(30), 1.0,
             float(T[1]['MAP@5_test_users_1150'])))
add(2, 'personal frequency', RA.M.personal_freq(RA.h, RA.CAND))
add(66, 'ALS f=16 reg=0.05 alpha=10 value=log',
    RA.M.als(RA.h, RA.CAND, RA.ALL, factors=16, reg=0.05, alpha=10, value='log'))
add(78, 'PPR alpha=0.7', RA.M.ppr(RA.h, RA.CAND, RA.ALL, alpha=0.7))
add(82, 'assoc rules confidence, minsup=50',
    RA.M.assoc_rules(RA.h, RA.CAND, RA.ALL, min_support=50, metric='confidence'))
add(89, 'CBF weights (1, 1, 1, 1, 2)', RA.M.cbf(RA.h, RA.CAND, RA.ALL, RA.ITEMS, weights=(1, 1, 1, 1, 2)))
add(92, 'item-kNN shrink=50.0', RA.M.item_knn(RA.h, RA.CAND, RA.ALL, shrink=50.0))

print(f'[recall] recall of the true top-5 within the method list; coverage = users with any scored candidate')
print(f'{"attempt":>7}  {"method":38s} {"R@5":>7} {"R@30":>7} {"cov@5":>7} {"MAP@5":>7}')
for aid, name, r5, r30, c5, m in rows:
    print(f'{aid:>7}  {name:38s} {r5:>7.4f} {r30:>7.4f} {c5:>7.2%} {m:>7.5f}')
print(f'[time] {time.time() - t0:.0f} s')
