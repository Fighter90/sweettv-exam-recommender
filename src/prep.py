"""Load raw SweetTV files, join the view log to the labelled schedule, cache to pickle.

Join rule: same channel (vsetv_id == channel_id) and overlapping time intervals.
For every (view, programme) pair we keep the overlap in seconds and the programme
duration, so the "watched" threshold can be chosen later without re-joining.
Rows with tv_show_id == 0 are unlabelled airtime and are dropped before the join.
"""
import sys, time
import numpy as np
import pandas as pd

D = sys.argv[1] if len(sys.argv) > 1 else 'data'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'cache'
EPOCH = pd.Timestamp('2020-03-09')  # Monday of ISO week 11


def load_sched(name):
    s = pd.read_csv(f'{D}/{name}', dtype={'channel_id': np.int32, 'tv_show_id': np.int64,
                                          'duration': np.int64}, low_memory=False)
    s['ts'] = ((pd.to_datetime(s['start_time'], format='%d.%m.%Y %H:%M:%S') - EPOCH)
               .dt.total_seconds().astype(np.int64))
    s['te'] = s['ts'] + s['duration']
    return s


def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    sched = []
    for part, name in [('tr1', 'export_arh_11-20-final.csv'), ('tr2', 'export_arh_21-30-final.csv'),
                       ('test', 'export_arh_31-42-final.csv')]:
        s = load_sched(name)
        s['part'] = part
        sched.append(s)
        print(name, len(s), 'labelled', int((s.tv_show_id != 0).sum()), f'{time.time()-t0:.1f}s', flush=True)
    sched = pd.concat(sched, ignore_index=True)
    sched.to_pickle(f'{OUT}/sched_all.pkl')
    lab = sched[sched.tv_show_id != 0].copy()

    v = pd.read_csv(f'{D}/dataset11-30.csv', dtype={'user_id': np.uint64, 'vsetv_id': np.int32,
                                                    'duraton': np.int64})
    v['vs'] = ((pd.to_datetime(v['start_time']) - EPOCH).dt.total_seconds().astype(np.int64))
    v['ve'] = ((pd.to_datetime(v['stop_time']) - EPOCH).dt.total_seconds().astype(np.int64))
    v = v[['user_id', 'vsetv_id', 'vs', 've']]
    v.to_pickle(f'{OUT}/views.pkl')
    print('views', len(v), 'users', v.user_id.nunique(), f'{time.time()-t0:.1f}s', flush=True)

    # interval join per channel
    out = []
    lab = lab.sort_values(['channel_id', 'ts'])
    for ch, g in v.groupby('vsetv_id', sort=False):
        p = lab[lab.channel_id == ch]
        if len(p) == 0:
            continue
        ps, pe = p.ts.values, p.te.values
        # schedule rows within a channel may overlap slightly; use running max of end for the lower bound
        pe_max = np.maximum.accumulate(pe)
        vs, ve = g.vs.values, g.ve.values
        lo = np.searchsorted(pe_max, vs, 'right')
        hi = np.searchsorted(ps, ve, 'left')
        n = np.maximum(hi - lo, 0)
        if n.sum() == 0:
            continue
        vi = np.repeat(np.arange(len(g)), n)
        pi = np.concatenate([np.arange(a, b) for a, b in zip(lo[n > 0], hi[n > 0])])
        ov = np.minimum(ve[vi], pe[pi]) - np.maximum(vs[vi], ps[pi])
        m = ov > 0
        vi, pi, ov = vi[m], pi[m], ov[m]
        out.append(pd.DataFrame({'user_id': g.user_id.values[vi], 'channel_id': ch,
                                 'tv_show_id': p.tv_show_id.values[pi], 'ts': ps[pi],
                                 'pdur': (pe - ps)[pi], 'ov': ov}))
    j = pd.concat(out, ignore_index=True)
    # one row per (user, airing): sum overlap of several view fragments of the same airing
    j = j.groupby(['user_id', 'channel_id', 'tv_show_id', 'ts', 'pdur'], as_index=False)['ov'].sum()
    j['week'] = 11 + j.ts // (7 * 86400)
    j.to_pickle(f'{OUT}/join.pkl')
    print('join rows', len(j), 'users', j.user_id.nunique(), 'shows', j.tv_show_id.nunique(),
          f'{time.time()-t0:.1f}s', flush=True)


if __name__ == '__main__':
    main()
