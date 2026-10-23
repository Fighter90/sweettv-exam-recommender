"""Recommendation methods. Each returns a DataFrame [user_id, tv_show_id, score] restricted to the
candidate pool (labelled programmes airing in the target window). Repeats of already-watched
programmes are allowed for every method (the official truth counts repeat viewing)."""
import numpy as np
import pandas as pd
import scipy.sparse as sp

HIGH = 0.8  # screen-time threshold of the official truth


def hits(h, thr=HIGH):
    """History airings that count as 'watched' under the official rule."""
    return h[h.ov >= thr * h.pdur]


def popularity(h, cand, users, by='hits'):
    """Baseline: same ranked list for everyone. Popularity = number of high-screen airings."""
    hh = hits(h)
    hh = hh[hh.tv_show_id.isin(cand)]
    pop = hh.groupby('tv_show_id').size().sort_values(ascending=False)
    return list(pop.index)


def personal_freq(h, cand, half_life=None, last_week=None, thr=HIGH, weight_target=None):
    """User's own frequency of high-screen airings per programme, optional exponential recency decay,
    optional multiplication by the number of airings in the target window divided by history airings."""
    hh = h[h.ov >= thr * h.pdur]
    hh = hh[hh.tv_show_id.isin(cand)]
    w = np.ones(len(hh))
    if half_life:
        w = 0.5 ** ((last_week - hh.week.values) / half_life)
    sc = hh.assign(score=w).groupby(['user_id', 'tv_show_id']).score.sum().reset_index()
    if weight_target is not None:
        sc['score'] *= sc.tv_show_id.map(weight_target).fillna(1.0).values
    return sc


def interaction_matrix(h, thr=HIGH, value='count'):
    hh = h[h.ov >= thr * h.pdur]
    c = hh.groupby(['user_id', 'tv_show_id']).size().rename('n').reset_index()
    uids = np.sort(c.user_id.unique())
    iids = np.sort(c.tv_show_id.unique())
    ui = np.searchsorted(uids, c.user_id.values)
    ii = np.searchsorted(iids, c.tv_show_id.values)
    v = c.n.values.astype(np.float32)
    if value == 'log':
        v = np.log1p(v)
    elif value == 'binary':
        v = np.ones_like(v)
    M = sp.csr_matrix((v, (ui, ii)), shape=(len(uids), len(iids)))
    return M, uids, iids


def _topn_dense(S, users_idx, uids, iids, cand_mask, n=50):
    rows = []
    for a in range(0, len(users_idx), 512):
        idx = users_idx[a:a + 512]
        block = np.asarray(S(idx))
        block[:, ~cand_mask] = -np.inf
        top = np.argpartition(-block, min(n, block.shape[1] - 1), axis=1)[:, :n]
        for r, u in enumerate(idx):
            t = top[r]
            sc = block[r, t]
            ok = np.isfinite(sc)
            rows.append(pd.DataFrame({'user_id': uids[u], 'tv_show_id': iids[t[ok]], 'score': sc[ok]}))
    return pd.concat(rows, ignore_index=True)


def als(h, cand, users, factors=64, reg=0.05, iters=20, alpha=10.0, value='log', seed=42, n=50):
    """Matrix factorisation for implicit feedback (Hu-Koren-Volinsky ALS via `implicit`).
    Confidence = 1 + alpha * value(user, programme)."""
    from implicit.als import AlternatingLeastSquares
    import threadpoolctl
    threadpoolctl.threadpool_limits(1, 'blas')
    M, uids, iids = interaction_matrix(h, value=value)
    model = AlternatingLeastSquares(factors=factors, regularization=reg, iterations=iters,
                                    random_state=seed, calculate_training_loss=False)
    model.fit((M * alpha).tocsr(), show_progress=False)
    U, V = model.user_factors, model.item_factors
    U = U.to_numpy() if hasattr(U, 'to_numpy') else np.asarray(U)
    V = V.to_numpy() if hasattr(V, 'to_numpy') else np.asarray(V)
    cand_mask = np.isin(iids, list(cand))
    uidx = np.where(np.isin(uids, list(users)))[0]
    return _topn_dense(lambda idx: U[idx] @ V.T, uidx, uids, iids, cand_mask, n)


def item_knn(h, cand, users, n=50, shrink=10.0, value='log'):
    """Item-based CF (cosine on user-programme matrix), score = sum of similarities to the user's items."""
    M, uids, iids = interaction_matrix(h, value=value)
    norms = np.sqrt(np.asarray(M.multiply(M).sum(0))).ravel() + 1e-9
    C = (M.T @ M).toarray()
    S = C / (np.outer(norms, norms) + shrink)
    np.fill_diagonal(S, 0)
    cand_mask = np.isin(iids, list(cand))
    uidx = np.where(np.isin(uids, list(users)))[0]
    return _topn_dense(lambda idx: M[idx] @ S, uidx, uids, iids, cand_mask, n)


