"""Candidate generation + features for the learning-to-rank hybrid.

Candidates for a user = programmes from the user's own history (any overlap) that air in the target
window, plus the top-N of PPR, ALS, association rules and CBF, plus the global top-N popular.
Every feature is computed from history-window views and from the schedule only (the target-window
schedule tells which programme airs when; target-window views are never touched)."""
import numpy as np
import pandas as pd
import methods as M

WEEK = 7 * 86400


def build(h, sched, hist_weeks, target_weeks, users, items, n_gen=30, n_pop=20, seed=42,
          gens=('ppr', 'als', 'ar', 'cbf')):
    hist_weeks, target_weeks = list(hist_weeks), list(target_weeks)
    lw, Lh, Lt = max(hist_weeks), len(hist_weeks), len(target_weeks)
    SCH = sched[sched.tv_show_id != 0].assign(week=lambda d: 11 + d.ts // WEEK)
    st = SCH[SCH.week.isin(target_weeks)]
    sh = SCH[SCH.week.isin(hist_weeks)]
    cand = set(st.tv_show_id)
    users = list(users)
    uset = set(users)

    # ---------------- user x show history aggregates
    hu = h[h.user_id.isin(uset) & h.tv_show_id.isin(cand)].copy()
    hu['frac'] = (hu.ov / hu.pdur).clip(0, 1)
    hu['hi'] = (hu.frac >= 0.8).astype(np.int32)
    hu['half'] = (hu.frac >= 0.5).astype(np.int32)
    hu['age'] = lw - hu.week
    hu['w4'] = 0.5 ** (hu.age / 4.0) * hu.hi
    hu['w2'] = 0.5 ** (hu.age / 2.0) * hu.hi
    hu['w8'] = 0.5 ** (hu.age / 8.0) * hu.hi
    hu['hi_l2'] = hu.hi * (hu.age < 2)
    hu['hi_l4'] = hu.hi * (hu.age < 4)
    g = hu.groupby(['user_id', 'tv_show_id'])
    us = g.agg(n_any=('hi', 'size'), n_hi=('hi', 'sum'), n_half=('half', 'sum'), ov_sum=('ov', 'sum'),
               frac_mean=('frac', 'mean'), frac_max=('frac', 'max'), w2=('w2', 'sum'), w4=('w4', 'sum'),
               w8=('w8', 'sum'), hi_l2=('hi_l2', 'sum'), hi_l4=('hi_l4', 'sum'),
               last_week=('week', 'max'), first_week=('week', 'min'),
               n_weeks=('week', 'nunique')).reset_index()
    hw = hu[hu.hi == 1].groupby(['user_id', 'tv_show_id']).week.agg(['max', 'nunique'])
    hw.columns = ['last_hi_week', 'n_hi_weeks']
    us = us.merge(hw.reset_index(), on=['user_id', 'tv_show_id'], how='left')
    us['since_hi'] = (lw - us.last_hi_week).fillna(99)
    us['since_any'] = lw - us.last_week
    us['n_hi_weeks'] = us.n_hi_weeks.fillna(0)
    us['src_hist'] = 1

    # ---------------- generator candidates (scores also used as features)
    gen_frames = {}
    if 'ppr' in gens:
        gen_frames['ppr'] = M.ppr(h, cand, users, n=n_gen)
    if 'als' in gens:
        gen_frames['als'] = M.als(h, cand, users, n=n_gen, seed=seed)
    if 'ar' in gens:
        gen_frames['ar'] = M.assoc_rules(h, cand, users, n=n_gen)
    if 'cbf' in gens:
        gen_frames['cbf'] = M.cbf(h, cand, users, items, n=n_gen)
    pop = M.popularity(h, cand, users)[:n_pop]
    popdf = pd.DataFrame({'user_id': np.repeat(users, len(pop)), 'tv_show_id': np.tile(pop, len(users))})

    keys = [us[['user_id', 'tv_show_id']], popdf]
    for k, f in gen_frames.items():
        keys.append(f[['user_id', 'tv_show_id']])
    df = pd.concat(keys, ignore_index=True).drop_duplicates()
    df = df.merge(us, on=['user_id', 'tv_show_id'], how='left')
    for k, f in gen_frames.items():
        f = f.rename(columns={'score': f'{k}_score'})
        f[f'{k}_rank'] = f.groupby('user_id')[f'{k}_score'].rank(ascending=False, method='first')
        df = df.merge(f, on=['user_id', 'tv_show_id'], how='left')
        df[f'{k}_rank'] = df[f'{k}_rank'].fillna(n_gen + 1)
    fill0 = ['n_any', 'n_hi', 'n_half', 'ov_sum', 'frac_mean', 'frac_max', 'w2', 'w4', 'w8', 'hi_l2',
             'hi_l4', 'n_weeks', 'n_hi_weeks', 'src_hist']
    df[fill0] = df[fill0].fillna(0)
    df['since_hi'] = df.since_hi.fillna(99)
    df['since_any'] = df.since_any.fillna(99)

    # ---------------- show features (schedule + history popularity)
    air_t = st.groupby('tv_show_id').agg(air_t=('ts', 'size'), air_t_sec=('duration', 'sum'),
                                         dur_mean=('duration', 'mean'), n_ch_t=('channel_id', 'nunique'),
                                         air_t_first=('week', 'min'), air_t_last=('week', 'max'),
                                         air_t_weeks=('week', 'nunique'))
    air_t['air_t_pw'] = air_t.air_t / Lt
    air_t['air_t_first'] -= min(target_weeks)
    air_t['air_t_last'] = max(target_weeks) - air_t['air_t_last']
    air_h = sh.groupby('tv_show_id').agg(air_h=('ts', 'size'))
    air_h['air_h_pw'] = air_h.air_h / Lh
    hh = h[h.ov >= 0.8 * h.pdur]
    gp = hh.groupby('tv_show_id').agg(pop_hi=('user_id', 'size'), pop_users=('user_id', 'nunique'))
    gp['pop_hi_pw'] = gp.pop_hi / Lh
    gl = hh[hh.week > lw - 4].groupby('tv_show_id').agg(pop_hi_l4=('user_id', 'size'))
    show = air_t.join(air_h, how='left').join(gp, how='left').join(gl, how='left').fillna(0)
    show['air_ratio'] = show.air_t_pw / (show.air_h_pw + 0.1)
    show['pop_trend'] = (show.pop_hi_l4 / 4) / (show.pop_hi_pw + 0.1)
    cat = items['cat'].astype('category').cat.codes.rename('cat_code')
    show = show.join(cat, how='left')
    df = df.merge(show, left_on='tv_show_id', right_index=True, how='left')

    # ---------------- user features
    hu_all = h[h.user_id.isin(uset)]
    uf = hu_all.assign(hi=(hu_all.ov >= 0.8 * hu_all.pdur).astype(int)).groupby('user_id').agg(
        u_hi=('hi', 'sum'), u_rows=('hi', 'size'), u_shows=('tv_show_id', 'nunique'),
        u_weeks=('week', 'nunique'), u_last=('week', 'max'))
    uf['u_hi_pw'] = uf.u_hi / Lh
    uf['u_since'] = lw - uf.u_last
    df = df.merge(uf.drop(columns='u_last'), left_on='user_id', right_index=True, how='left')
    df[['u_hi', 'u_rows', 'u_shows', 'u_weeks', 'u_hi_pw']] = df[['u_hi', 'u_rows', 'u_shows', 'u_weeks', 'u_hi_pw']].fillna(0)
    df['u_since'] = df.u_since.fillna(99)

    # ---------------- user x channel affinity (time share on the programme's channels in target window)
    uc = h[h.user_id.isin(uset)].groupby(['user_id', 'channel_id']).ov.sum()
    uc = (uc / uc.groupby(level=0).transform('sum')).rename('ch_share').reset_index()
    sc_ = st.groupby(['tv_show_id', 'channel_id']).size().rename('n').reset_index()
    sc_['w'] = sc_.n / sc_.groupby('tv_show_id').n.transform('sum')
    x = df[['user_id', 'tv_show_id']].merge(sc_, on='tv_show_id').merge(uc, on=['user_id', 'channel_id'], how='left')
    x['ch_share'] = x.ch_share.fillna(0) * x.w
    chs = x.groupby(['user_id', 'tv_show_id']).ch_share.sum().rename('ch_aff').reset_index()
    df = df.merge(chs, on=['user_id', 'tv_show_id'], how='left')
    df['ch_aff'] = df.ch_aff.fillna(0)

    # ---------------- user x hour-of-day affinity vs programme's target airing hours
    hv = h[h.user_id.isin(uset)].assign(hr=lambda d: (d.ts % 86400) // 3600)
    uh = hv.groupby(['user_id', 'hr']).ov.sum()
    uh = (uh / uh.groupby(level=0).transform('sum')).rename('hr_share').reset_index()
    sh_ = st.assign(hr=lambda d: (d.ts % 86400) // 3600).groupby(['tv_show_id', 'hr']).size().rename('n').reset_index()
    sh_['w'] = sh_.n / sh_.groupby('tv_show_id').n.transform('sum')
    x = df[['user_id', 'tv_show_id']].merge(sh_, on='tv_show_id').merge(uh, on=['user_id', 'hr'], how='left')
    x['hr_share'] = x.hr_share.fillna(0) * x.w
    hrs = x.groupby(['user_id', 'tv_show_id']).hr_share.sum().rename('hr_aff').reset_index()
    df = df.merge(hrs, on=['user_id', 'tv_show_id'], how='left')
    df['hr_aff'] = df.hr_aff.fillna(0)

    # ---------------- derived
    df['catch'] = df.n_hi / (df.air_h + 1)
    df['catch_any'] = df.n_any / (df.air_h + 1)
    df['exp_hi'] = df.catch * df.air_t
    df['exp_hi_pw'] = df.catch * df.air_t_pw
    df['n_hi_pw'] = df.n_hi / Lh
    df['n_any_pw'] = df.n_any / Lh
    df['share_hi'] = df.n_hi / (df.u_hi + 1)
    df['rank_hi'] = df.groupby('user_id').n_hi.rank(ascending=False, method='average')
    df['rank_w4'] = df.groupby('user_id').w4.rank(ascending=False, method='average')
    df['rank_exp'] = df.groupby('user_id').exp_hi.rank(ascending=False, method='average')
    return df


FEATS_EXCLUDE = {'user_id', 'tv_show_id', 'label', 'cnt', 'last_week', 'first_week', 'last_hi_week',
                 'n_hi_w', 'u_last'}


def feat_cols(df):
    return [c for c in df.columns if c not in FEATS_EXCLUDE]


def add_labels(df, truth):
    rel = {}
    for u, lst in truth.items():
        for r, i in enumerate(lst):
            rel[(u, i)] = 5 - r
    k = list(zip(df.user_id.values, df.tv_show_id.values))
    df['label'] = np.array([rel.get(x, 0) for x in k], dtype=np.int32)
    return df


def slot_features(df, views, h, sched, hist_weeks, target_weeks, max_hours=48):
    """Habit features. Occupancy P_u(channel, weekday, hour) = share of history weeks in which the user
    had any view of that channel covering that hour (raw view log, labelled or not). For every
    target-window airing of a programme we look up the user's occupancy at the airing's slot(s):
    slot_sum = sum over target airings (expected number of airings the user is 'there' for),
    slot_mean = mean per airing. hi_slot_* do the same with weeks in which the user had a high-screen
    (>=0.8) labelled airing starting in that slot."""
    hist_weeks, target_weeks = list(hist_weeks), list(target_weeks)
    Lh = len(hist_weeks)
    users = df.user_id.unique()
    v = views[views.user_id.isin(set(users)) & views.week.isin(hist_weeks)]
    h0 = v.vs // 3600
    h1 = np.minimum(v.ve // 3600, h0 + max_hours)
    n = (h1 - h0 + 1).values
    hrs = np.repeat(h0.values, n) + (np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n))
    occ = pd.DataFrame({'user_id': np.repeat(v.user_id.values, n), 'channel_id': np.repeat(v.vsetv_id.values, n),
                        'slot': (hrs % 168).astype(np.int16), 'wk': (hrs // 168).astype(np.int16)})
    occ = occ.drop_duplicates().groupby(['user_id', 'channel_id', 'slot']).size().rename('occ').reset_index()
    occ['occ'] = occ.occ / Lh

    SCH = sched[sched.tv_show_id != 0].assign(week=lambda d: 11 + d.ts // WEEK)
    st = SCH[SCH.week.isin(target_weeks)]
    st = st.assign(slot=((st.ts // 3600) % 168).astype(np.int16),
                   slot2=(((st.ts + st.duration // 2) // 3600) % 168).astype(np.int16))
    air = st.groupby(['tv_show_id', 'channel_id', 'slot', 'slot2']).size().rename('k').reset_index()
    pairs = df[['user_id', 'tv_show_id']]
    x = pairs.merge(air, on='tv_show_id')
    x = x.merge(occ, on=['user_id', 'channel_id', 'slot'], how='left')
    x = x.merge(occ.rename(columns={'slot': 'slot2', 'occ': 'occ2'}), on=['user_id', 'channel_id', 'slot2'], how='left')
    x['occ'] = x.occ.fillna(0)
    x['occ2'] = x.occ2.fillna(0)
    x['s1'] = x.occ * x.k
    x['s2'] = x.occ2 * x.k
    x['s12'] = np.minimum(x.occ, x.occ2) * x.k
    g = x.groupby(['user_id', 'tv_show_id']).agg(slot_sum=('s1', 'sum'), slot_mid_sum=('s2', 'sum'),
                                                  slot_both_sum=('s12', 'sum'), k=('k', 'sum'),
                                                  slot_max=('occ', 'max'))
    g['slot_mean'] = g.slot_sum / g.k
    g['slot_both_mean'] = g.slot_both_sum / g.k
    g = g.drop(columns='k').reset_index()

    # high-screen labelled airings by slot
    hh = h[h.user_id.isin(set(users)) & (h.ov >= 0.8 * h.pdur)]
    hs = hh.assign(slot=((hh.ts // 3600) % 168).astype(np.int16)).groupby(
        ['user_id', 'channel_id', 'slot']).week.nunique().rename('hocc').reset_index()
    hs['hocc'] = hs.hocc / Lh
    y = pairs.merge(air[['tv_show_id', 'channel_id', 'slot', 'k']], on='tv_show_id').merge(
        hs, on=['user_id', 'channel_id', 'slot'], how='left')
    y['hocc'] = y.hocc.fillna(0)
    y['hs'] = y.hocc * y.k
    g2 = y.groupby(['user_id', 'tv_show_id']).agg(hi_slot_sum=('hs', 'sum'), hi_slot_max=('hocc', 'max'),
                                                   k=('k', 'sum'))
    g2['hi_slot_mean'] = g2.hi_slot_sum / g2.k
    g2 = g2.drop(columns='k').reset_index()
    out = df.merge(g, on=['user_id', 'tv_show_id'], how='left').merge(g2, on=['user_id', 'tv_show_id'], how='left')
    cols = ['slot_sum', 'slot_mid_sum', 'slot_both_sum', 'slot_max', 'slot_mean', 'slot_both_mean',
            'hi_slot_sum', 'hi_slot_max', 'hi_slot_mean']
    out[cols] = out[cols].fillna(0)
    out['rank_slot'] = out.groupby('user_id').slot_both_sum.rank(ascending=False, method='average')
    out['rank_hislot'] = out.groupby('user_id').hi_slot_sum.rank(ascending=False, method='average')
    return out


def extra_features(df, h, sched, hist_weeks, target_weeks):
    """Show stickiness, recent catch rates, near-term airings, recent user activity."""
    hist_weeks, target_weeks = list(hist_weeks), list(target_weeks)
    lw, t0 = max(hist_weeks), min(target_weeks)
    SCH = sched[sched.tv_show_id != 0].assign(week=lambda d: 11 + d.ts // WEEK)
    hh = h[h.ov >= 0.8 * h.pdur]
    per_user = hh.groupby(['tv_show_id', 'user_id']).size()
    stick = per_user.groupby(level=0).agg(['mean', 'median', 'max'])
    stick.columns = ['stick_mean', 'stick_median', 'stick_max']
    rep = (per_user >= 3).groupby(level=0).mean().rename('stick_rep3')
    # retention: share of the show's early-half viewers who also watched it in the last 4 history weeks
    mid = hist_weeks[len(hist_weeks) // 2]
    a = hh[hh.week < mid].groupby('tv_show_id').user_id.agg(set)
    b = hh[hh.week > lw - 4].groupby('tv_show_id').user_id.agg(set)
    ret = pd.Series({k: len(v & b.get(k, set())) / len(v) for k, v in a.items()}, name='show_ret')
    air_l2 = SCH[(SCH.week > lw - 2) & (SCH.week <= lw)].groupby('tv_show_id').size().rename('air_l2')
    air_l4 = SCH[(SCH.week > lw - 4) & (SCH.week <= lw)].groupby('tv_show_id').size().rename('air_l4')
    air_e2 = SCH[(SCH.week >= t0) & (SCH.week < t0 + 2)].groupby('tv_show_id').size().rename('air_e2')
    air_e4 = SCH[(SCH.week >= t0) & (SCH.week < t0 + 4)].groupby('tv_show_id').size().rename('air_e4')
    show = pd.concat([stick, rep, ret, air_l2, air_l4, air_e2, air_e4], axis=1)
    show['hi_per_air'] = hh.groupby('tv_show_id').size().reindex(show.index).fillna(0) / (
        SCH[SCH.week.isin(hist_weeks)].groupby('tv_show_id').size().reindex(show.index).fillna(0) + 1)
    df = df.drop(columns=[c for c in show.columns if c in df.columns])
    df = df.merge(show, left_on='tv_show_id', right_index=True, how='left')
    for c in show.columns:
        df[c] = df[c].fillna(0)
    df['catch_l2'] = df.hi_l2 / (df.air_l2 + 1)
    df['catch_l4'] = df.hi_l4 / (df.air_l4 + 1)
    df['exp_e4'] = df.catch_l4 * df.air_e4
    df['exp_l4_t'] = df.catch_l4 * df.air_t
    ua = hh.assign(l1=hh.week == lw, l4=hh.week > lw - 4).groupby('user_id')[['l1', 'l4']].sum()
    ua.columns = ['u_hi_l1', 'u_hi_l4']
    df = df.drop(columns=[c for c in ua.columns if c in df.columns]).merge(ua, left_on='user_id', right_index=True, how='left')
    df[['u_hi_l1', 'u_hi_l4']] = df[['u_hi_l1', 'u_hi_l4']].fillna(0)
    df['share_l4'] = df.hi_l4 / (df.u_hi_l4 + 1)
    df['rank_l4'] = df.groupby('user_id').hi_l4.rank(ascending=False, method='average')
    df['rank_catch_l4'] = df.groupby('user_id').exp_l4_t.rank(ascending=False, method='average')
    return df


def ppr_pair_features(df, h, alphas=(0.5,), iters=20):
    """PPR score of every candidate pair (not only the generator's top-N) for several restart
    probabilities, plus personal frequency at screen-time >= 0.5 (both best single methods)."""
    import scipy.sparse as sp
    M_, uids, iids = M.interaction_matrix(h, value='log')
    Pu = sp.diags(1.0 / (np.asarray(M_.sum(1)).ravel() + 1e-12)) @ M_
    MT = M_.T.tocsr()
    Pi = sp.diags(1.0 / (np.asarray(MT.sum(1)).ravel() + 1e-12)) @ MT
    T = (Pi @ Pu).tocsr()
    ui = np.searchsorted(uids, df.user_id.values)
    ok_u = (ui < len(uids)) & (uids[np.minimum(ui, len(uids) - 1)] == df.user_id.values)
    ii = np.searchsorted(iids, df.tv_show_id.values)
    ok_i = (ii < len(iids)) & (iids[np.minimum(ii, len(iids) - 1)] == df.tv_show_id.values)
    need = np.unique(ui[ok_u])
    for a in alphas:
        col = np.zeros(len(df), dtype=np.float32)
        for b in range(0, len(need), 1024):
            blk = need[b:b + 1024]
            R = Pu[blk].toarray()
            x = R.copy()
            for _ in range(iters):
                x = a * R + (1 - a) * (T.T @ x.T).T
            pos = {u: r for r, u in enumerate(blk)}
            m = ok_u & ok_i & np.isin(ui, blk)
            rows = np.array([pos[u] for u in ui[m]])
            col[m] = x[rows, ii[m]]
        df[f'ppr{int(a * 100)}'] = col
        df[f'ppr{int(a * 100)}_rank'] = df.groupby('user_id')[f'ppr{int(a * 100)}'].rank(ascending=False)
    hh = h[h.ov >= 0.5 * h.pdur].groupby(['user_id', 'tv_show_id']).size().rename('n_hi50')
    df = df.drop(columns=[c for c in ['n_hi50'] if c in df.columns]).merge(
        hh.reset_index(), on=['user_id', 'tv_show_id'], how='left')
    df['n_hi50'] = df.n_hi50.fillna(0)
    df['rank_hi50'] = df.groupby('user_id').n_hi50.rank(ascending=False)
    return df


def lag_features(df, h, hist_weeks, n_lags=10):
    """Weekly lags: number of high-screen airings of the programme by the user in each of the last
    n_lags history weeks (lag 0 = last history week), plus slope over those weeks and the longest
    run of consecutive recent weeks with at least one high-screen airing."""
    lw = max(hist_weeks)
    hh = h[(h.ov >= 0.8 * h.pdur) & (h.week > lw - n_lags)]
    hh = hh[hh.user_id.isin(set(df.user_id.unique()))]
    c = hh.assign(lag=lw - hh.week).groupby(['user_id', 'tv_show_id', 'lag']).size().unstack('lag', fill_value=0)
    c = c.reindex(columns=range(n_lags), fill_value=0)
    c.columns = [f'lag{i}' for i in range(n_lags)]
    X = c.values
    x = np.arange(n_lags)[::-1].astype(float)          # time index, newest = largest
    xc = x - x.mean()
    c['lag_slope'] = (X * xc).sum(1) / (xc ** 2).sum()
    run = np.zeros(len(c), dtype=int)
    alive = np.ones(len(c), dtype=bool)
    for i in range(n_lags):
        alive &= X[:, i] > 0
        run += alive
    c['lag_run'] = run
    c['lag_std'] = X.std(1)
    df = df.drop(columns=[k for k in c.columns if k in df.columns])
    df = df.merge(c.reset_index(), on=['user_id', 'tv_show_id'], how='left')
    for k in c.columns:
        df[k] = df[k].fillna(0)
    return df
