"""LightGBM learning-to-rank hybrid on the temporal hold-out (history weeks 11-20 -> truth weeks 21-30).

Protocol: 3-fold cross-validation BY USER over all 4030 users who have a full top-5 in weeks 21-30.
Each fold trains on the other users' (history features, weeks 21-30 labels) and scores held-out users.
Reported: MAP@5 on the 1150 test users (same set as the single-method attempts) and on all 4030 users.
History features never include the scored user's weeks 21-30 views."""
import sys, os, time
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import load, split, mapk, pad
import methods as M
from features import build, add_labels, feat_cols

HIST, TGT = range(11, 21), range(21, 31)
RAW_COUNTS = ['n_any', 'n_hi', 'n_half', 'ov_sum', 'w2', 'w4', 'w8', 'n_weeks', 'n_hi_weeks', 'air_t',
              'air_t_sec', 'air_h', 'pop_hi', 'pop_users', 'u_hi', 'u_rows', 'u_weeks', 'exp_hi',
              'since_hi', 'since_any', 'hi_l2', 'hi_l4', 'pop_hi_l4']


def get_frame(hist=HIST, tgt=TGT, cache='cache/feat_S1.pkl', users=None):
    j, s, sub = load()
    h, truth, tsched = split(j, s, hist, tgt)
    subu = set(sub.user_id)
    all_users = list(truth) if users is None else users
    if os.path.exists(cache):
        df = pd.read_pickle(cache)
    else:
        items = M.item_content(s)
        df = build(h, s, hist, tgt, all_users, items)
        df = add_labels(df, truth)
        df.to_pickle(cache)
    if 'cnt' not in df.columns:
        t = j[j.week.isin(list(tgt)) & (j.ov >= 0.8 * j.pdur)]
        cnt = t.groupby(['user_id', 'tv_show_id']).size().rename('cnt').reset_index()
        df = df.merge(cnt, on=['user_id', 'tv_show_id'], how='left')
        df['cnt'] = df.cnt.fillna(0).astype(np.float32)
        df.to_pickle(cache)
    if 'slot_sum' not in df.columns:
        from common import load_views
        from features import slot_features
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
    pop = M.popularity(h, set(tsched.tv_show_id), all_users)
    sub_users = [u for u in sub.user_id if u in truth]
    return df, truth, sub_users, all_users, pop


def predict_topk(df, score, users, pop, k=5):
    d = df[['user_id', 'tv_show_id']].assign(score=score)
    d = d.sort_values(['user_id', 'score'], ascending=[True, False])
    pr = d.groupby('user_id').tv_show_id.apply(lambda x: list(x[:k])).to_dict()
    return pad(pr, users, pop)


def train_lgb(tr, feats, params=None, rounds=400, objective='lambdarank', seed=42, label='graded'):
    import lightgbm as lgb
    tr = tr.sort_values('user_id', kind='stable')
    grp = tr.groupby('user_id', sort=False).size().values
    p = dict(objective=objective, learning_rate=0.05, num_leaves=63, min_data_in_leaf=50,
             feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
             verbose=-1, seed=seed, num_threads=4)
    if objective in ('lambdarank', 'rank_xendcg'):
        p.update(lambdarank_truncation_level=20)
    if params:
        p.update(params)
    y = tr.label.values
    if objective == 'binary' or label == 'binary':
        y = (y > 0).astype(int)
    if label == 'cnt':
        y = tr.cnt.values
    if label == 'tie':        # positive = count >= the user's 5th-largest count (keeps tied items too)
        thr = tr[tr.label > 0].groupby('user_id').cnt.min()
        t = tr.user_id.map(thr).values
        y = ((tr.cnt.values >= t) & (tr.cnt.values > 0)).astype(int)
    if label == 'logcnt':
        y = np.log1p(tr.cnt.values)
    if label == 'cnt_rank':   # graded: 0 none, 1 watched >=1, 2..6 = top-5 position (5->6)
        y = np.where(tr.label.values > 0, tr.label.values + 1, (tr.cnt.values > 0).astype(int))
    ds = lgb.Dataset(tr[feats], y, group=None if objective in ('binary', 'regression') else grp)
    return lgb.train(p, ds, num_boost_round=rounds)


def cv_scores(df, feats, folds=3, seeds=(42,), extra=(), **kw):
    """Out-of-fold scores for every row of df (user-grouped folds). `extra` = additional training frames
    (other temporal splits); rows of held-out-fold users are removed from them too."""
    users = np.sort(df.user_id.unique())
    rng = np.random.RandomState(0)
    fold_of = pd.Series(rng.randint(0, folds, len(users)), index=users)
    f = fold_of.loc[df.user_id.values].values
    out = np.zeros(len(df))
    for k in range(folds):
        tr, te = df[f != k], df[f == k]
        held = set(users[fold_of.values == k])
        if extra:
            tr = pd.concat([tr] + [e[~e.user_id.isin(held)].assign(user_id=lambda d: d.user_id + (i + 1) * 10**7)
                                   for i, e in enumerate(extra)], ignore_index=True)
        for sd in seeds:
            m = train_lgb(tr, feats, seed=sd, **kw)
            p = m.predict(te[feats])
            # rank-average across seeds so different score scales mix fairly
            out[f == k] += pd.Series(p).groupby(te.user_id.values).rank(pct=True).values
    return out


