"""Attempts built from saved out-of-fold scores: per-user rank averaging of several hybrid models.
Usage: python src/ensemble.py <attempt_id> <name> <oof_id[:weight]> ...  (same protocol and users)"""
import sys, os, time
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from ranker import get_frame, evaluate, log

df, truth, sub_users, all_users, pop = get_frame()
aid, name = int(sys.argv[1]), sys.argv[2]
t0 = time.time()
score = np.zeros(len(df))
for part in sys.argv[3:]:
    k, w = (part.split(':') + ['1'])[:2]
    o = np.load(f'cache/oof_{k}.npy')
    score += float(w) * pd.Series(o).groupby(df.user_id.values).rank(pct=True).values
np.save(f'cache/oof_{aid}.npy', score)
log(aid, name, *evaluate(df, score, truth, sub_users, all_users, pop), time.time() - t0)
