"""Does a model trained on SHORT history features transfer to LONGER history at inference?
(The final model is trained with 10-week history and must score the test with up to 20 weeks.)
Train on 5-week history (weeks 16-20) features, then score held-out users with
 (a) matched 5-week history features, (b) 10-week history features (weeks 11-20).
Same truth (weeks 21-30), same user folds."""
import sys, os, time
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from ranker import get_frame, train_lgb, evaluate, log
from features import feat_cols

t0 = time.time()
S1, truth, sub_users, all_users, pop = get_frame()
H5, _, _, _, pop5 = get_frame(hist=range(16, 21), cache='cache/feat_H5.pkl', users=all_users)
F = [c for c in feat_cols(S1) if c in H5.columns]
users = np.sort(S1.user_id.unique())
fold_of = pd.Series(np.random.RandomState(0).randint(0, 3, len(users)), index=users)
for norm in (False, True):
    feats = F if not norm else [c for c in F if c not in __import__('ranker').RAW_COUNTS]
    sa = np.zeros(len(H5)); sb = np.zeros(len(S1))
    fa = fold_of.reindex(H5.user_id.values).values; fb = fold_of.reindex(S1.user_id.values).values
    for k in range(3):
        m = train_lgb(H5[fa != k], feats, objective='binary')
        sa[fa == k] = m.predict(H5[fa == k][feats])
        sb[fb == k] = m.predict(S1[fb == k][feats])
    tag = 'normalised feats' if norm else 'all feats'
    ma = evaluate(H5, sa, truth, sub_users, all_users, pop5)
    mb = evaluate(S1, sb, truth, sub_users, all_users, pop)
    log(25 + 2 * norm, f'train 5w-history, infer 5w-history ({tag})', *ma, time.time() - t0)
    log(26 + 2 * norm, f'train 5w-history, infer 10w-history ({tag})', *mb, time.time() - t0)