def evaluate(df, score, truth, sub_users, all_users, pop):
    m_sub = mapk(truth, predict_topk(df[df.user_id.isin(set(sub_users))],
                                     score[df.user_id.isin(set(sub_users)).values], sub_users, pop), sub_users)
    m_all = mapk(truth, predict_topk(df, score, all_users, pop), all_users)
    return m_sub, m_all


def log(aid, name, m_sub, m_all, dt):
    os.makedirs('results', exist_ok=True)
    with open('results/attempts.csv', 'a') as fh:
        fh.write(f'{aid},"{name}",{m_sub:.5f},{dt:.1f},{m_all:.5f}\n')
    print(f'#{aid:>3} sub={m_sub:.5f} all={m_all:.5f} {dt:6.1f}s  {name}', flush=True)


if __name__ == '__main__':
    t0 = time.time()
    df, truth, sub_users, all_users, pop = get_frame()
    F = feat_cols(df)
    rec = df[df.user_id.isin(set(sub_users))].groupby('user_id').label.apply(lambda x: (x > 0).sum() / 5).mean()
    print('frame', df.shape, 'recall(sub)', round(rec, 4), f'{time.time()-t0:.0f}s')
    exps = {
        11: ('LGB lambdarank, all features, graded label', F, {}),
        12: ('LGB binary objective, all features', F, {'objective': 'binary'}),
        13: ('LGB lambdarank, length-normalised features only', [c for c in F if c not in RAW_COUNTS], {}),
        14: ('LGB lambdarank, no generator features (history+schedule only)',
             [c for c in F if not c.split('_')[0] in ('ppr', 'als', 'ar', 'cbf')], {}),
        15: ('LGB lambdarank, binary relevance label', F, {'label': 'binary'}),
        16: ('LGB lambdarank, leaves=31 lr=0.03 rounds=800', F, {'params': {'num_leaves': 31, 'learning_rate': 0.03}, 'rounds': 800}),
        17: ('LGB lambdarank, leaves=127 min_leaf=100', F, {'params': {'num_leaves': 127, 'min_data_in_leaf': 100}}),
        18: ('LGB rank_xendcg', F, {'objective': 'rank_xendcg'}),
        19: ('LGB poisson regression on target high-screen count', F, {'objective': 'poisson', 'label': 'cnt'}),
        20: ('LGB L2 regression on log1p(count)', F, {'objective': 'regression', 'label': 'logcnt'}),
        21: ('LGB lambdarank, graded label (watched + top-5 position)', F, {'label': 'cnt_rank'}),
        22: ('LGB binary, 3 seeds rank-averaged', F, {'objective': 'binary', 'seeds': (1, 2, 3)}),
        23: ('LGB binary + habit (channel x weekday x hour occupancy) features', F, {'objective': 'binary'}),
        24: ('LGB lambdarank + habit features', F, {}),
        29: ('LGB binary + stickiness/recent-catch/near-term-airing features', F, {'objective': 'binary'}),
        30: ('LGB xendcg + extra features', F, {'objective': 'rank_xendcg'}),
    }
    def frames(*names):
        spl = {'S2': (range(11, 25), range(25, 31)), 'S3': (range(11, 18), range(18, 25)),
               'S4': (range(11, 23), range(23, 31))}
        return tuple(get_frame(*spl[n], cache=f'cache/feat_{n}.pkl')[0] for n in names)
    for a in sys.argv[1:]:
        a = int(a)
        if a == 31:
            exps[31] = ('LGB binary, train S1 + S2 (hist 11-24 -> 25-30)', F, {'objective': 'binary', 'extra': frames('S2')})
        if a == 32:
            exps[32] = ('LGB binary, train S1 + S2 + S3 (hist 11-17 -> 18-24)', F, {'objective': 'binary', 'extra': frames('S2', 'S3')})
        if a == 33:
            exps[33] = ('LGB binary, train S1 + S4 (hist 11-22 -> 23-30)', F, {'objective': 'binary', 'extra': frames('S4')})
        name, feats, kw = exps[a]
        t1 = time.time()
        sc = cv_scores(df, feats, **kw)
        ms, ma = evaluate(df, sc, truth, sub_users, all_users, pop)
        log(a, name, ms, ma, time.time() - t1)
