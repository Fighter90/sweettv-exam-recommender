"""Builds the exam report in English (submitted) and Russian (for reading), DOCX, then PDF with LibreOffice.
Usage: python report/build_report.py en|ru
Every number comes from results/attempts_table.csv, results/data_stats.txt, results/examples.md, the Kaggle
submissions page (screenshots/kaggle_submissions.png) or the OpenCode reproduction logs (results/oc/)."""
import re
import sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

LANG = sys.argv[1] if len(sys.argv) > 1 else 'en'
RU = LANG == 'ru'
OUT = f'/home/claude/sw/report/emelyanov_sergey_exam_report{"_ru" if RU else ""}.docx'
FIG = '/home/claude/sw/report/fig1_methods.png'
SHOT = '/home/claude/sw/report/kaggle_submissions.png'
SHOT2 = '/home/claude/sw/report/kaggle_submission_details.png'
REPO = 'https://github.com/Fighter90/sweettv-recommender'


def T(en, ru):
    return ru if RU else en


doc = Document()
st = doc.styles['Normal']
st.font.name = 'Times New Roman'; st.font.size = Pt(9.5)
st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
st.paragraph_format.space_after = Pt(2); st.paragraph_format.line_spacing = 1.0
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(1.8); s.top_margin = s.bottom_margin = Cm(1.5)
ACC = RGBColor(0x1F, 0x3A, 0x5F)

INL = re.compile(r'(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)')


def run(p, text, size=None, bold=False, italic=False):
    for part in INL.split(text):
        if not part:
            continue
        if part.startswith('**'):
            r = p.add_run(part[2:-2]); r.bold = True
        elif part.startswith('`'):
            r = p.add_run(part[1:-1]); r.font.name = 'Consolas'; r.font.size = Pt(8.5)
        elif part.startswith('*') and len(part) > 2:
            r = p.add_run(part[1:-1]); r.italic = True
        else:
            r = p.add_run(part)
        if size: r.font.size = Pt(size)
        if bold: r.bold = True
        if italic: r.italic = True
    return p


def P(text, size=None, align=None, after=2, italic=False):
    p = doc.add_paragraph(); run(p, text, size, italic=italic)
    p.paragraph_format.space_after = Pt(after)
    if align: p.alignment = align
    return p


def H(text):
    p = doc.add_paragraph(); r = p.add_run(text); r.bold = True; r.font.size = Pt(10.5); r.font.color.rgb = ACC
    p.paragraph_format.space_before = Pt(5); p.paragraph_format.space_after = Pt(2)


def BL(items, size=None):
    for t in items:
        p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(0.5); p.paragraph_format.first_line_indent = Cm(-0.3)
        p.paragraph_format.space_after = Pt(1); run(p, '• ' + t, size)


def NL(items, size=None):
    for i, t in enumerate(items, 1):
        p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(0.5); p.paragraph_format.first_line_indent = Cm(-0.4)
        p.paragraph_format.space_after = Pt(1); run(p, f'{i}. ' + t, size)


def table(rows, widths, size=8, header=True, caption=None):
    t = doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = 'Table Grid'; t.autofit = False
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = t.cell(i, j); c.width = Cm(widths[j]); c.text = ''
            run(c.paragraphs[0], str(v), size, bold=(header and i == 0))
            c.paragraphs[0].paragraph_format.space_after = Pt(0)
    for j, w in enumerate(widths):
        for c in t.columns[j].cells:
            c.width = Cm(w)
    for j, gc in enumerate(t._tbl.tblGrid.findall(qn('w:gridCol'))):
        gc.set(qn('w:w'), str(int(widths[j] * 567)))
    for row in t.rows:  # keep each row on one page
        trPr = row._tr.get_or_add_trPr(); e = OxmlElement('w:cantSplit'); trPr.append(e)
    if caption:
        P(caption, size=8, italic=True, after=4)


# ------------------------------------------------------------------ title block
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run(T('Repeat Viewing Beats Collaborative Signal on sweet.tv: A Leakage-Free LightGBM Hybrid over '
                'Personal Frequency, Personalized PageRank and Association Rules for Top-5 TV Programmes',
                'Повторный просмотр сильнее коллаборативного сигнала на sweet.tv: гибрид LightGBM без утечки '
                'поверх личной частоты, Personalized PageRank и ассоциативных правил для Top-5 телепередач'))
