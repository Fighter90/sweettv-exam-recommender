"""Validate a submission CSV against the template and compare it with a reference file
(the one submitted to Kaggle). Usage: python checks/check_submission.py <candidate.csv> [reference.csv]"""
import sys, hashlib
import numpy as np
import pandas as pd

cand = sys.argv[1]
ref = sys.argv[2] if len(sys.argv) > 2 else None
tmpl = pd.read_csv('data/submission.csv', dtype=str)
c = pd.read_csv(cand, dtype=str)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
print(f'[file] {cand}  sha256 {sha(cand)}')
ok = True
def check(name, cond):
    global ok
    ok &= bool(cond)
    print(f'  {"PASS" if cond else "FAIL"}  {name}')
check('header is user_id,tv_show_id', list(c.columns) == ['user_id', 'tv_show_id'])
check('1260 rows, same users in the same order as the template', len(c) == 1260 and (c.user_id.values == tmpl.user_id.values).all())
lists = c.tv_show_id.str.split()
check('5 ids per row', (lists.str.len() == 5).all())
check('5 distinct ids per row', lists.apply(lambda x: len(set(x)) == 5).all())
check('no id 0 (unlabelled airtime)', not lists.apply(lambda x: '0' in x).any())
s = pd.read_csv('data/export_arh_31-42-final.csv', usecols=['tv_show_id'])
aired = set(s.tv_show_id.astype(str))
check('every id airs in the weeks 31-42 schedule', lists.apply(lambda x: all(i in aired for i in x)).all())
if ref:
    r = pd.read_csv(ref, dtype=str)
    print(f'[reference] {ref}  sha256 {sha(ref)}')
    same_rows = (r.tv_show_id.values == c.tv_show_id.values).sum()
    rl = r.tv_show_id.str.split()
    same_sets = sum(set(a) == set(b) for a, b in zip(rl, lists))
    print(f'  identical rows (same ids, same order): {same_rows} of {len(r)}')
    print(f'  rows with the same five ids in any order: {same_sets} of {len(r)}')
    print(f'  byte-identical files: {sha(ref) == sha(cand)}')
print('[result]', 'ALL CHECKS PASS' if ok else 'SOME CHECKS FAILED')
