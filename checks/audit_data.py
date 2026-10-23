"""Audit of the raw competition files, independent of src/ (only pandas on the CSVs).
Prints file hashes, sizes, the view log and schedule shape, the share of unlabelled airtime
(tv_show_id = 0) and the template's users. Usage: python checks/audit_data.py [data_dir]"""
import sys, hashlib, os, time
import numpy as np
import pandas as pd

D = sys.argv[1] if len(sys.argv) > 1 else 'data'
EXPECTED = {  # sha1 of the files inside sweettv-tv-program-recommender.zip (Kaggle, downloaded 2026-10-22)
    'dataset11-30.csv': 'a8f7e96ca42b7f012b4658c286bf46ede77358e7',
    'export_arh_11-20-final.csv': '08d86cb22074d3138687547715b13e770d9ef045',
    'export_arh_21-30-final.csv': 'e3fe8351fbe6894f46a9b0e091ae35f9e4ae3de4',
    'export_arh_31-42-final.csv': '487c3aa6337c529975e032b90cba3788766d4852',
    'submission.csv': '266b0a3c87fab62fab0b0ffa5b898da643272701',
}
t0 = time.time()
print('[files]')
for f, want in EXPECTED.items():
    h = hashlib.sha1(open(os.path.join(D, f), 'rb').read()).hexdigest()
    print(f'  {f:28s} {os.path.getsize(os.path.join(D, f)):>11,d} bytes  sha1 {h}  expected: {h == want}')

v = pd.read_csv(f'{D}/dataset11-30.csv', dtype={'user_id': np.uint64})
st, sp = pd.to_datetime(v.start_time), pd.to_datetime(v.stop_time)
print('[views] dataset11-30.csv')
print(f'  rows {len(v):,}  users {v.user_id.nunique():,}  channels {v.vsetv_id.nunique()}')
print(f'  first start {st.min()}  last stop {sp.max()}')
dur = (sp - st).dt.total_seconds()
print(f'  duration column name: {"duraton" if "duraton" in v.columns else "?"} (sic); '
      f'equals stop-start on {(dur == v.duraton).mean():.4%} of rows; median {int(dur.median())} s, max {int(dur.max())} s')
wk = 11 + ((st - pd.Timestamp("2020-03-09")).dt.days // 7)
print(f'  ISO weeks covered: {wk.min()}..{wk.max()} (week 11 starts Monday 2020-03-09)')

print('[schedule]')
for f in ('export_arh_11-20-final.csv', 'export_arh_21-30-final.csv', 'export_arh_31-42-final.csv'):
    s = pd.read_csv(f'{D}/{f}', low_memory=False)
    t = pd.to_datetime(s.start_time, format='%d.%m.%Y %H:%M:%S')
    lab = s.tv_show_id != 0
    print(f'  {f}: rows {len(s):,}  from {t.min().date()} to {t.max().date()}  channels {s.channel_id.nunique()}  '
          f'labelled (tv_show_id != 0) {lab.sum():,} = {lab.mean():.2%}  distinct ids {s.tv_show_id[lab].nunique():,}  '
          f'airtime labelled {s.duration[lab].sum() / s.duration.sum():.2%}')

sub = pd.read_csv(f'{D}/submission.csv', dtype={'user_id': np.uint64})
print('[template] submission.csv')
print(f'  rows {len(sub)}  unique users {sub.user_id.nunique()}  all rows "0 0 0 0 0": {(sub.tv_show_id == "0 0 0 0 0").all()}')
print(f'  template users present in the view log: {sub.user_id.isin(set(v.user_id)).sum()} of {len(sub)}')
print(f'[time] {time.time() - t0:.0f} s')
