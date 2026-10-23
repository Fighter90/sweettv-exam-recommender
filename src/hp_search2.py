"""Attempts 56+: candidate pool size, tie-aware labels, more temporal splits, seed bagging, DART,
within-user percentile features. Same protocol as ranker.py / hp_search.py."""
import sys, os, time
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from ranker import get_frame, cv_scores, evaluate, log
from features import feat_cols

df, truth, sub_users, all_users, pop = get_frame()
spl = {'S2': (range(11, 25), range(25, 31)), 'S3': (range(11, 18), range(18, 25)),
       'S4': (range(11, 23), range(23, 31))}
FR = {n: get_frame(*spl[n], cache=f'cache/feat_{n}.pkl')[0] for n in spl}
PCT = ['n_hi', 'n_any', 'w4', 'w2', 'exp_hi', 'slot_both_sum', 'hi_slot_sum', 'ppr_score', 'als_score',
       'catch', 'exp_l4_t', 'ov_sum', 'air_t', 'pop_hi_l4', 'ch_aff', 'hr_aff']


def add_pct(d):
    for c in PCT:
        d[c + '_upct'] = d.groupby('user_id')[c].rank(pct=True)
        d[c + '_umax'] = d[c] / (d.groupby('user_id')[c].transform('max') + 1e-9)
    return d


F = feat_cols(df)
X23 = (FR['S2'], FR['S3'])
X234 = (FR['S2'], FR['S3'], FR['S4'])
B = dict(objective='binary', params={'num_leaves': 31})
EXPS = {
    56: ('binary L31, S1+S2+S3, tie-aware positives', lambda: dict(B, extra=X23, label='tie')),
    57: ('binary L31, S1+S2+S3+S4', lambda: dict(B, extra=X234)),
    58: ('binary L31, S1+S2+S3, 5 seeds', lambda: dict(B, extra=X23, seeds=(1, 2, 3, 4, 5))),
    59: ('binary L31 DART 300 rounds, S1+S2+S3', lambda: dict(objective='binary', extra=X23, rounds=300,
         params={'num_leaves': 31, 'boosting': 'dart', 'drop_rate': 0.1})),
    60: ('binary L31 + within-user percentile features, S1+S2+S3', 'pct'),
}

if __name__ == '__main__':
    for a in map(int, sys.argv[1:]):
        name, mk = EXPS[a]
        t1 = time.time()
        if mk == 'pct':
            d0 = add_pct(df.copy())
            ex = tuple(add_pct(FR[n].copy()) for n in ('S2', 'S3'))
            feats = F + [c for c in d0.columns if c.endswith('_upct') or c.endswith('_umax')]
            sc = cv_scores(d0, feats, **dict(B, extra=ex))
        else:
            sc = cv_scores(df, F, **mk())
        np.save(f'cache/oof_{a}.npy', sc)
        log(a, name, *evaluate(df, sc, truth, sub_users, all_users, pop), time.time() - t1)
