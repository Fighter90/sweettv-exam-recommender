"""Recommendation examples for two users on the hold-out (history 11-20 -> truth 21-30):
each method's Top-5 with id, title, category, marked against the user's actual top-5 in weeks 21-30,
plus the user's own history top programmes. Usage: python src/examples.py <oof_attempt_id>"""
import sys, os
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import load, split, pad, topk_from_scores, apk
import methods as M
from ranker import get_frame, predict_topk

aid = int(sys.argv[1])
j, s, sub = load()
h, truth, ts = split(j, s, range(11, 21), range(21, 31))
df, truth2, sub_users, all_users, pop = get_frame()
items = M.item_content(s)
cand = set(ts.tv_show_id)
hh = M.hits(h)
nhi = hh[hh.user_id.isin(set(sub_users))].groupby('user_id').size()
heavy = int((nhi - nhi.quantile(0.9)).abs().idxmin())   # typical heavy viewer: 90th percentile of activity
light = int((nhi - nhi.quantile(0.05)).abs().idxmin())   # light viewer: 5th percentile of activity
U = [heavy, light]
raw = dict(zip(sub.user_id, sub.raw_id))

P = {'Popularity (baseline)': pad({}, U, pop)}
P['Personal frequency'] = pad(topk_from_scores(M.personal_freq(h, cand)), U, pop)
P['ALS (MF)'] = pad(topk_from_scores(M.als(h, cand, U)), U, pop)
P['Item-kNN CF'] = pad(topk_from_scores(M.item_knn(h, cand, U)), U, pop)
P['Personalized PageRank'] = pad(topk_from_scores(M.ppr(h, cand, U)), U, pop)
P['Association rules'] = pad(topk_from_scores(M.assoc_rules(h, cand, U)), U, pop)
P['CBF (TF-IDF)'] = pad(topk_from_scores(M.cbf(h, cand, U, items)), U, pop)
oof = np.load(f'cache/oof_{aid}.npy')
m = df.user_id.isin(set(U)).values
P['Hybrid LightGBM (final)'] = predict_topk(df[m], oof[m], U, pop)

lines = []
for u in U:
    t = truth[u]
    hist_top = hh[hh.user_id == u].groupby('tv_show_id').size().sort_values(ascending=False).head(5)
    lines.append(f'\n### User {raw[u]} ({"heavy, 90th percentile" if u == heavy else "light, 5th percentile"}: {nhi[u]} high-screen airings in weeks 11-20)\n')
    lines.append('History top-5 (weeks 11-20, count of airings watched >= 80%): ' + '; '.join(
        f'{i} {items.title.get(i, "?")} [{items.cat.get(i, "?")}] x{c}' for i, c in hist_top.items()))
    lines.append('\nActual top-5 in weeks 21-30 (official rule): ' + '; '.join(
        f'{i} {items.title.get(i, "?")} [{items.cat.get(i, "?")}]' for i in t) + '\n')
    lines.append('| Method | AP@5 | #1 | #2 | #3 | #4 | #5 |\n|---|---|---|---|---|---|---|')
    for name, pr in P.items():
        cells = []
        for i in pr[u]:
            mark = ' ✔' if i in t else ''
            cells.append(f'{i} {str(items.title.get(i, "?"))[:28]} [{items.cat.get(i, "?")}]{mark}')
        lines.append(f'| {name} | {apk(set(t), pr[u]):.3f} | ' + ' | '.join(cells) + ' |')
out = '\n'.join(lines)
os.makedirs('results', exist_ok=True)
open('results/examples.md', 'w').write(out)
print(out)