def ppr(h, cand, users, alpha=0.15, iters=20, n=50, value='log', self_weight=1.0):
    """Personalized PageRank on the bipartite user-programme graph, restart at the user's node.
    Computed with power iteration for all requested users at once (dense restart matrix)."""
    M, uids, iids = interaction_matrix(h, value=value)
    nu, ni = M.shape
    # row-stochastic transitions user->item and item->user
    Pu = sp.diags(1.0 / (np.asarray(M.sum(1)).ravel() + 1e-12)) @ M          # nu x ni
    MT = M.T.tocsr()
    Pi = sp.diags(1.0 / (np.asarray(MT.sum(1)).ravel() + 1e-12)) @ MT        # ni x nu
    uidx = np.where(np.isin(uids, list(users)))[0]
    # restart distribution on the user's own items (one step from the user node)
    R = Pu[uidx].toarray()                                                     # B x ni
    # two-hop item->item transition: item -> user -> item
    T = (Pi @ Pu).tocsr()                                                      # ni x ni
    x = R.copy()
    for _ in range(iters):
        x = alpha * R + (1 - alpha) * (T.T @ x.T).T
    if self_weight != 1.0:
        x = x + (self_weight - 1.0) * alpha * R
    cand_mask = np.isin(iids, list(cand))
    X = np.asarray(x)
    order = {u: r for r, u in enumerate(uidx)}
    return _topn_dense(lambda idx: X[[order[i] for i in idx]], uidx, uids, iids, cand_mask, n)


def assoc_rules(h, cand, users, min_support=20, n=50, metric='confidence'):
    """Pairwise association rules A -> B over users' sets of watched programmes.
    Score(u, B) = max over A in history(u) of confidence(A -> B) (or lift)."""
    M, uids, iids = interaction_matrix(h, value='binary')
    sup = np.asarray(M.sum(0)).ravel()
    C = (M.T @ M).toarray().astype(np.float32)
    C[C < min_support] = 0
    np.fill_diagonal(C, 0)
    conf = C / (sup[:, None] + 1e-9)                       # P(B | A), rows = antecedent A
    if metric == 'lift':
        conf = conf / (sup[None, :] / M.shape[0] + 1e-9)
    cand_mask = np.isin(iids, list(cand))
    uidx = np.where(np.isin(uids, list(users)))[0]
    Mb = M.tocsr()

    def score(idx):
        out = np.zeros((len(idx), len(iids)), dtype=np.float32)
        for r, u in enumerate(idx):
            items = Mb.indices[Mb.indptr[u]:Mb.indptr[u + 1]]
            if len(items):
                out[r] = conf[items].max(0)
        return out
    return _topn_dense(score, uidx, uids, iids, cand_mask, n)


def item_content(sched):
    """Item attribute table from the schedule: category, genres, director, actors, channel."""
    lab = sched[sched.tv_show_id != 0]
    it = lab.groupby('tv_show_id').agg(cat=('tv_show_category', 'first'), g1=('tv_show_genre_1', 'first'),
                                       g2=('tv_show_genre_2', 'first'), g3=('tv_show_genre_3', 'first'),
                                       director=('director', 'first'), actors=('actors', 'first'),
                                       channel=('channel_id', lambda x: x.mode().iat[0]),
                                       title=('tv_show_title', 'first'))
    return it


def cbf(h, cand, users, items, n=50, weights=(1.0, 1.0, 0.5, 0.5, 1.0)):
    """Content-based filtering: TF-IDF item vectors from category, genres, director, actors and
    main channel; user profile = sum of watched item vectors weighted by log(1+count);
    score = cosine(profile, item)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize
    w_cat, w_gen, w_dir, w_act, w_ch = weights
    def toks(r):
        t = []
        t += [f"cat={r['cat']}"] if isinstance(r['cat'], str) else []
        for g in (r['g1'], r['g2'], r['g3']):
            if isinstance(g, str):
                t.append('gen=' + g)
        if isinstance(r['director'], str):
            t += ['dir=' + d.strip() for d in r['director'].split(',') if d.strip()]
        if isinstance(r['actors'], str):
            t += ['act=' + a.strip() for a in r['actors'].split(',')[:10] if a.strip()]
        t.append(f"ch={r['channel']}")
        return t
    docs = items.apply(toks, axis=1)
    vec = TfidfVectorizer(analyzer=lambda x: x, min_df=2, sublinear_tf=True)
    X = vec.fit_transform(docs.values)
    vocab = vec.get_feature_names_out()
    colw = np.array([w_cat if v.startswith('cat=') else w_gen if v.startswith('gen=') else
                     w_dir if v.startswith('dir=') else w_act if v.startswith('act=') else w_ch
                     for v in vocab])
    X = normalize(X @ sp.diags(colw))
    iids = items.index.values
    M, uids, miids = interaction_matrix(h, value='log')
    # map M columns to items rows
    pos = pd.Series(np.arange(len(iids)), index=iids)
    keep = np.isin(miids, iids)
    M = M[:, np.where(keep)[0]]
    cols = pos[miids[keep]].values
    P = M @ X[cols]                                     # user profiles
    P = normalize(P)
    cand_mask = np.isin(iids, list(cand))
    uidx = np.where(np.isin(uids, list(users)))[0]
    return _topn_dense(lambda idx: (P[idx] @ X.T).toarray(), uidx, uids, iids, cand_mask, n)
