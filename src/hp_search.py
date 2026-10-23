"""Attempts 34+: hyper-parameters, objectives and ensembles of the hybrid ranker.
All use the same protocol as ranker.py (3-fold user CV on the 11-20 -> 21-30 hold-out),
training on S1 + extra temporal splits S2 (11-24 -> 25-30) and S3 (11-17 -> 18-24)."""
import sys, os, time, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from ranker import get_frame, cv_scores, evaluate, log, RAW_COUNTS
from features import feat_cols

df, truth, sub_users, all_users, pop = get_frame()
spl = {'S2': (range(11, 25), range(25, 31)), 'S3': (range(11, 18), range(18, 25))}
EXTRA = tuple(get_frame(*spl[n], cache=f'cache/feat_{n}.pkl')[0] for n in ('S2', 'S3'))
F = feat_cols(df)
GEN = [c for c in F if c.split('_')[0] in ('ppr', 'als', 'ar', 'cbf')]

B = {'objective': 'binary', 'extra': EXTRA}
EXPS = {
    34: ('binary leaves=15', {**B, 'params': {'num_leaves': 15}}),
    35: ('binary leaves=31', {**B, 'params': {'num_leaves': 31}}),
    36: ('binary leaves=127', {**B, 'params': {'num_leaves': 127}}),
    37: ('binary leaves=31 lr=0.03 rounds=700', {**B, 'params': {'num_leaves': 31, 'learning_rate': 0.03}, 'rounds': 700}),
    38: ('binary leaves=63 min_leaf=200', {**B, 'params': {'min_data_in_leaf': 200}}),
    39: ('binary leaves=63 min_leaf=20', {**B, 'params': {'min_data_in_leaf': 20}}),
    40: ('binary feature_fraction=0.5', {**B, 'params': {'feature_fraction': 0.5}}),
    41: ('binary rounds=200', {**B, 'rounds': 200}),
    42: ('binary rounds=800 lr=0.03', {**B, 'rounds': 800, 'params': {'learning_rate': 0.03}}),
    43: ('binary lambda_l2=10', {**B, 'params': {'lambda_l2': 10.0}}),
    44: ('binary scale_pos_weight=5', {**B, 'params': {'scale_pos_weight': 5.0}}),
    45: ('binary bagging_fraction=0.5 feature_fraction=0.6', {**B, 'params': {'bagging_fraction': 0.5, 'feature_fraction': 0.6}}),
    46: ('xendcg, S1+S2+S3', {'objective': 'rank_xendcg', 'extra': EXTRA}),
    47: ('lambdarank, S1+S2+S3', {'objective': 'lambdarank', 'extra': EXTRA}),
    48: ('regression log1p(count), S1+S2+S3', {'objective': 'regression', 'label': 'logcnt', 'extra': EXTRA}),
    49: ('binary without generator features, S1+S2+S3', {**B, 'feats': [c for c in F if c not in GEN]}),
    50: ('binary without raw counts (normalised only), S1+S2+S3', {**B, 'feats': [c for c in F if c not in RAW_COUNTS]}),
}

if __name__ == '__main__':
    for a in map(int, sys.argv[1:]):
        name, kw = EXPS[a]
        kw = dict(kw)
        feats = kw.pop('feats', F)
        t1 = time.time()
        sc = cv_scores(df, feats, **kw)
        np.save(f'cache/oof_{a}.npy', sc)
        ms, ma = evaluate(df, sc, truth, sub_users, all_users, pop)
        log(a, name, ms, ma, time.time() - t1)
