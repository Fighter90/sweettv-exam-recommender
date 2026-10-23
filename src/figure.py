"""Fig. 1: hold-out MAP@5 of the best setting of each method (values from results/attempts_table.csv)."""
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T = {r['attempt']: r for r in csv.DictReader(open('results/attempts_table.csv'))}
rows = [('Popularity (#1)', '1'), ('CBF TF-IDF (#89)', '89'), ('Item-kNN CF (#92)', '92'), ('ALS MF (#66)', '66'),
        ('Assoc. rules (#82)', '82'), ('Personal freq. (#61)', '61'), ('PPR alpha=0.5 (#77)', '77'),
        ('Hybrid LightGBM (#107)', '107'), ('Final ensemble (#123)', '123')]
lab = [r[0] for r in rows]
a = [float(T[k]['MAP@5_all_users_4030']) for _, k in rows]
s = [float(T[k]['MAP@5_test_users_1150']) for _, k in rows]
fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
y = range(len(rows))
ax.barh([i + 0.2 for i in y], s, 0.4, color='#2a6f97', label='test users (n=1150)')
ax.barh([i - 0.2 for i in y], a, 0.4, color='#a9c5d9', label='all hold-out users (n=4030)')
for i, (vs, va) in enumerate(zip(s, a)):
    ax.text(vs + 0.004, i + 0.2, f'{vs:.3f}', va='center', fontsize=7)
    ax.text(va + 0.004, i - 0.2, f'{va:.3f}', va='center', fontsize=7, color='#555')
ax.set_yticks(list(y)); ax.set_yticklabels(lab, fontsize=8)
ax.set_xlabel('MAP@5, history weeks 11-20 -> truth weeks 21-30', fontsize=8)
ax.set_xlim(0, 0.52); ax.tick_params(axis='x', labelsize=7)
ax.spines[['top', 'right']].set_visible(False)
ax.legend(fontsize=7, loc='lower right', frameon=False)
plt.tight_layout(); plt.savefig('report/fig1_methods.png')
print('ok')
