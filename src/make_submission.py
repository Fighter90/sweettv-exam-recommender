"""Final pipeline: train the hybrid ranker on the hold-out frame (history 11-20 -> labels 21-30,
all 4030 users with a full top-5), then score the 1260 test users with features computed from the
full history (weeks 11-30) against the test-window schedule (weeks 31-42). No week 31-42 views exist
or are used. Users without any labelled history get the popularity list (same fallback as everywhere).
Usage: python src/make_submission.py <config> <out.csv>"""
import sys, os, time, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import load, load_views, pad
import methods as M
from features import build, slot_features, feat_cols
from ranker import get_frame, train_lgb, RAW_COUNTS

CONFIGS = {
    'bin3': dict(models=[dict(objective='binary', seed=s) for s in (1, 2, 3)]),
    'bin3_multi': dict(models=[dict(objective='binary', seed=s) for s in (1, 2, 3)], extra=('S2', 'S3')),
    # final: same components as hold-out attempt 123 (107 + 121 + 122), each a seed-bag, rank-averaged
    'final': dict(extra=('S2', 'S3'), components=[
        [dict(objective='binary', params={'num_leaves': 31}, seed=s) for s in (1, 2, 3, 4, 5)],
        [dict(objective='binary', params={'num_leaves': 31, 'learning_rate': 0.03}, rounds=700, seed=s) for s in (1, 2, 3)],
        [dict(objective='regression', label='logcnt', params={'num_leaves': 31}, seed=s) for s in (1, 2, 3)],
    ]),
}
SPL = {'S2': (range(11, 25), range(25, 31)), 'S3': (range(11, 18), range(18, 25)),
       'S4': (range(11, 23), range(23, 31))}


def test_frame(cache='cache/feat_TEST.pkl'):
    j, s, sub = load()
    hist, tgt = range(11, 31), range(31, 43)
    h = j[j.week.isin(hist)]
    users = list(sub.user_id)
    if os.path.exists(cache):
        df = pd.read_pickle(cache)
    else:
        df = build(h, s, hist, tgt, users, M.item_content(s))
        df = slot_features(df, load_views(), h, s, hist, tgt)
        df.to_pickle(cache)
    if 'stick_mean' not in df.columns:
        from features import extra_features
        df = extra_features(df, h, s, hist, tgt)
        df.to_pickle(cache)
    if 'ppr50' not in df.columns:
        from features import ppr_pair_features
        df = ppr_pair_features(df, h, alphas=(0.5, 0.7))
        df.to_pickle(cache)
    if 'lag_run' not in df.columns:
        from features import lag_features
        df = lag_features(df, h, list(hist))
        df.to_pickle(cache)
    SCH = s[s.tv_show_id != 0].assign(week=lambda d: 11 + d.ts // (7 * 86400))
    cand = set(SCH[SCH.week.isin(tgt)].tv_show_id)
    pop = M.popularity(h, cand, users)
    return df, sub, pop


def run(cfg_name, out, feats=None):
    t0 = time.time()
    tr, *_ = get_frame()
    cfg = CONFIGS[cfg_name]
    if cfg.get('extra'):
        ex = [get_frame(*SPL[n], cache=f'cache/feat_{n}.pkl')[0] for n in cfg['extra']]
        tr = pd.concat([tr] + [e.assign(user_id=e.user_id + (i + 1) * 10**7) for i, e in enumerate(ex)],
                       ignore_index=True)
    te, sub, pop = test_frame()
    F = feats or [c for c in feat_cols(tr) if c in te.columns]
    score = np.zeros(len(te))
    comps = cfg.get('components') or [cfg['models']]
    rk = lambda v: pd.Series(v).groupby(te.user_id.values).rank(pct=True).values
    for comp in comps:
        cs = np.zeros(len(te))
        for mp in comp:
            m = train_lgb(tr, F, **dict(mp))
            cs += rk(m.predict(te[F]))
        score += rk(cs) if len(comps) > 1 else cs
    np.save(out.replace('.csv', '_scores.npy'), score)
    d = te[['user_id', 'tv_show_id']].assign(score=score).sort_values(['user_id', 'score'], ascending=[True, False])
    pr = d.groupby('user_id').tv_show_id.apply(lambda x: list(x[:5])).to_dict()
    pr = pad(pr, list(sub.user_id), pop)
    rows = [(str(r), ' '.join(str(int(x)) for x in pr[u])) for u, r in zip(sub.user_id, sub.raw_id)]
    res = pd.DataFrame(rows, columns=['user_id', 'tv_show_id'])
    # sanity checks
    assert len(res) == 1260 and res.user_id.nunique() == 1260
    assert all(len(set(x.split())) == 5 and '0' not in x.split() for x in res.tv_show_id)
    res.to_csv(out, index=False)
    print('wrote', out, 'cold-start users padded:', sum(1 for u in sub.user_id if u not in set(te.user_id)),
          f'{time.time()-t0:.0f}s')


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
