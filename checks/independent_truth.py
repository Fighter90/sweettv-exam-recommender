"""Independent re-implementation of the official answer rule (competition Data page) for a random
sample of users, written without src/: brute-force join of each view with every labelled airing of the
same channel, overlap summed per (user, airing), screen time = overlap / duration >= 0.8, count per
programme, top-5 by count (ties by smaller id). Compared with src/ (cache/join.pkl + common.make_truth).
Usage: python checks/independent_truth.py [n_users=300] [seed=0]"""
import sys, os, time
import numpy as np
import pandas as pd

n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
t0 = time.time()
v = pd.read_csv('data/dataset11-30.csv', dtype={'user_id': np.uint64})
users = np.random.RandomState(seed).choice(np.sort(v.user_id.unique()), n, replace=False)
v = v[v.user_id.isin(set(users))].copy()
v['vs'], v['ve'] = pd.to_datetime(v.start_time), pd.to_datetime(v.stop_time)
# target window = weeks 21-30 by airing start time, [2020-05-18, 2020-07-27). The window is taken from all
# three schedule files: the weeks 11-20 file also carries some airings after midnight of 2020-05-18.
s = pd.concat([pd.read_csv(f'data/export_arh_{p}-final.csv', low_memory=False) for p in ('11-20', '21-30', '31-42')])
s = s[s.tv_show_id != 0].copy()
s['ts'] = pd.to_datetime(s.start_time, format='%d.%m.%Y %H:%M:%S')
s = s[(s.ts >= '2020-05-18') & (s.ts < '2020-07-27')]
s['te'] = s.ts + pd.to_timedelta(s.duration, unit='s')
v = v[v.ve >= s.ts.min()]                                               # views that can touch the window
S = s[['channel_id', 'ts', 'te', 'duration', 'tv_show_id']]
parts = []
for u, g in v.groupby('user_id'):                                         # one user at a time (memory)
    m = g.merge(S, left_on='vsetv_id', right_on='channel_id')
    m['ov'] = (np.minimum(m.ve, m.te) - np.maximum(m.vs, m.ts)).dt.total_seconds()
    m = m[m.ov > 0]
    parts.append(m.groupby(['user_id', 'channel_id', 'ts', 'tv_show_id', 'duration'], as_index=False).ov.sum())
a = pd.concat(parts, ignore_index=True)
a = a[a.ov / a.duration >= 0.8]
c = a.groupby(['user_id', 'tv_show_id']).size().rename('n').reset_index()
c = c.sort_values(['user_id', 'n', 'tv_show_id'], ascending=[True, False, True])
top = c.groupby('user_id').head(5).groupby('user_id').tv_show_id.agg(list)
mine = {int(u): l for u, l in top.items() if len(l) == 5}
print(f'[independent] {n} random users (seed {seed}); {len(mine)} have a full top-5 in weeks 21-30; {time.time()-t0:.0f} s')

sys.path.insert(0, 'src')
from common import load, make_truth, IDS
import common
j, sch, sub = load()
truth = make_truth(j[j.week.isin(range(21, 31))])
code = {int(r): i for i, r in enumerate(common.IDS)}
theirs = {u: truth[code[u]] for u in map(int, users) if u in code and code[u] in truth}
same = sum(mine.get(u) == theirs.get(u) for u in set(mine) | set(theirs))
print(f'[src] users with a full top-5: {len(theirs)}')
print(f'[compare] identical top-5 lists: {same} of {len(set(mine) | set(theirs))}')
for u in sorted(set(mine) | set(theirs)):
    if mine.get(u) != theirs.get(u):
        print('  DIFF', u, 'independent', mine.get(u), 'src', theirs.get(u))
ex = next(iter(sorted(mine)))
print(f'[example] user {ex}: top-5 {mine[ex]}')
