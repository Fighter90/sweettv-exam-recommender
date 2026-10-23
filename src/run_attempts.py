"""Single-method attempts on the temporal hold-out; appends to results/attempts.csv.
Hold-out: history weeks 11-20 -> truth weeks 21-30 (official top-5 rule). Reported on two user sets:
'sub' = test users (submission.csv) with a full top-5 in weeks 21-30 (1150), 'all' = every user with a
full top-5 (4030). Every method is padded with the same popularity list (cold-start fallback).
Usage: python src/run_attempts.py 1 2 3"""
import sys, time, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import load, split, mapk, pad, topk_from_scores
import methods as M

HIST, TGT = range(11, 21), range(21, 31)
j, s, sub = load()
h, truth, tsched = split(j, s, HIST, TGT)
subu = set(sub.user_id)
USERS = [u for u in sub.user_id if u in truth]
ALL = list(truth)
CAND = set(tsched.tv_show_id)
POP = M.popularity(h, CAND, ALL)
ITEMS = M.item_content(s)  # programme metadata only (no viewing data)
# target-window airings per programme (schedule only) and history airings per programme
SCH = s[s.tv_show_id != 0].assign(week=lambda d: 11 + d.ts // (7 * 86400))
AIR_T = SCH[SCH.week.isin(TGT)].groupby('tv_show_id').size()
AIR_H = SCH[SCH.week.isin(HIST)].groupby('tv_show_id').size()


def ev(sc):
    preds = pad(topk_from_scores(sc), ALL, POP)
    return mapk(truth, preds, USERS), mapk(truth, preds, ALL)


def A(i):
    lw = max(HIST)
    if i == 1:   return 'popularity (high-screen airings, cand pool)', ev(pd.DataFrame(columns=['user_id', 'tv_show_id', 'score']))
    if i == 2:   return 'personal frequency', ev(M.personal_freq(h, CAND))
    if i == 3:   return 'personal frequency, decay hl=4w', ev(M.personal_freq(h, CAND, 4, lw))
    if i == 4:   return 'personal frequency, decay hl=2w', ev(M.personal_freq(h, CAND, 2, lw))
    if i == 5:   return 'personal frequency x target airings / history airings', ev(
        M.personal_freq(h, CAND, weight_target=(AIR_T / AIR_H).clip(0, 5)))
    if i == 6:   return 'ALS f=64', ev(M.als(h, CAND, ALL))
    if i == 7:   return 'item-kNN cosine', ev(M.item_knn(h, CAND, ALL))
    if i == 8:   return 'PPR alpha=0.15', ev(M.ppr(h, CAND, ALL))
    if i == 9:   return 'assoc rules conf, minsup=20', ev(M.assoc_rules(h, CAND, ALL))
    if i == 10:  return 'CBF tfidf (cat,genre,dir,actors,channel)', ev(M.cbf(h, CAND, ALL, ITEMS))
    X = EXTRA.get(i)
    if X:
        return X[0], ev(X[1]())
    raise KeyError(i)


EXTRA = {}
_id = 61
def reg(name, fn):
    global _id
    EXTRA[_id] = (name, fn)
    _id += 1
lw = max(HIST)
# 61-65 personal frequency variants
for thr in (0.5, 0.95):
    reg(f'personal frequency, screen-time threshold {thr}', lambda thr=thr: M.personal_freq(h, CAND, thr=thr))
for hl in (6, 10):
    reg(f'personal frequency, decay hl={hl}w', lambda hl=hl: M.personal_freq(h, CAND, hl, lw))
reg('personal frequency, last 5 weeks only', lambda: M.personal_freq(h[h.week > lw - 5], CAND))
# 66-73 ALS grid
for f, r, a in [(16, .05, 10), (32, .05, 10), (128, .05, 10), (64, .5, 10), (64, .01, 10), (64, .05, 1), (64, .05, 40), (64, .05, 10, )]:
    pass
for f, r, a, v in [(16, .05, 10, 'log'), (32, .05, 10, 'log'), (128, .05, 10, 'log'), (64, .5, 10, 'log'),
                   (64, .01, 10, 'log'), (64, .05, 1, 'log'), (64, .05, 40, 'log'), (64, .05, 10, 'count')]:
    reg(f'ALS f={f} reg={r} alpha={a} value={v}', lambda f=f, r=r, a=a, v=v: M.als(h, CAND, ALL, factors=f, reg=r, alpha=a, value=v))
# 74-79 PPR grid
for al in (0.05, 0.1, 0.3, 0.5, 0.7):
    reg(f'PPR alpha={al}', lambda al=al: M.ppr(h, CAND, ALL, alpha=al))
reg('PPR alpha=0.15 binary edges', lambda: M.ppr(h, CAND, ALL, value='binary'))
# 80-85 association rules grid
for ms, met in [(5, 'confidence'), (10, 'confidence'), (50, 'confidence'), (100, 'confidence'), (20, 'lift'), (50, 'lift')]:
    reg(f'assoc rules {met}, minsup={ms}', lambda ms=ms, met=met: M.assoc_rules(h, CAND, ALL, min_support=ms, metric=met))
# 86-90 CBF weight variants (category, genre, director, actors, channel)
for w in [(1, 1, 0, 0, 0), (1, 1, 0.5, 0.5, 0), (0, 0, 0, 0, 1), (1, 1, 1, 1, 2), (0.5, 1, 1, 1, 1)]:
    reg(f'CBF weights cat/gen/dir/act/ch={w}', lambda w=w: M.cbf(h, CAND, ALL, ITEMS, weights=w))
# 91-92 item-kNN variants
for sh in (0.0, 50.0):
    reg(f'item-kNN shrink={sh}', lambda sh=sh: M.item_knn(h, CAND, ALL, shrink=sh))


if __name__ == '__main__':
    os.makedirs('results', exist_ok=True)
    print('val users', len(USERS), 'cand', len(CAND))
    for a in sys.argv[1:]:
        t0 = time.time()
        name, (ms, ma) = A(int(a))
        dt = time.time() - t0
        print(f'#{a:>3} sub={ms:.5f} all={ma:.5f} {dt:6.1f}s  {name}', flush=True)
        with open('results/attempts.csv', 'a') as f:
            f.write(f'{a},"{name}",{ms:.5f},{dt:.1f},{ma:.5f}\n')
