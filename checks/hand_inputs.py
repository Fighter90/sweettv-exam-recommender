"""Raw inputs for the two hand checks (the student computes the results by hand, not this script).
1) Join: views of user 8377619604347126107 on channel 3 (1+1) on 2020-03-16 and the labelled airings
   of that channel that day. 2) MAP@5: the slide example and the heavy user's popularity list.
Usage: python checks/hand_inputs.py"""
import numpy as np
import pandas as pd

U, CH, DAY = 8377619604347126107, 3, '2020-03-16'
v = pd.read_csv('data/dataset11-30.csv', dtype={'user_id': np.uint64})
v = v[(v.user_id == np.uint64(U)) & (v.vsetv_id == CH) & v.start_time.str.startswith(DAY)]
print(f'[views] user {U}, channel {CH}, {DAY}:')
print(v[['start_time', 'stop_time', 'duraton']].to_string(index=False))
s = pd.read_csv('data/export_arh_11-20-final.csv', low_memory=False)
s = s[(s.channel_id == CH) & s.start_time.str.startswith('16.03.2020') & (s.tv_show_id != 0)]
print(f'[airings] channel {CH} on 16.03.2020 with tv_show_id != 0 (first 12):')
print(s[['start_time', 'duration', 'tv_show_id', 'tv_show_title']].head(12).to_string(index=False))
print('[slide example] R = {A, B, C}; list X = [A, B, D, C, E]; list Y = [D, A, E, B, C]')
print('[heavy user, hold-out] actual top-5 weeks 21-30: 2400480 ТСН. Неделя, 2400508 Сегодня. Итоги, '
      '240081 Факты. День, 20088 Завтрак с 1+1, 12002955 Свинка Пеппа')
print('  popularity list: 2400480, 240081, 12001682, 20088, 2400508')
