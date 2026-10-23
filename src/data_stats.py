"""Data accounting numbers quoted in the report (written to results/data_stats.txt)."""
import sys, os
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import load, split, week_of
from ranker import get_frame
out = []
P = lambda *a: out.append(' '.join(str(x) for x in a))
j, s, sub = load()
v = pd.read_pickle('cache/views.pkl')
P('view rows', len(v), 'users in log', v.user_id.nunique(), 'channels in log', v.vsetv_id.nunique())
P('view duration median s', int((v.ve - v.vs).median()), 'max s', int((v.ve - v.vs).max()))
for p in ('tr1', 'tr2', 'test'):
    x = s[s.part == p]
    P('schedule', p, 'rows', len(x), 'labelled', int((x.tv_show_id != 0).sum()), 'share', round((x.tv_show_id != 0).mean(), 4))
P('joined user-airing rows (overlap>0, labelled)', len(j), 'users', j.user_id.nunique(), 'programmes', j.tv_show_id.nunique())
hi = j.ov >= 0.8 * j.pdur
P('rows with screen time >= 0.8', int(hi.sum()), 'share', round(hi.mean(), 4))
P('test users', len(sub), 'with labelled history', int(sub.user_id.isin(set(j.user_id)).sum()))
h, truth, ts = split(j, s, range(11, 21), range(21, 31))
su = [u for u in sub.user_id if u in truth]
P('hold-out users with full top-5 in weeks 21-30', len(truth), 'of them test users', len(su))
P('candidate programmes airing in weeks 21-30', ts.tv_show_id.nunique())
lab = s[s.tv_show_id != 0].assign(week=lambda d: week_of(d.ts))
te = lab[lab.week >= 31]
old = set(lab[lab.week <= 30].tv_show_id)
P('candidate programmes airing in weeks 31-42', te[te.week <= 42].tv_show_id.nunique(),
  'airings with an id never seen in weeks 11-30', int((~te.tv_show_id.isin(old)).sum()), 'of', len(te))
df = get_frame()[0]
P('hold-out ranker frame rows', len(df), 'users', df.user_id.nunique(), 'mean candidates/user', round(len(df) / df.user_id.nunique(), 1))
rec = df[df.user_id.isin(set(su))].groupby('user_id').label.apply(lambda x: (x > 0).sum() / 5).mean()
P('candidate recall of the true top-5 (test users)', round(rec, 4))
open('results/data_stats.txt', 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
