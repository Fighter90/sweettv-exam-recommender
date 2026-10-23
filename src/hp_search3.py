"""Attempts 93+: hybrid ranker with full-pair PPR (alpha 0.5/0.7) and personal-frequency(>=0.5) features.
Same protocol as ranker.py (3-fold user CV on 11-20 -> 21-30; extra temporal splits for training only)."""
import sys, os, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ranker import get_frame, cv_scores, evaluate, log
from features import feat_cols

df, truth, sub_users, all_users, pop = get_frame()
spl = {'S2': (range(11, 25), range(25, 31)), 'S3': (range(11, 18), range(18, 25)),
       'S4': (range(11, 23), range(23, 31))}
FR = {n: get_frame(*spl[n], cache=f'cache/feat_{n}.pkl')[0] for n in spl}
F = feat_cols(df)
TOPN = [c for c in F if c.split('_')[0] in ('ppr', 'als', 'ar', 'cbf')]
X23, X234 = (FR['S2'], FR['S3']), (FR['S2'], FR['S3'], FR['S4'])
B = dict(objective='binary', params={'num_leaves': 31})
P = lambda **kw: dict(B, params={**B['params'], **kw})
EXPS = {
    93: ('binary L31 S1+S2+S3 + PPR(0.5,0.7)/freq50 pair features', dict(B, extra=X23)),
    94: ('as 93 + S4', dict(B, extra=X234)),
    95: ('as 93, 5 seeds', dict(B, extra=X23, seeds=(1, 2, 3, 4, 5))),
    96: ('lambdarank + PPR pair features, S1+S2+S3', dict(objective='lambdarank', extra=X23)),
    97: ('regression log1p(count) + PPR pair features', dict(objective='regression', label='logcnt', extra=X23)),
    98: ('xendcg + PPR pair features', dict(objective='rank_xendcg', extra=X23)),
    99: ('binary L15 + PPR pair features', dict(objective='binary', params={'num_leaves': 15}, extra=X23)),
    100: ('binary L63 + PPR pair features', dict(objective='binary', extra=X23)),
    101: ('binary L31 lr=0.03 rounds=700 + PPR pair features', dict(P(learning_rate=0.03), rounds=700, extra=X23)),
    102: ('binary L31 min_leaf=100 + PPR pair features', dict(P(min_data_in_leaf=100), extra=X23)),
    103: ('binary L31 feature_fraction=0.6 + PPR pair features', dict(P(feature_fraction=0.6), extra=X23)),
    104: ('binary L31 without top-N generator columns (keeps PPR pair features)', dict(B, extra=X23, feats=[c for c in F if c not in TOPN])),
    105: ('binary L31 tie-aware positives + PPR pair features', dict(B, extra=X23, label='tie')),
    106: ('binary L31 S1+S2+S3 + weekly lag features (lag0-9, slope, run)', dict(B, extra=X23)),
    107: ('as 106, 5 seeds', dict(B, extra=X23, seeds=(1, 2, 3, 4, 5))),
    108: ('regression log1p(count) + lag features', dict(objective='regression', label='logcnt', extra=X23)),
    109: ('binary L63 + lag features', dict(objective='binary', extra=X23)),
    110: ('binary L31 + lag features, S1+S2+S3+S4', dict(B, extra=X234)),
    121: ('binary L31 lr=0.03 rounds=700 + lag features, 3 seeds', dict(P(learning_rate=0.03), rounds=700, extra=X23, seeds=(1, 2, 3))),
    122: ('regression log1p(count) L31 + lag features, 3 seeds', dict(objective='regression', label='logcnt', params={'num_leaves': 31}, extra=X23, seeds=(1, 2, 3))),
}

if __name__ == '__main__':
    for a in map(int, sys.argv[1:]):
        name, kw = EXPS[a]
        kw = dict(kw)
        feats = kw.pop('feats', F)
        t1 = time.time()
        sc = cv_scores(df, feats, **kw)
        np.save(f'cache/oof_{a}.npy', sc)
        log(a, name, *evaluate(df, sc, truth, sub_users, all_users, pop), time.time() - t1)
