"""Shared data access, temporal split and MAP@5 evaluator (same formula as Kaggle MAP@K)."""
import numpy as np
import pandas as pd

CACHE = 'cache'
K = 5


def apk(actual, predicted, k=K):
    """AP@k exactly as in the course slides / Kaggle ml_metrics: sum P@i*rel(i) / min(|R|, k)."""
    if not actual:
        return 0.0
    predicted = list(predicted)[:k]
    hits, s = 0, 0.0
    for i, p in enumerate(predicted):
        if p in actual and p not in predicted[:i]:
            hits += 1
            s += hits / (i + 1.0)
    return s / min(len(actual), k)


def mapk(truth, preds, users, k=K):
    """Mean over `users`; a user with an empty truth set contributes 0 (as Kaggle does)."""
    return float(np.mean([apk(set(truth.get(u, ())), preds.get(u, []), k) for u in users]))


def load():
    """user_id (uint64 hashes) is replaced by a dense int64 code to avoid float casts in merges;
    sub keeps the original id in column `raw_id` for writing the submission file."""
    j = pd.read_pickle(f'{CACHE}/join.pkl')
    s = pd.read_pickle(f'{CACHE}/sched_all.pkl')
    sub = pd.read_csv('data/submission.csv', dtype={'user_id': np.uint64})
    ids = np.unique(np.concatenate([j.user_id.values, sub.user_id.values]))
    j['user_id'] = np.searchsorted(ids, j.user_id.values).astype(np.int64)
    sub['raw_id'] = sub.user_id
    sub['user_id'] = np.searchsorted(ids, sub.user_id.values).astype(np.int64)
    global IDS
    IDS = ids
    return j, s, sub


IDS = None


def load_views():
    """Raw view log with the same dense user codes as load() (call load() first)."""
    v = pd.read_pickle(f'{CACHE}/views.pkl')
    v['user_id'] = np.searchsorted(IDS, v.user_id.values).astype(np.int64)
    v['week'] = 11 + v.vs // (7 * 86400)
    return v


def week_of(ts):
    return 11 + ts // (7 * 86400)


def make_truth(rows, thr=0.8, k=K):
    """Official rule (competition Data page): per user and airing, screen time = watched / duration;
    keep airings with screen time >= thr; count such airings per tv_show_id; truth = 5 most frequent.
    Ties broken by tv_show_id (the host's tie rule is not published). Users with < k shows dropped."""
    t = rows[rows.ov >= thr * rows.pdur]
    c = t.groupby(['user_id', 'tv_show_id']).size().rename('n').reset_index()
    c = c.sort_values(['user_id', 'n', 'tv_show_id'], ascending=[True, False, True])
    top = c.groupby('user_id').head(k)
    sizes = top.groupby('user_id').size()
    top = top[top.user_id.isin(sizes[sizes == k].index)]
    return top.groupby('user_id').tv_show_id.agg(list).to_dict()


def split(j, s, hist_weeks, target_weeks, thr=0.8):
    """History = joined rows in hist_weeks (all users). Truth = official top-5 rule on target_weeks.
    Target schedule = labelled airings in target_weeks (known in advance, no viewing data)."""
    h = j[j.week.isin(hist_weeks)]
    truth = make_truth(j[j.week.isin(target_weeks)], thr)
    ss = s[(s.tv_show_id != 0)].copy()
    ss['week'] = week_of(ss.ts)
    tgt_sched = ss[ss.week.isin(target_weeks)]
    return h, truth, tgt_sched


def topk_from_scores(score_df, k=K, fill=None):
    """score_df: columns user_id, tv_show_id, score. Returns dict user -> list of k ids,
    padded with `fill` (a ranked list) without duplicates."""
    score_df = score_df.sort_values(['user_id', 'score'], ascending=[True, False])
    preds = score_df.groupby('user_id').tv_show_id.apply(lambda x: list(x[:k])).to_dict()
    return preds


def pad(preds, users, fill, k=K):
    out = {}
    for u in users:
        p = list(preds.get(u, []))[:k]
        if len(p) < k:
            for f in fill:
                if f not in p:
                    p.append(f)
                if len(p) == k:
                    break
        out[u] = p
    return out
