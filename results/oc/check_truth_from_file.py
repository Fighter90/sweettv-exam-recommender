"""File-as-window probe: rebuild the weeks 21-30 truth from export_arh_21-30-final.csv ONLY
(whole file, no date filter), same 300 users (seed 0) as checks/independent_truth.py, and compare
with src/ truth (cache/join.pkl + common.make_truth). For DIFF users, prints the qualifying
airings that explain the difference, with per-file membership on the boundary day 2020-05-18
(missing rows from the 11-20 file) and ov/pdur (duplication inflation if the day is in both files).
Usage: python results/oc/check_truth_from_file.py"""
import sys, time
from collections import Counter
import numpy as np
import pandas as pd

EPOCH = pd.Timestamp('2020-03-09')
t0 = time.time()
v = pd.read_csv('data/dataset11-30.csv', dtype={'user_id': np.uint64})
users = np.random.RandomState(0).choice(np.sort(v.user_id.unique()), 300, replace=False)
v = v[v.user_id.isin(set(users))].copy()
v['vs'], v['ve'] = pd.to_datetime(v.start_time), pd.to_datetime(v.stop_time)
print(f'[views] sampled users: {len(users)}, last stop {v.ve.max()} (week-31 rows in the file '
      f'can matter only if this reaches 2020-07-27)')

s = pd.read_csv('data/export_arh_21-30-final.csv', low_memory=False)
s = s[s.tv_show_id != 0].copy()
s['ts'] = pd.to_datetime(s.start_time, format='%d.%m.%Y %H:%M:%S')
s['te'] = s.ts + pd.to_timedelta(s.duration, unit='s')
print(f'[file] export_arh_21-30-final.csv labelled rows: {len(s)}, span {s.ts.min()} .. {s.te.max()}')
v = v[v.ve >= s.ts.min()]
S = s[['channel_id', 'ts', 'te', 'duration', 'tv_show_id']]
parts = []
for u, g in v.groupby('user_id'):
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
print(f'[file-only] {len(mine)} of 300 users have a full top-5; {time.time()-t0:.0f} s')

sys.path.insert(0, 'src')
from common import load, make_truth
import common
j, sch, sub = load()
truth = make_truth(j[j.week.isin(range(21, 31))])
code = {int(r): i for i, r in enumerate(common.IDS)}
theirs = {u: truth[code[u]] for u in map(int, users) if u in code and code[u] in truth}
same = sum(mine.get(u) == theirs.get(u) for u in set(mine) | set(theirs))
print(f'[src] users with a full top-5: {len(theirs)}')
print(f'[compare] identical top-5 lists: {same} of {len(set(mine) | set(theirs))}')
diffs = [u for u in sorted(set(mine) | set(theirs)) if mine.get(u) != theirs.get(u)]
print(f'[compare] differing users: {len(diffs)}')
for u in diffs[:5]:
    print('  DIFF', u, 'file-only', mine.get(u), 'src', theirs.get(u))

# ---- why: boundary-day accounting, then the first DIFF user's 2020-05-18 airings
f1 = pd.read_csv('data/export_arh_11-20-final.csv', low_memory=False)
f1 = f1[f1.tv_show_id != 0].copy()
f1['ts'] = pd.to_datetime(f1.start_time, format='%d.%m.%Y %H:%M:%S')
day = pd.Timestamp('2020-05-18').date()
b1, b2 = f1[f1.ts.dt.date == day], s[s.ts.dt.date == day]
c1, c2 = Counter(zip(b1.channel_id, b1.ts)), Counter(zip(b2.channel_id, b2.ts))
print(f'[boundary 2020-05-18] labelled airings: in 11-20 file {len(b1)}, in 21-30 file {len(b2)}, '
      f'keys in both {len(set(c1) & set(c2))}, keys only in 11-20 {len(set(c1) - set(c2))}, '
      f'keys only in 21-30 {len(set(c2) - set(c1))}')
titles = sch.drop_duplicates(['channel_id', 'ts']).set_index(['channel_id', 'ts']).tv_show_title
f3 = pd.read_csv('data/export_arh_31-42-final.csv', low_memory=False)
f3 = f3[f3.tv_show_id != 0].copy()
f3['ts'] = pd.to_datetime(f3.start_time, format='%d.%m.%Y %H:%M:%S')
day2 = pd.Timestamp('2020-07-27').date()
d2, d3 = s[s.ts.dt.date == day2], f3[f3.ts.dt.date == day2]
e2, e3 = Counter(zip(d2.channel_id, d2.ts)), Counter(zip(d3.channel_id, d3.ts))
print(f'[boundary 2020-07-27] labelled airings: in 21-30 file {len(d2)}, in 31-42 file {len(d3)}, '
      f'keys in both {len(set(e2) & set(e3))}, keys only in 21-30 {len(set(e2) - set(e3))}, '
      f'keys only in 31-42 {len(set(e3) - set(e2))}')
if diffs:
    u = diffs[0]
    uc = code[u]  # join.pkl user_id is the dense code from common.load(), not the raw id
    ju = j[(j.user_id == uc) & j.week.isin(range(21, 31)) & (j.ov >= 0.8 * j.pdur)].copy()
    ju['start'] = pd.to_datetime(ju.ts, unit='s', origin=EPOCH)
    bd = ju[ju.start.dt.date == day].sort_values('ts')
    print(f'[why] user {u}: {len(bd)} qualifying airing(s) start on 2020-05-18 (in src truth only if the '
          f'airing sits in the 11-20 file):')
    for _, r in bd.iterrows():
        k = (r.channel_id, r.start)
        print(f'    ts={int(r.ts)} start={r.start} show={int(r.tv_show_id)} '
              f'title={titles.get(k, "?")} pdur={int(r.pdur)} ov={int(r.ov)} '
              f'ov/pdur={r.ov / r.pdur:.4f} copies in 11-20 file={c1.get(k, 0)} in 21-30 file={c2.get(k, 0)}')
    cnt_src = ju.groupby('tv_show_id').size().rename('src')
    cnt_fil = a[a.user_id == u].groupby('tv_show_id').size().rename('file_only')
    cmp = pd.concat([cnt_src, cnt_fil], axis=1).fillna(0).astype(int)
    cmp = cmp[cmp.src != cmp.file_only]
    print(f'[why] user {u}: programmes whose airing count differs (src vs file-only):')
    for sid, r in cmp.iterrows():
        has518 = int((ju[ju.tv_show_id == sid].start.dt.date == day).sum())
        print(f'    show {sid}: src n={r.src}, file-only n={r.file_only}, of which qualifying 05-18 airings: {has518}')