r.bold = True; r.font.size = Pt(13)
P(T('Student: Sergey Emelyanov    Team: Individual    Email: sbemelyanov@edu.hse.ru    Date: 2026-10-24',
    'Студент: Сергей Емельянов    Команда: индивидуально    Email: sbemelyanov@edu.hse.ru    Дата: 2026-10-24'), size=9,
  align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
P(T('Assignment: Final Exam Quiz (AVITO) — TV Program Recommendation on sweet.tv    Kaggle: pochtasergeia',
    'Задание: Final Exam Quiz (AVITO) — TV Program Recommendation on sweet.tv    Kaggle: pochtasergeia'), size=9,
  align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
P(T(f'Repository: {REPO}', f'Репозиторий: {REPO}'), size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=4 if not RU else 0)
if RU:
    P('Русская версия отчёта для чтения; сдаётся английская версия. Числа, таблицы и ссылки те же.', size=8.5,
      align=WD_ALIGN_PARAGRAPH.CENTER, after=4, italic=True)

H(T('Abstract', 'Аннотация'))
P(T('The task is to predict, for 1,260 sweet.tv users, the five programmes they will watch most often in weeks 31–42, '
    'scored by MAP@5 against a top-5 built from airings watched for at least 80 % of their length. I joined 5.82 M viewing '
    'intervals to the 11 % of schedule rows that carry a programme id, reproduced the organisers\' answer rule on a '
    'weeks 11–20 → 21–30 hold-out, and compared a popularity baseline with personal frequency, Personalized PageRank (PPR), '
    'association rules, ALS matrix factorisation, item-kNN and content-based filtering before re-ranking their candidates '
    'with LightGBM. On the 1,150 test users with a full hold-out top-5, the best single method (PPR, α = 0.5) reaches '
    'MAP@5 0.394 and popularity 0.305, while the final hybrid ensemble reaches 0.447; on Kaggle it returned private 0.44801 '
    '(public 0.46135). On this platform, most of the signal is repeat viewing of the same news, kids\' and entertainment '
    'shows, so a hybrid that keeps the user\'s own history as the backbone outperforms pure collaborative filtering.',
    'Задача — предсказать для 1 260 пользователей sweet.tv пять передач, которые они чаще всего будут смотреть в неделях '
    '31–42; метрика MAP@5 против Top-5, построенного из показов, просмотренных не меньше чем на 80 % длины. Я сопоставил '
    '5,82 млн интервалов просмотра с 11 % строк расписания, у которых есть id передачи, воспроизвёл правило ответа '
    'организаторов на hold-out недели 11–20 → 21–30 и сравнил бейзлайн популярности с личной частотой, Personalized '
    'PageRank (PPR), ассоциативными правилами, матричной факторизацией ALS, item-kNN и контентной фильтрацией, а затем '
    'переранжировал их кандидатов с LightGBM. На 1 150 тестовых пользователях с полным Top-5 лучший одиночный метод '
    '(PPR, α = 0,5) даёт MAP@5 0,394, популярность — 0,305, финальный гибридный ансамбль — 0,447; на Kaggle он получил '
    'private 0,44801 (public 0,46135). На этой платформе основной сигнал — повторный просмотр тех же новостей, детских и '
    'развлекательных передач, поэтому гибрид, опирающийся на собственную историю пользователя, обходит чистую '
    'коллаборативную фильтрацию.'))
P(T('*Index Terms* — recommender systems, implicit feedback, personalized PageRank, learning to rank, TV viewing logs.',
    '*Ключевые слова* — рекомендательные системы, неявная обратная связь, personalized PageRank, обучение ранжированию, '
    'логи телепросмотра.'), after=3)

# ------------------------------------------------------------------ 1
H(T('1. Introduction', '1. Введение'))
P(T('**Problem statement.** The competition [1] gives a view log (`user_id, vsetv_id, start_time, stop_time, duraton`) for '
    'weeks 11–30 of 2020 and broadcast schedules for weeks 11–42. A view is a channel interval, not a programme, so '
    'interactions must be built by joining views to airings. The answer for weeks 31–42 is defined on the Data page: drop '
    '`tv_show_id = 0`, compute per user and airing *screen time = watched time / programme duration*, keep airings with '
    'screen time ≥ 0.8, count them per programme and take the five most frequent, in order.',
    '**Постановка задачи.** Соревнование [1] даёт лог просмотров (`user_id, vsetv_id, start_time, stop_time, duraton`) '
    'за недели 11–30 2020 года и расписания вещания за недели 11–42. Просмотр — это интервал на канале, а не передача, '
    'поэтому взаимодействия строятся сопоставлением просмотров с показами. Ответ для недель 31–42 определён на странице '
    'Data: отбросить `tv_show_id = 0`, по каждому пользователю и показу посчитать *screen time = просмотренное время / '
    'длительность передачи*, оставить показы с screen time ≥ 0,8, посчитать их по передаче и взять пять самых частых '
    'по порядку.'))
P(T('**Motivation.** My first local truth (any overlap ≥ 300 s) gave the popularity baseline MAP@5 0.727. That is far from '
    'the 0.4–0.46 range of real submissions, so the metric was not measuring the competition\'s target. With the official '
    'rule the same baseline scores 0.305, and the hold-out estimate of the first submitted hybrid (0.439, attempt 22) landed near its '
    'Kaggle private score (0.448). Before tuning any model, the evaluation itself has to be validated.',
    '**Мотивация.** Мой первый локальный ответ (любое перекрытие ≥ 300 с) давал бейзлайну популярности MAP@5 0,727. Это '
    'далеко от диапазона 0,4–0,46 реальных отправок, то есть метрика измеряла не то, что соревнование. С официальным '
    'правилом тот же бейзлайн даёт 0,305, а оценка первого отправленного гибрида на hold-out (0,439, попытка 22) оказалась рядом '
    'с его private на Kaggle (0,448). Прежде чем настраивать модели, надо проверить саму оценку.'))
P(T('**Concrete example.** User 8377619604347126107 (90th percentile of activity) watched *ТСН. Неделя* 59 times and '
    '*Факты. День* 22 times at ≥ 80 % screen time in weeks 11–20. In weeks 21–30 the top-5 was ТСН. Неделя, '
    'Сегодня. Итоги, Факты. День, Завтрак с 1+1 and Свинка Пеппа. The hybrid returns exactly these five (AP@5 = 1.000), '
    'popularity hits four of them (0.710) and ALS three (0.550), Table 3.',
    '**Конкретный пример.** Пользователь 8377619604347126107 (90-й перцентиль активности) в неделях 11–20 смотрел '
    '*ТСН. Неделя* 59 раз и *Факты. День* 22 раза с screen time ≥ 80 %. В неделях 21–30 его Top-5: ТСН. Неделя, '
    'Сегодня. Итоги, Факты. День, Завтрак с 1+1 и Свинка Пеппа. Гибрид выдаёт ровно эти пять (AP@5 = 1,000), '
    'популярность угадывает четыре (0,710), ALS — три (0,550), Таблица 3.'))
P(T('**Contributions.** (i) A leakage-free pipeline that reproduces the organisers\' answer rule locally, with 124 logged '
    'attempts in which each method is first evaluated individually, then combined. (ii) A hybrid (candidate generation + '
    'LightGBM) that improves MAP@5 by +0.053 over the best single method on the same users, and a Kaggle private score of '
    '0.44801 (public 0.46135). (iii) An independent reproduction on a second machine, which shows which of these numbers '
    'are stable and which depend on the numeric library (§4, Table 4).',
    '**Вклад.** (i) Конвейер без утечки, который локально воспроизводит правило ответа организаторов, со 124 '
    'записанными попытками: каждый метод сначала оценён отдельно, потом объединён. (ii) Гибрид (генерация кандидатов + '
    'LightGBM), который улучшает MAP@5 на +0,053 относительно лучшего одиночного метода на тех же пользователях, и private '
    'на Kaggle 0,44801 (public 0,46135). (iii) Независимое воспроизведение на второй машине, которое показывает, какие '
    'из этих чисел устойчивы, а какие зависят от числовой библиотеки (§4, Таблица 4).'), after=3)

# ------------------------------------------------------------------ 2
H(T('2. Related Work', '2. Связанные работы'))
P(T('[2] Hu, Koren and Volinsky: confidence-weighted ALS for implicit feedback, my MF method (`implicit` library). '
    '[3] Haveliwala: topic-sensitive (personalised) PageRank, a random walk with restart to a preference set, my PPR on the '
    'user–programme graph. [4] Agrawal and Srikant: support/confidence association rules, used here as pairwise rules '
    'A → B over users\' programme sets. [5] Sarwar et al.: item-based CF with cosine similarity. [6] Lops et al.: '
    'content-based recommenders built from item attributes, my TF-IDF CBF. [7] Ke et al.: LightGBM, the gradient-boosted '
    're-ranker. [8] Burges: LambdaRank/LambdaMART, the listwise objective I compared with a pointwise binary one. '
    '[9] Hamner: the reference `apk/mapk` code used by Kaggle MAP@K metrics.',
    '[2] Hu, Koren, Volinsky: ALS с весами доверия для неявной обратной связи, мой метод MF (библиотека `implicit`). '
    '[3] Haveliwala: тематический (персонализированный) PageRank — случайное блуждание с рестартом в множество '
    'предпочтений, мой PPR на графе «пользователь–передача». [4] Agrawal, Srikant: ассоциативные правила с support и '
    'confidence, здесь парные правила A → B над множествами передач пользователей. [5] Sarwar и др.: item-based CF с '
    'косинусной близостью. [6] Lops и др.: контентные рекомендатели на атрибутах объектов, мой TF-IDF CBF. [7] Ke и др.: '
    'LightGBM, градиентный бустинг для переранжирования. [8] Burges: LambdaRank/LambdaMART, списочная цель, которую я '
    'сравнил с поточечной бинарной. [9] Hamner: эталонный код `apk/mapk`, на котором основаны метрики MAP@K Kaggle.'))
P(T('**Alternatives considered.** (a) Pure MF as the final model: rejected because it scores 0.235 against 0.392 for '
    'simply repeating the user\'s own most-watched shows (attempts 66 vs 61). (b) A fraction-of-duration watch threshold '
    'other than 0.8 for the *answer*: not an option, since the organisers fix it; for *features* 0.5 and 0.95 were tried '
    '(0.5 is best as a single method, 0.392 vs 0.383). (c) Lift-ranked association rules: they collapse to 0.012 because '
    'lift rewards rare programmes (attempt 84).',
    '**Рассмотренные альтернативы.** (a) Чистая MF как финальная модель: отклонена, потому что даёт 0,235 против 0,392 у '
    'простого повтора самых просматриваемых передач пользователя (попытки 66 и 61). (b) Другой порог доли длительности '
    'для *ответа*, кроме 0,8: невозможно, его фиксируют организаторы; для *признаков* пробовал 0,5 и 0,95 (0,5 лучше как '
    'одиночный метод, 0,392 против 0,383). (c) Ассоциативные правила по lift: падают до 0,012, потому что lift поощряет '
    'редкие передачи (попытка 84).'), after=3)

# ------------------------------------------------------------------ 3
H(T('3. Method', '3. Метод'))
P(T('**Approach.** I build interactions with an interval join, then evaluate everything on one temporal hold-out with the '
    'official answer rule. Single methods produce scores over the candidate pool and the top-5 is read off directly. The '
    'hybrid takes the union of their candidates and learns a ranking from history-only features.',
    '**Подход.** Взаимодействия строятся интервальным джойном, затем всё оценивается на одном временном hold-out с '
    'официальным правилом ответа. Одиночные методы дают счёт по пулу кандидатов, и Top-5 берётся напрямую. Гибрид '
    'объединяет их кандидатов и учится ранжировать по признакам только из истории.'))
P(T('**Pipeline.**', '**Конвейер.**'))
NL([T('**Join** (`prep.py`). Keep schedule rows with `tv_show_id ≠ 0`; per channel, binary-search each view against airing '
      'starts/ends; overlap = min(ends) − max(starts) > 0; sum the overlap of several view fragments of the same airing. '
      'The week of an airing is taken from its start time, not from the schedule file it is stored in (the weeks 11–20 '
      'file also holds airings of 2020-05-18, week 21). Result: 3,014,129 user–airing rows for 4,895 users and 4,363 '
      'programmes, 20.4 % of them with screen time ≥ 0.8.',
      '**Джойн** (`prep.py`). Оставить строки расписания с `tv_show_id ≠ 0`; по каждому каналу бинарным поиском '
      'сопоставить просмотр с началами и концами показов; перекрытие = min(концов) − max(начал) > 0; перекрытия '
      'нескольких фрагментов просмотра одного показа складываются. Неделя показа берётся по времени его начала, а не по '
      'файлу расписания (файл недель 11–20 содержит и показы 18.05.2020, это неделя 21). Итог: 3 014 129 строк '
      '«пользователь–показ» для 4 895 пользователей и 4 363 передач, у 20,4 % из них screen time ≥ 0,8.'),
    T('**Candidate pool.** Programmes with an id that air in the target window according to its schedule (6,376 for weeks '
      '21–30; 6,642 for 31–42). Repeats of already-watched programmes are allowed for every method, because the answer counts '
      'repeat viewing. Every list is padded with the same popularity list. This is also the cold-start fallback: 2 of the '
      '1,260 test users have no labelled history and receive it unchanged.',
      '**Пул кандидатов.** Передачи с id, которые идут в целевом окне по его расписанию (6 376 для недель 21–30; 6 642 '
      'для 31–42). Повторы уже просмотренных передач разрешены всем методам, потому что ответ считает повторный просмотр. '
      'Каждый список дополняется одним и тем же списком популярности. Это и запасной вариант для холодного старта: у 2 из '
      '1 260 тестовых пользователей нет истории с id, и они получают его без изменений.'),
    T('**Single methods** (`methods.py`). Popularity: number of ≥ 0.8 airings per programme in the history. Personal '
      'frequency: the user\'s own count of ≥ τ airings. ALS [2] on log(1+count), confidence 1 + α·value. Item-kNN [5] with '
      'cosine and shrinkage. PPR [3]: restart probability α at the user\'s own programmes, item→user→item transitions on '
      'log-count edges, 20 power iterations. Association rules [4]: confidence(A→B) over programme sets, minimum support, '
      'score = max over the user\'s antecedents. CBF [6]: TF-IDF over category, genres, directors, actors and main channel; '
      'profile = log-count-weighted sum. Each method outputs a score; its top-5 is the answer.',
      '**Одиночные методы** (`methods.py`). Популярность: число показов передачи с ≥ 0,8 в истории. Личная частота: число '
      'собственных показов пользователя с ≥ τ. ALS [2] на log(1+count), доверие 1 + α·value. Item-kNN [5] с косинусом и '
      'сжатием. PPR [3]: вероятность рестарта α в собственные передачи пользователя, переходы передача→пользователь→'
      'передача по рёбрам log-count, 20 итераций степенного метода. Ассоциативные правила [4]: confidence(A→B) по '
      'множествам передач, минимальный support, счёт = максимум по посылкам пользователя. CBF [6]: TF-IDF по категории, '
      'жанрам, режиссёрам, актёрам и основному каналу; профиль — сумма с весами log-count. Каждый метод выдаёт счёт; его '
      'Top-5 и есть ответ.'),
    T('**Hybrid** (`features.py`, `ranker.py`). Candidates = the user\'s own history in the pool, the top-30 of PPR, ALS, '
      'AR and CBF, and the top-20 popular programmes (189.5 per user; they contain 85.2 % of the true top-5 items). '
      'About 100 features: own counts at several thresholds and recencies, weekly lags, catch rate = hits / airings, number '
      'and timing of airings in the target window (schedule only), channel and hour-of-day affinity, show stickiness, '
      'generator scores and ranks, full-pair PPR at α 0.5/0.7. LightGBM [7] learns P(item ∈ true top-5). Per-user ranks of '
      'several models are averaged.',
      '**Гибрид** (`features.py`, `ranker.py`). Кандидаты = собственная история пользователя в пуле, top-30 из PPR, ALS, '
      'AR и CBF и top-20 популярных передач (189,5 на пользователя; в них 85,2 % правильных ответов). Около 100 '
      'признаков: собственные счётчики при нескольких порогах и давностях, недельные лаги, доля пойманных показов = '
      'попадания / показы, число и время показов в целевом окне (только расписание), привязанность к каналу и часу, '
      '«липкость» передачи, счета и ранги генераторов, PPR по полной паре при α 0,5/0,7. LightGBM [7] учит P(передача ∈ '
      'истинный Top-5). Ранги нескольких моделей по пользователю усредняются.'),
    T('**Final model** (attempt 123). A rank average of three seed bags: binary, 31 leaves, 400 rounds, learning rate 0.05, '
      '5 seeds; binary, learning rate 0.03, 700 rounds, 3 seeds; L2 regression on log(1+future count), 3 seeds. Trained on '
      'the 11–20 → 21–30 hold-out of all 4,030 users plus two extra temporal splits (11–24 → 25–30, 11–17 → 18–24). It '
      'scores weeks 31–42 from features of weeks 11–30.',
      '**Финальная модель** (попытка 123). Ранговое среднее трёх мешков по сидам: binary, 31 лист, 400 раундов, learning '
      'rate 0,05, 5 сидов; binary, learning rate 0,03, 700 раундов, 3 сида; L2-регрессия на log(1+будущий счёт), 3 сида. '
      'Обучена на hold-out 11–20 → 21–30 всех 4 030 пользователей и двух дополнительных временных сплитах (11–24 → 25–30, '
      '11–17 → 18–24). Неделям 31–42 ставит счёт по признакам недель 11–30.')])
P(T('**Tools & libraries.** Python 3.13.16, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, scikit-learn 1.9.1 (TF-IDF), '
    'implicit 0.7.3 (ALS) [10], LightGBM 4.7.0 [11], matplotlib 3.11.2. AI agents (§6): Claude Code for development, '
    'OpenCode v2.1.2 [12] with GLM-5.3-Flash for the reproduction on my Mac.',
    '**Инструменты и библиотеки.** Python 3.13.16, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, scikit-learn 1.9.1 (TF-IDF), '
    'implicit 0.7.3 (ALS) [10], LightGBM 4.7.0 [11], matplotlib 3.11.2. ИИ-агенты (§6): Claude Code для разработки, '
    'OpenCode v2.1.2 [12] с GLM-5.3-Flash для воспроизведения на моём Mac.'))
P(T('**Key design decisions.** (1) *Validate the metric first*: the truth rule is copied from the Data page, and ties in '
    'the local truth are broken by id because the organisers\' tie rule is not published. (2) *User-grouped 3-fold CV* for the '
    'hybrid: the scored user\'s rows never appear in the training folds, and the extra temporal splits drop the held-out '
    'users too. (3) *Longer history at test time*: a model trained on 5-week features scored 10-week features better than '
    'matched 5-week ones (all users 0.4024 vs 0.3972, attempts 26 vs 25). So the final model, trained with 10–14-week '
    'histories, is applied to the full 20 weeks.',
    '**Ключевые решения.** (1) *Сначала проверить метрику*: правило ответа взято со страницы Data, ничьи в локальном '
    'ответе решаются по id, потому что правило ничьих организаторов не опубликовано. (2) *3-fold CV, сгруппированная по '
    'пользователям*, для гибрида: строки оцениваемого пользователя не попадают в обучающие фолды, и из дополнительных '
    'временных сплитов эти пользователи тоже удаляются. (3) *Более длинная история при тесте*: модель, обученная на '
    'признаках за 5 недель, лучше оценивала признаки за 10 недель, чем за те же 5 (все пользователи 0,4024 против 0,3972, '
    'попытки 26 и 25). Поэтому финальная модель, обученная на истории 10–14 недель, применяется ко всем 20 неделям.'))
P(T('**Configuration.** Hold-out: history 11–20, truth 21–30. LightGBM: feature_fraction 0.8, bagging 0.8, λ2 = 1, '
    'min_data_in_leaf 50. ALS f = 16, reg 0.05, α = 10, seed 42. PPR α = 0.5, 20 iterations. AR min support 50. Fold seed 0. '
    'Hardware: 4 vCPU Intel Xeon 2.1 GHz, 15 GB RAM, numpy with OpenBLAS (all numbers in Tables 1–3).',
    '**Конфигурация.** Hold-out: история 11–20, ответ 21–30. LightGBM: feature_fraction 0,8, bagging 0,8, λ2 = 1, '
    'min_data_in_leaf 50. ALS f = 16, reg 0,05, α = 10, seed 42. PPR α = 0,5, 20 итераций. AR min support 50. Сид фолдов 0. '
    'Железо: 4 vCPU Intel Xeon 2,1 ГГц, 15 ГБ ОЗУ, numpy с OpenBLAS (все числа Таблиц 1–3).'), after=3)

# ------------------------------------------------------------------ 4
H(T('4. Experiments', '4. Эксперименты'))
P(T('**Setup.** Table 1 gives the data accounting (from `results/data_stats.txt`). MAP@5 uses the slide/Kaggle formula '
    'AP@5 = Σₖ P@k·rel(k) / min(|R|, 5). Two user sets: the 1,150 *test users* that have a full top-5 in weeks 21–30, and '
    'all 4,030 such users (lower variance; the standard error is about 0.005).',
    '**Постановка.** Таблица 1 — учёт данных (из `results/data_stats.txt`). MAP@5 по формуле слайдов и Kaggle '
    'AP@5 = Σₖ P@k·rel(k) / min(|R|, 5). Два набора пользователей: 1 150 *тестовых пользователей* с полным Top-5 в неделях '
    '21–30 и все 4 030 таких пользователей (меньше дисперсия; стандартная ошибка около 0,005).'))
table([[T('Quantity', 'Величина'), T('Value', 'Значение')],
       [T('View log', 'Лог просмотров'), T('5,821,987 intervals; 4,914 users; 202 channels; median 396 s, max 342,145 s',
                                          '5 821 987 интервалов; 4 914 пользователей; 202 канала; медиана 396 с, максимум 342 145 с')],
       [T('Schedules (rows / with id)', 'Расписания (строк / с id)'),
        T('11–20: 1,074,235 / 115,613; 21–30: 1,074,394 / 121,505; 31–42: 1,295,378 / 144,774',
          '11–20: 1 074 235 / 115 613; 21–30: 1 074 394 / 121 505; 31–42: 1 295 378 / 144 774')],
       [T('Joined user–airing rows', 'Строки джойна'),
        T('3,014,129 (4,895 users, 4,363 programmes); 615,979 with screen time ≥ 0.8',
          '3 014 129 (4 895 пользователей, 4 363 передачи); 615 979 с screen time ≥ 0,8')],
       [T('Test users', 'Тестовые пользователи'),
        T('1,260; 1,258 with labelled history; 1,150 with a full top-5 in weeks 21–30',
          '1 260; 1 258 с историей с id; 1 150 с полным Top-5 в неделях 21–30')],
       [T('Hold-out users (full top-5)', 'Пользователи hold-out (полный Top-5)'),
        T('4,030; candidate pool 6,376 programmes; hybrid frame 763,617 rows',
          '4 030; пул кандидатов 6 376 передач; таблица гибрида 763 617 строк')],
       [T('Test window', 'Тестовое окно'),
        T('6,642 candidate programmes; 6,308 of 145,041 airings have an id never seen in weeks 11–30',
          '6 642 передачи-кандидата; у 6 308 из 145 041 показов id, которого не было в неделях 11–30')]],
      [4.2, 13.2], caption=T('Table 1. Data accounting. The 145,041 test-window airings include 267 week-31 airings stored in the weeks 21–30 file.', 'Таблица 1. Учёт данных. 145 041 показ тестового окна включает 267 показов недели 31 из файла недель 21–30.'))
table([[T('Method (best setting, attempt)', 'Метод (лучшая настройка, попытка)'), T('Test users', 'Тестовые'),
        T('All users', 'Все'), T('Time', 'Время')],
       [T('Popularity baseline (#1)', 'Бейзлайн популярности (#1)'), '0.305', '0.279', '<1 s'],
       [T('CBF TF-IDF, channel weight 2 (#89)', 'CBF TF-IDF, вес канала 2 (#89)'), '0.204', '0.190', '2 s'],
       [T('Item-kNN, shrink 50 (#92)', 'Item-kNN, сжатие 50 (#92)'), '0.218', '0.207', '1 s'],
       ['ALS f=16 (#66); f=64 (#6)', '0.235; 0.212', '0.227; 0.208', '2 s'],
       [T('Association rules, confidence, minsup 50 (#82)', 'Ассоциативные правила, confidence, minsup 50 (#82)'),
        '0.320', '0.300', '3 s'],
       [T('Personal frequency, τ = 0.5 (#61); τ = 0.8 (#2)', 'Личная частота, τ = 0,5 (#61); τ = 0,8 (#2)'),
        '0.392; 0.383', '0.356; 0.347', '<1 s'],
       ['PPR α = 0.5 (#77); α = 0.15 (#8)', '0.394; 0.349', '0.361; 0.323', '30 s'],
       [T('Hybrid LightGBM lambdarank, 1 split (#11)', 'Гибрид LightGBM lambdarank, 1 сплит (#11)'), '0.429', '0.398',
        T('59 s (CV)', '59 s (CV)')],
       [T('Hybrid LightGBM binary, 3 seeds (#22)', 'Гибрид LightGBM binary, 3 сида (#22)'), '0.439', '0.407', '115 s (CV)'],
       [T('Hybrid LightGBM binary, 3 splits + lags, 5 seeds (#107)', 'Гибрид LightGBM binary, 3 сплита + лаги, 5 сидов (#107)'),
        '0.446', '0.412', '529 s (CV)'],
       [T('**Final ensemble (#123)**', '**Финальный ансамбль (#123)**'), '**0.447**', '**0.413**',
        T('742 s (train+score)', '742 s (обучение+счёт)')]],
      [9.0, 2.6, 2.6, 3.2], caption=T('Table 2. Hold-out MAP@5 (history weeks 11–20 → truth weeks 21–30). All 124 attempts '
                                      'are listed in results/attempts_table.csv. Best setting = highest MAP@5 on all users; for PPR, '
                                      'α = 0.7 (#78) is equal within noise (0.396 / 0.361).',
                                      'Таблица 2. MAP@5 на hold-out (история недели 11–20 → ответ недели 21–30). Все 124 '
                                      'попытки — в results/attempts_table.csv. Лучшая настройка — максимум MAP@5 на всех пользователях; '
                                      'для PPR α = 0,7 (#78) равен в пределах шума (0,396 / 0,361).'))
doc.add_picture(FIG, width=Cm(13.5)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
P(T('Fig. 1. Best setting of each method on the same hold-out, the same candidate pool and the same popularity fallback.',
    'Рис. 1. Лучшая настройка каждого метода на одном hold-out, одном пуле кандидатов и одном запасном списке популярности.'),
  size=8, italic=True, after=4)
P(T('**Comparison vs baseline.** Popularity is a strong reference (0.305), because a few national news and morning shows '
    'dominate everyone\'s top-5. ALS, item-kNN and CBF fall below it: they rank programmes *similar* to the history, while '
    'the answer mostly contains the *same* programmes again. Personal frequency and PPR (whose restart keeps most mass on '
    'the user\'s own items when α ≥ 0.5) beat popularity by about 0.09. The hybrid adds a further +0.053, because it '
    'learns when a habit continues: recent weekly counts, catch rate and the number of target-window airings. '
    'After attempt 35 (0.447 / 0.411), 57 further hybrid attempts (hyper-parameters, objectives, features, ensembles) '
    'changed the test-user score by −0.008 to +0.0002 and the all-user score by at most +0.002, within the noise.',
    '**Сравнение с бейзлайном.** Популярность — сильная точка отсчёта (0,305): несколько общенациональных новостей и '
    'утренних шоу есть в Top-5 почти у всех. ALS, item-kNN и CBF ниже неё: они ранжируют передачи, *похожие* на историю, '
    'а ответ в основном состоит из *тех же* передач. Личная частота и PPR (рестарт которого при α ≥ 0,5 держит большую '
    'часть массы на собственных передачах пользователя) обходят популярность примерно на 0,09. Гибрид добавляет ещё '
    '+0,053, потому что учится, когда привычка продолжается: недавние недельные счётчики, доля пойманных показов и число '
    'показов в целевом окне. После попытки 35 (0,447 / 0,411) ещё 57 попыток гибрида (гиперпараметры, цели, признаки, '
    'ансамбли) меняли счёт на тестовых пользователях от −0,008 до +0,0002, а на всех — не больше чем на +0,002, в пределах шума.'))
P(T('**Kaggle.** The first hybrid submission (`bin3`: binary objective, 3 seeds, no extra splits, i.e. attempt 22 on the '
    'hold-out) returned private 0.44756 / public 0.45892. The final ensemble returned **private 0.44801 / public 0.46135** '
    '(Fig. 2), the best of the two on both splits (the course grades the private score), with the description '
    '"Емельянов Сергей Борисович (pochtasergeia) — …" (full name in Russian and Kaggle name, as the course requires), and '
    'it is the designated final submission (Kaggle disables selecting a submission after the deadline, so it is '
    'designated by this screenshot, this report and submission/sub_final.csv in the repository).',
    '**Kaggle.** Первая отправка гибрида (`bin3`: бинарная цель, 3 сида, без дополнительных сплитов, на hold-out это '
    'попытка 22) получила private 0,44756 / public 0,45892. Финальный ансамбль получил **private 0,44801 / public '
    '0,46135** (Рис. 2) — лучший из двух на обеих частях (курс оценивает private), с описанием «Емельянов Сергей '
    'Борисович (pochtasergeia) — …» (ФИО по-русски и имя на Kaggle, как требует курс); это назначенная финальная отправка '
    '(после дедлайна Kaggle не даёт выбрать отправку, поэтому её назначают этот скриншот, этот отчёт и '
    'submission/sub_final.csv в репозитории).'))
doc.add_picture(SHOT, width=Cm(14.5)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.paragraphs[-1].paragraph_format.space_after = Pt(2)
doc.add_picture(SHOT2, width=Cm(11.0)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
P(T('Fig. 2. Kaggle, account pochtasergeia. Top: submissions page with both late submissions; the final sub_final.csv '
    'returned private 0.44801 and public 0.46135. Bottom: its details with the description (full name and Kaggle name).',
    'Рис. 2. Kaggle, аккаунт pochtasergeia. Сверху: страница отправок с обеими поздними отправками; финальная '
    'sub_final.csv получила private 0,44801 и public 0,46135. Снизу: её карточка с описанием (ФИО и имя на Kaggle).'),
  size=8, italic=True, after=3)
P(T('**Verification.** (a) *Join on one data point*: on 2020-03-16 the user above viewed channel 1+1 from 06:26:04 to '
    '06:27:24, while ТСН. Неделя aired 05:00–06:30 (5,400 s). Overlap = 80 s, screen time 80 / 5,400 = 0.0148, so this '
    'airing is not counted; the 12:00 airing of the same show (1,200 s) lies inside the view 11:57:48–12:28:02, overlap '
    '1,200 s, screen time 1.0, counted. Both rows are in the join output (`ts` 622800 and 648000). '
    '(b) *Metric on one data point*: popularity for the same user hits ranks 1, 2, 4 and 5, so AP@5 = (1/1 + 2/2 + 3/4 + '
    '4/5) / 5 = 3.55 / 5 = 0.710, equal to `apk` in Table 3; on the slide example `apk` returns 0.9167 and 0.5333. '
    '(c) *Answer rule, independent re-implementation*: a separate script that does not import `src/` joins each sampled '
    'user\'s views to every airing of the channel by brute force; on 300 random users it gives identical top-5 lists for '
    '247 of 247 users with a full top-5. Cutting the window by schedule file instead of by start time changes one of the '
    '247 (user 5215032701573495051: four airings of Свинка Пеппа on 2020-05-18 sit in the weeks 11–20 file, 283 labelled '
    'week-21 airings in total). (d) *Submission file*: 1,260 rows in the template\'s user order, five distinct non-zero '
    'ids that air in weeks 31–42 (`checks/check_submission.py`). (e) *Leakage*: features read only history-window views '
    'and the target-window *schedule*; the CV folds are grouped by user.',
    '**Проверка.** (a) *Джойн на одной точке данных*: 16.03.2020 пользователь выше смотрел канал 1+1 с 06:26:04 до '
    '06:27:24, а ТСН. Неделя шла 05:00–06:30 (5 400 с). Перекрытие = 80 с, screen time 80 / 5 400 = 0,0148, показ не '
    'засчитан; показ той же передачи в 12:00 (1 200 с) целиком внутри просмотра 11:57:48–12:28:02, перекрытие 1 200 с, '
    'screen time 1,0, засчитан. Обе строки есть в выходе джойна (`ts` 622800 и 648000). (b) *Метрика на одной точке '
    'данных*: популярность у того же пользователя попадает на позициях 1, 2, 4 и 5, поэтому AP@5 = (1/1 + 2/2 + 3/4 + '
    '4/5) / 5 = 3,55 / 5 = 0,710, как `apk` в Таблице 3; на примере со слайда `apk` даёт 0,9167 и 0,5333. (c) *Правило '
    'ответа, независимая реализация*: отдельный скрипт, не импортирующий `src/`, перебором сопоставляет просмотры каждого '
    'пользователя выборки со всеми показами канала; на 300 случайных пользователях Top-5 совпали у 247 из 247 '
    'пользователей с полным Top-5. Если резать окно по файлу расписания, а не по времени начала, меняется один из 247 '
    '(пользователь 5215032701573495051: четыре показа «Свинки Пеппы» 18.05.2020 лежат в файле недель 11–20; всего таких '
    'показов недели 21 с id — 283). (d) *Файл отправки*: 1 260 строк в порядке пользователей шаблона, пять разных '
    'ненулевых id, которые идут в неделях 31–42 (`checks/check_submission.py`). (e) *Утечка*: признаки читают только '
    'просмотры окна истории и *расписание* целевого окна; фолды CV сгруппированы по пользователям.'))
P(T('**Reproduction on a second machine (Table 4).** The pipeline was re-run from a fresh clone twice on Linux x86-64 '
    '(by Claude Code) and once on my Apple M1 in a separate OpenCode session that I directed, with the same package '
    'versions (Python 3.13.13 there, 3.13.16 here). On Linux every number and the submission file are identical. On the M1, numpy uses Apple Accelerate instead '
    'of OpenBLAS; the last bits of the sparse AR and CBF products change, which reorders near-ties, gives a hybrid '
    'candidate frame of 763,658 rows instead of 763,617 and shifts LightGBM\'s splits.',
    '**Воспроизведение на второй машине (Таблица 4).** Конвейер перезапущен из чистого клона дважды на Linux x86-64 '
    '(в Claude Code) и один раз на моём Apple M1 в отдельной сессии OpenCode, которой я руководил, с теми же версиями '
    'пакетов (Python 3.13.13 там, 3.13.16 здесь). На Linux все числа и файл отправки совпали. На M1 numpy считает через Apple Accelerate вместо OpenBLAS: '
    'последние биты разреженных произведений AR и CBF меняются, порядок почти равных счетов сдвигается, в таблице '
    'кандидатов гибрида 763 658 строк вместо 763 617, и LightGBM строит другие разбиения.'))
table([[T('Check', 'Проверка'), T('Linux x86-64, OpenBLAS', 'Linux x86-64, OpenBLAS'),
        T('Apple M1, Accelerate (my session)', 'Apple M1, Accelerate (моя сессия)')],
       [T('Answer rule, independent script (300 users)', 'Правило ответа, независимый скрипт (300 польз.)'),
        '247 / 247', '247 / 247'],
       [T('10 single methods vs the log', '10 одиночных методов против лога'),
        T('10 / 10 to 5 decimals', '10 / 10 до 5-го знака'),
        T('7 / 10; AR and CBF within 0.00053', '7 / 10; AR и CBF в пределах 0,00053')],
       [T('Hybrid #107 / #121 / #122 (test users)', 'Гибрид #107 / #121 / #122 (тестовые)'),
        '0.44603 / 0.44511 / 0.44511', '0.44565 / 0.44678 / 0.44408'],
       [T('Final ensemble #123 (test / all users)', 'Финальный ансамбль #123 (тестовые / все)'),
        '0.44692 / 0.41315', '0.44548 / 0.41138'],
       [T('Candidate recall of the true top-5', 'Recall кандидатов по истинному Top-5'), '0.8515', '0.8513'],
       [T('Regenerated sub_final.csv', 'Заново построенный sub_final.csv'),
        T('byte-identical (sha256 76f439ce…7fe8)', 'побайтно тот же (sha256 76f439ce…7fe8)'),
        T('all format checks pass; same five ids for 1,037 / 1,260 users, same order for 722',
          'все проверки формата пройдены; те же пять id у 1 037 / 1 260, тот же порядок у 722')]],
      [6.2, 4.8, 6.4], caption=T('Table 4. Reproduction from a fresh clone (logs in results/oc/ of the OpenCode session).',
                                 'Таблица 4. Воспроизведение из чистого клона (логи в results/oc/ сессии OpenCode).'))

# ------------------------------------------------------------------ examples
H(T('Recommendation examples (same two users for every method)', 'Примеры рекомендаций (одни и те же два пользователя для всех методов)'))
P(T('I chose a typical heavy viewer (90th percentile of ≥ 0.8 airings in weeks 11–20, 179 airings) and a light viewer '
    '(5th percentile, 12 airings), both test users, to show where each method works. ✔ = in the user\'s actual weeks 21–30 '
    'top-5. Titles and categories are looked up from the schedule.',
    'Я взял типичного активного зрителя (90-й перцентиль по показам с ≥ 0,8 в неделях 11–20, 179 показов) и малоактивного '
    '(5-й перцентиль, 12 показов), оба — тестовые пользователи, чтобы показать, где работает каждый метод. ✔ = есть в '
    'реальном Top-5 недель 21–30. Названия и категории взяты из расписания.'))
M = lambda en, ru: T(en, ru)
heavy = [[T('Method', 'Метод'), 'AP@5', T('Top-5 (id title [category]) — heavy user 8377619604347126107',
                                          'Top-5 (id название [категория]) — активный пользователь 8377619604347126107')],
         [M('Popularity', 'Популярность'), '0.710', '2400480 ТСН. Неделя [Инфо] ✔; 240081 Факты. День [Инфо] ✔; 12001682 Губка Боб [Детям]; 20088 Завтрак с 1+1 [Развлечения] ✔; 2400508 Сегодня. Итоги [Инфо] ✔'],
         [M('Personal freq.', 'Личная частота'), '0.760', 'ТСН. Неделя ✔; Факты. День ✔; 12002955 Свинка Пеппа [Детям] ✔; 200338 Готовим вместе [Познавательное]; Завтрак с 1+1 ✔'],
         ['ALS (MF)', '0.550', 'Свинка Пеппа ✔; ТСН. Неделя ✔; 200344 Чистоnews [Развлечения]; Завтрак с 1+1 ✔; 12002896 Вспыш и чудо-машинки [Детям]'],
         ['PPR', '0.800', 'ТСН. Неделя ✔; Факты. День ✔; Сегодня. Итоги ✔; Завтрак с 1+1 ✔; 2400467 Викна-Новости [Инфо]'],
         [M('Assoc. rules', 'Ассоц. правила'), '0.550', 'ТСН. Неделя ✔; Свинка Пеппа ✔; Вспыш и чудо-машинки [Детям]; Факты. День ✔; Викна-Новости [Инфо]'],
         ['CBF', '0.167', '5900319 Абзац! [Инфо]; Викна-Новости [Инфо]; ТСН. Неделя ✔; Факты. День ✔; 2500261 Подробности недели [Инфо]'],
         [M('Hybrid (final)', 'Гибрид (финал)'), '1.000', 'ТСН. Неделя ✔; Факты. День ✔; Завтрак с 1+1 ✔; Свинка Пеппа ✔; Сегодня. Итоги ✔']]
table(heavy, [2.2, 1.3, 13.9], size=7.5)
light = [[T('Method', 'Метод'), 'AP@5', T('Top-5 — light user 795534560850101267', 'Top-5 — малоактивный пользователь 795534560850101267')],
         [M('Popularity', 'Популярность'), '0.400', 'ТСН. Неделя ✔; Факты. День ✔; Губка Боб [Детям]; Завтрак с 1+1 [Развлечения]; Сегодня. Итоги [Инфо]'],
         [M('Personal freq.', 'Личная частота'), '0.333', 'Факты. День ✔; 200337 Утро с Интером [Развлечения]; ТСН. Неделя ✔; 500281 Говорит Украина [Развлечения]; 5900348 Украинские сенсации [Инфо]'],
         ['ALS (MF)', '0.400', 'Факты. День ✔; ТСН. Неделя ✔; 6200371 ДжеДАИ [Познавательное]; Утро с Интером; Чистоnews'],
         ['PPR', '0.400', 'ТСН. Неделя ✔; Факты. День ✔; Губка Боб; Утро с Интером; Викна-Новости'],
         [M('Assoc. rules', 'Ассоц. правила'), '0.333', 'ТСН. Неделя ✔; Чистоnews; Факты. День ✔; Сегодня. Итоги; Викна-Новости'],
         ['CBF', '0.400', 'ТСН. Неделя ✔; Факты. День ✔; Подробности недели [Инфо]; Абзац! [Инфо]; Украинские сенсации [Инфо]'],
         [M('Hybrid (final)', 'Гибрид (финал)'), '0.400', 'Факты. День ✔; ТСН. Неделя ✔; Викна-Новости; Губка Боб; Сегодня. Итоги']]
table(light, [2.2, 1.3, 13.9], size=7.5,
      caption=T('Table 3. Top-5 of every method on the hold-out (results/examples.md). Actual top-5, heavy: ТСН. Неделя, '
                'Сегодня. Итоги, Факты. День, Завтрак с 1+1, Свинка Пеппа; light: Факты. День, 200352 Вечерний квартал, ТСН. Неделя, '
                'two films (90018819 Сломанная стрела, 90080730 Борг/Макинрой).',
                'Таблица 3. Top-5 каждого метода на hold-out (results/examples.md). Реальный Top-5, активный: ТСН. Неделя, '
                'Сегодня. Итоги, Факты. День, Завтрак с 1+1, Свинка Пеппа; малоактивный: Факты. День, 200352 Вечерний квартал, '
                'ТСН. Неделя, два фильма (90018819 Сломанная стрела, 90080730 Борг/Макинрой).'))

# ------------------------------------------------------------------ 5
H(T('5. Discussion — which strategy for SWEET.TV, and why', '5. Обсуждение — какую стратегию выбрать SWEET.TV и почему'))
P(T('**Recommendation.** Use the hybrid as the main "for you" row: candidates from the user\'s own history, PPR and '
    'association rules, re-ranked by LightGBM. It scores 0.447 against 0.394 for the best single method and 0.305 for '
    'popularity on the same users and protocol. Single methods cost seconds; the whole final model trains and scores '
    '1,260 users in 742 s on 4 vCPUs. Retraining weekly is therefore cheap, and serving is a feature lookup plus a tree '
    'ensemble over about 190 candidates per user.',
    '**Рекомендация.** Сделать гибрид основной полкой «для вас»: кандидаты из собственной истории пользователя, PPR и '
    'ассоциативных правил, переранжированные LightGBM. Он даёт 0,447 против 0,394 у лучшего одиночного метода и 0,305 у '
    'популярности на тех же пользователях и протоколе. Одиночные методы считаются за секунды; вся финальная модель '
    'обучается и ставит счёт 1 260 пользователям за 742 с на 4 vCPU. Еженедельное переобучение дёшево, а выдача — это '
    'чтение признаков и ансамбль деревьев примерно по 190 кандидатам на пользователя.'))
P(T('**How the methods differ (Table 3).** For the heavy user, personal frequency keeps *Готовим вместе*, which the user '
    'stopped watching. PPR\'s diffusion drops it (and Свинка Пеппа) for *Сегодня. Итоги*, a show co-watched by similar viewers, '
    'which was in the truth, and puts its four hits first (0.800). The hybrid also uses the target-window schedule and recent weeks, and it recovers all five. Association rules '
    'and ALS see the kids\' cluster (Свинка Пеппа → Вспыш) and so capture household co-viewing. CBF only matches '
    'attributes (news → news), which helps where co-view signal is thin. For the light user every method shares the same '
    'two hits, the national news shows that popularity already provides. Only three of the five true programmes are among '
    'the user\'s 192 candidates: the two films are not, so 0.600 is the ceiling, and the hybrid reaches 0.400. The third '
    'reachable programme, Вечерний квартал, has a single 105 s touch of a 6,600 s airing in the history, too weak to rank it. '
    'The lists are mostly *familiar* programmes, which fits a "continue watching / your channels" row. A discovery row (PPR '
    'beyond the user\'s own items, CBF for new-season series) should be a separate row: an unfamiliar item here is not shown '
    'to be a useful discovery.',
    '**Чем различаются методы (Таблица 3).** У активного пользователя личная частота держит *Готовим вместе*, которую он '
    'перестал смотреть. Диффузия PPR убирает её (и Свинку Пеппу) и ставит *Сегодня. Итоги* — передачу, которую смотрят похожие '
    'зрители, и она была в ответе; четыре попадания PPR стоят на первых местах (0,800). Гибрид дополнительно использует расписание целевого окна и последние недели и находит все пять. '
    'Ассоциативные правила и ALS видят детский кластер (Свинка Пеппа → Вспыш) и так ловят совместный просмотр в семье. '
    'CBF сопоставляет только атрибуты (новости → новости), что помогает там, где сигнал совместного просмотра слабый. У '
    'малоактивного пользователя у всех методов те же два попадания — общенациональные новости, которые даёт и '
    'популярность. Среди 192 кандидатов этого пользователя только три из пяти правильных передач: двух фильмов там нет, '
    'поэтому потолок 0,600, а гибрид достигает 0,400. У третьей достижимой передачи, «Вечернего квартала», в истории одно '
    'касание 105 с из показа длиной 6 600 с — слишком слабый сигнал, чтобы поднять её в Top-5. Списки состоят в основном '
    'из *знакомых* передач, что подходит полке «продолжить просмотр / ваши каналы». Полку открытий (PPR за пределами '
    'собственных передач, CBF для новых сезонов) стоит делать отдельной: незнакомая передача здесь не доказанно полезна.'))
P(T('**Failure case.** The first hybrid run reported candidate recall 0.0031 and MAP@5 0.305, the same as popularity, '
    'even though 85 % of true items were in the frame. **Root cause:** the 64-bit unsigned `user_id` hashes became '
    '`float64` after a `concat` with a frame of signed integers. Above 2⁵³ the cast loses digits, so (user, item) keys no '
    'longer matched the truth dictionary and almost every label became 0. **Fix + verification:** `load()` maps ids to '
    'dense `int64` codes and keeps the raw id only for writing the CSV. Recall became 0.8515 and MAP@5 0.433 on the next '
    'run, and the written file\'s ids are diffed against the template (identical).',
    '**Случай сбоя.** Первый прогон гибрида показал recall кандидатов 0,0031 и MAP@5 0,305 — как у популярности, хотя 85 % '
    'правильных передач были в таблице. **Причина:** 64-битные беззнаковые хэши `user_id` превратились во `float64` после '
    '`concat` с таблицей знаковых целых. Выше 2⁵³ приведение теряет цифры, ключи (пользователь, передача) перестали '
    'совпадать со словарём ответов, и почти все метки стали 0. **Исправление и проверка:** `load()` переводит id в плотные '
    'коды `int64`, а исходный id хранит только для записи CSV. На следующем прогоне recall стал 0,8515, MAP@5 — 0,433, а '
    'id в записанном файле сверены с шаблоном (совпадают).'))
P(T('**What worked.** Reproducing the official answer rule before modelling; letting repeat viewing drive the model; '
    'user-grouped CV, which made 124 attempts comparable; re-running everything on a second machine, which separated the '
    'stable claims from the fragile ones.',
    '**Что сработало.** Воспроизвести официальное правило ответа до моделирования; дать повторному просмотру вести '
    'модель; CV по пользователям, благодаря которой 124 попытки сравнимы; перезапуск всего на второй машине, который '
    'отделил устойчивые утверждения от хрупких.'))
P(T('**What surprised me / didn\'t work.** (1) PPR improved from 0.349 to 0.394 when the restart probability rose from 0.15 '
    'to 0.5, i.e. when it behaved *more* like personal frequency. (2) Generators find but cannot order: 78.6 % of a test '
    'user\'s true top-5 is already in their own weeks 11–20 history, and ALS has the highest recall of the true top-5 in its top-30 '
    '(0.716; PPR 0.707, popularity 0.655) but only 0.327 in its top-5, against 0.456 for PPR. So the generators are used only '
    'for candidates, and the re-ranker decides the order. (3) The ensemble\'s gain over its best component (+0.0009 over '
    '#107) is smaller than the spread between machines (up to 0.0018): on the M1, #121 alone scores above #123. Habit '
    'features, DART, lambdarank and extra hyper-parameter search did not beat the plain binary objective beyond noise.',
    '**Что удивило / не сработало.** (1) PPR вырос с 0,349 до 0,394, когда вероятность рестарта поднялась с 0,15 до 0,5, '
    'то есть когда он стал *больше* похож на личную частоту. (2) Генераторы находят, но не упорядочивают: 78,6 % '
    'правильного Top-5 тестового пользователя уже есть в его истории недель 11–20, и у ALS самый высокий recall правильного '
    'Top-5 в top-30 (0,716; PPR 0,707, популярность 0,655), но в top-5 только 0,327 против 0,456 у PPR. Поэтому '
    'генераторы дают только кандидатов, а порядок решает ранкер. (3) Выигрыш ансамбля над лучшим компонентом (+0,0009 к '
    '#107) меньше разброса между машинами (до 0,0018): на M1 один #121 выше #123. Признаки привычек, DART, lambdarank и '
    'дополнительный подбор гиперпараметров не обошли простую бинарную цель сверх шума.'))
P(T('**Limitations supported by the results.** Only about 11 % of schedule rows carry an id (10.8–11.3 % per file), so most viewing time is invisible '
    'to every method. 85.2 % candidate recall caps the hybrid. With a perfect ordering of the candidates by true future '
    'count, MAP@5 is 0.851 when ties are broken as in my truth and 0.776 when they are broken randomly; part of the score '
    'therefore depends on the organisers\' unpublished tie rule. 4.3 % of test-window airings carry programme ids never seen '
    'before (new season), which the hybrid can reach only through popularity or CBF. The defensible claim is the ordering '
    'hybrid > single methods > popularity, which holds on both machines and on Kaggle (one concordant pair: +0.00045 '
    'private), not the third decimal. The log covers this platform\'s views only, so absence from it does not mean a user '
    'never saw a programme, and nothing here shows that users enjoyed what they watched. No online test was run, and no '
    'revenue claim is made.',
    '**Ограничения, подтверждённые результатами.** Только примерно у 11 % строк расписания есть id (10,8–11,3 % по файлам), поэтому большая часть '
    'времени просмотра невидима для всех методов. Recall кандидатов 85,2 % ограничивает гибрид сверху. При идеальном '
    'порядке кандидатов по истинному будущему счёту MAP@5 равен 0,851, если ничьи решать как в моём ответе, и 0,776 при '
    'случайных ничьих; часть счёта зависит от неопубликованного правила ничьих организаторов. 4,3 % показов тестового окна '
    'несут id, которых раньше не было (новый сезон); гибрид может достать их только через популярность или CBF. '
    'Защитимое утверждение — порядок «гибрид > одиночные методы > популярность», который держится на обеих машинах и на '
    'Kaggle (одна согласованная пара: +0,00045 private), а не третий знак. Лог покрывает только просмотры на этой '
    'платформе: отсутствие в нём не значит, что пользователь не видел передачу, и ничто здесь не показывает, что '
    'пользователям понравилось увиденное. Онлайн-теста не было, утверждений о выручке нет.'))
P(T('**Next improvement.** An airing-level model that predicts P(screen time ≥ 0.8) for every target-window airing and sums '
    'the predictions into an expected count per programme. This would handle long films and schedule changes directly.',
    '**Следующее улучшение.** Модель уровня показа, которая предсказывает P(screen time ≥ 0,8) для каждого показа целевого '
    'окна и суммирует предсказания в ожидаемый счёт по передаче. Так напрямую учитывались бы длинные фильмы и изменения '
    'расписания.'), after=3)

# ------------------------------------------------------------------ 6
H(T('6. AI Usage Disclosure', '6. Раскрытие использования ИИ'))
BL([T('**Tools.** (1) Claude Code (Anthropic), cloud session, model Claude Opus 5.5, working on my Mac folder ~/kaggle and '
      'in my Chrome session (Kaggle rules acceptance, data download, the two late submissions). (2) OpenCode v2.1.2 [12] '
      'with GLM-5.3-Flash (Z.AI Coding Plan), on my Apple M1 (macOS 26.3.1), for a separate reproduction session.',
      '**Инструменты.** (1) Claude Code (Anthropic), облачная сессия, модель Claude Opus 5.5, с доступом к папке ~/kaggle на '
      'моём Mac и к моему Chrome (принятие правил Kaggle, скачивание данных, две поздние отправки). (2) OpenCode v2.1.2 [12] '
      'с GLM-5.3-Flash (Z.AI Coding Plan) на моём Apple M1 (macOS 26.3.1) для отдельной сессии воспроизведения.'),
    T('**How AI was used.** Claude Code: reading the task and the Data page; code generation (all of `src/`); running the '
      '124 attempts; debugging (the float64 id cast); the figure, the README and the drafts of this report (English and '
      'Russian); the plan of the OpenCode session (prompt sequence, expected numbers, reply templates) and its four check '
      'scripts (`audit_data.py`, `independent_truth.py`, `hand_inputs.py`, `check_submission.py`); during that session, '
      'reviewing the agent\'s answers and drafting most of my replies to it. OpenCode: re-running the pipeline from a fresh '
      'clone on my machine and checking each number (27 prompts, 97 tool calls, 2.9 h).',
      '**Как использовался ИИ.** Claude Code: чтение задания и страницы Data; генерация кода (весь `src/`); прогон 124 '
      'попыток; отладка (приведение id к float64); рисунок, README и черновики этого отчёта (английский и русский); план '
      'сессии OpenCode (последовательность запросов, ожидаемые числа, шаблоны реплик) и четыре скрипта проверки для неё '
      '(`audit_data.py`, `independent_truth.py`, `hand_inputs.py`, `check_submission.py`); во время той сессии — разбор '
      'ответов агента и черновики большинства моих реплик ему. OpenCode: перезапуск конвейера из чистого клона на моей машине '
      'и сверка каждого числа (27 запросов, 97 вызовов инструментов, 2,9 ч).'),
    T('**What I personally verified.** (a) I re-ran the experiment from scratch on my own machine and compared every number '
      'with the logged one (Table 4); the regenerated file is not byte-identical on Apple Silicon, and I recorded that '
      'instead of replacing the submitted file. (b) I read the private and public scores of both submissions on the Kaggle '
      'page myself (Fig. 2) and checked them against the README. (c) The hold-out order of the two submitted configurations '
      '(#123 0.447 > #22 0.439) matches their Kaggle order on both splits.',
      '**Что я проверил сам.** (a) Перезапустил эксперимент с нуля на своей машине и сверил каждое число с записанным '
      '(Таблица 4); на Apple Silicon заново построенный файл не совпал побайтно, и я записал это, а не заменил отправленный '
      'файл. (b) Сам прочитал private и public обеих отправок на странице Kaggle (Рис. 2) и сверил их с README. (c) Порядок '
      'двух отправленных конфигураций на hold-out (#123 0,447 > #22 0,439) совпадает с их порядком на Kaggle на обеих частях.'),
    T('**Trusted without verification / limits of my checks.** The data-point checks in §4 (a, b) were worked out with '
      'Claude; the same values appear in my OpenCode turns, which I asked Claude to write, so they are an AI cross-check '
      'confirmed by the code, not an independent hand calculation of mine. Two errors of the OpenCode agent (a table cell '
      'with 0.40989 instead of 0.44511 for #122, and an airing length of 2,700 s instead of 6,600 s) were found by Claude '
      'when I asked it to review the agent\'s answers; the correction of my mapping of the first submission to attempt #22 '
      'came from the OpenCode agent. The byte-identical runs on Linux were done by Claude Code, not on my machine. I also '
      'trusted the internals of LightGBM and `implicit` ALS, and the organisers\' description of the answer rule (their '
      'tie-breaking is unknown).',
      '**Чему я доверился без проверки / пределы моих проверок.** Проверки на одной точке данных в §4 (a, b) рассчитаны с '
      'Claude; те же значения есть в моих репликах в OpenCode, которые я просил написать Claude, поэтому это перекрёстная '
      'проверка ИИ, подтверждённая кодом, а не моя независимая ручная. Две ошибки агента OpenCode (ячейка таблицы с 0,40989 '
      'вместо 0,44511 у #122 и длина показа 2 700 с вместо 6 600 с) нашёл Claude, когда я попросил его проверить ответы '
      'агента; исправление моего сопоставления первой отправки с попыткой #22 пришло от агента OpenCode. Побайтные прогоны '
      'на Linux делал Claude Code, а не моя машина. Также я доверился внутреннему устройству LightGBM и ALS из `implicit` '
      'и описанию правила ответа организаторами (их правило ничьих неизвестно).'),
    T('**Session log.** Submitted unmodified: `emelyanov_sergey_exam_opencode_session.json` (OpenCode session '
      'ses_e95aa2d45ffelUbzQd00ghZrWQ of 2026-10-23, the reproduction in Table 4; its logs and check scripts are in '
      '`results/oc/` and `checks/`).',
      '**Лог сессии.** Сдаётся без изменений: `emelyanov_sergey_exam_opencode_session.json` (сессия OpenCode '
      'ses_e95aa2d45ffelUbzQd00ghZrWQ от 2026-10-23, воспроизведение из Таблицы 4; её логи и скрипты проверок — '
      'в `results/oc/` и `checks/`).')])

# ------------------------------------------------------------------ refs
H(T('References', 'Список литературы'))
refs = [
    '[1] ogurbych, "sweet.tv – TV program recommender," Kaggle Community Prediction Competition, 2020. [Online]. Available: https://www.kaggle.com/competitions/sweettv-tv-program-recommender. [Accessed: 2026-10-22].',
    '[2] Y. Hu, Y. Koren, and C. Volinsky, "Collaborative filtering for implicit feedback datasets," in Proc. 8th IEEE Int. Conf. Data Mining (ICDM), 2008, pp. 263–272, doi: 10.1109/ICDM.2008.22.',
    '[3] T. H. Haveliwala, "Topic-sensitive PageRank," in Proc. 11th Int. World Wide Web Conf. (WWW), 2002, pp. 517–526, doi: 10.1145/511446.511513.',
    '[4] R. Agrawal and R. Srikant, "Fast algorithms for mining association rules," in Proc. 20th Int. Conf. Very Large Data Bases (VLDB), 1994, pp. 487–499.',
    '[5] B. Sarwar, G. Karypis, J. Konstan, and J. Riedl, "Item-based collaborative filtering recommendation algorithms," in Proc. 10th Int. World Wide Web Conf. (WWW), 2001, pp. 285–295, doi: 10.1145/371920.372071.',
    '[6] P. Lops, M. de Gemmis, and G. Semeraro, "Content-based recommender systems: State of the art and trends," in Recommender Systems Handbook, F. Ricci et al., Eds. Boston, MA: Springer, 2011, pp. 73–105, doi: 10.1007/978-0-387-85820-3_3.',
    '[7] G. Ke et al., "LightGBM: A highly efficient gradient boosting decision tree," in Advances in Neural Information Processing Systems 30 (NeurIPS), 2017, pp. 3146–3154.',
    '[8] C. J. C. Burges, "From RankNet to LambdaRank to LambdaMART: An overview," Microsoft Research, Tech. Rep. MSR-TR-2010-82, 2010.',
    '[9] B. Hamner, "Metrics: Machine learning evaluation metrics (average_precision.py)," GitHub repository. [Online]. Available: https://github.com/benhamner/Metrics. [Accessed: 2026-10-22].',
    '[10] B. Frederickson, "implicit: Fast Python collaborative filtering for implicit datasets," GitHub repository. [Online]. Available: https://github.com/benfred/implicit. [Accessed: 2026-10-22].',
    '[11] Microsoft, "LightGBM documentation." [Online]. Available: https://lightgbm.readthedocs.io. [Accessed: 2026-10-22].',
    '[12] OpenCode, "OpenCode documentation." [Online]. Available: https://opencode.ai/docs/. [Accessed: 2026-10-24].',
]
for r_ in refs:
    P(r_, size=8, after=1)
doc.save(OUT)
print('saved', OUT)
