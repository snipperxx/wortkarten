"""找词库里缺的常用词：开源词频表（新闻 + 字幕）→ 用 Wiktionary 把词形归到原形 → 去掉词库已有的 → 按频率排序。

用法（在仓库根目录；数据都在 gitignored 的 wiktionary/ 里）：
  python -I scripts/wikt_missing.py wiktionary/kaikki-German.jsonl.gz \
      wiktionary/freq_news/deu_news_2023_1M/deu_news_2023_1M-words.txt wiktionary/freq_subs/de_50k.txt \
      wiktionary/missing.json
词频：Leipzig Corpora Collection deu_news_2023_1M（CC BY）、FrequencyWords de_50k（OpenSubtitles 2018，CC BY-SA）。
"""
import gzip
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wikt_keys import word_keys  # noqa: E402

src, news_f, subs_f, dest = map(Path, sys.argv[1:5])
words = json.loads(Path("docs/words.json").read_text(encoding="utf-8"))
have = set()
for w in words:
    for k in word_keys(w):
        have.add(k.lower())
        for part in k.split():          # "spazieren gehen" 之类也记下第一个词
            pass

KEEP_POS = {"noun", "verb", "adj", "adv", "prep", "conj", "pron", "det", "num", "particle", "postp"}
OUT_POS = {"noun", "verb", "adj", "adv", "prep", "conj"}   # 代词、冠词、数词不做卡片
BAD_TAGS = {"vulgar", "archaic", "obsolete", "dated", "Austria", "Switzerland", "Swiss", "Austrian", "dialectal",
            "regional", "rare", "derogatory", "offensive", "slur", "Bavarian", "historical", "poetic", "Southern-Germany",
            "Northern-Germany", "Liechtenstein", "South-Tyrol"}
SKIP_TABLE = {"table-tags", "inflection-template", "class", "auxiliary"}

lemmas = {}                     # (word, pos) -> info
form2lem = defaultdict(set)     # form -> {(lemma, pos)}
with gzip.open(src, "rt", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        if d.get("lang_code") != "de":
            continue
        w, pos = d.get("word", ""), d.get("pos")
        senses = d.get("senses", [])
        fo = [s for s in senses if s.get("form_of") or "form-of" in s.get("tags", [])]
        if fo and len(fo) == len(senses):
            for s in fo:
                for t in s.get("form_of", []):
                    if t.get("word"):
                        form2lem[w].add((t["word"], pos))
            continue
        if pos not in KEEP_POS or not senses:
            continue
        good = [s for s in senses if not (set(s.get("tags", [])) & BAD_TAGS) and not s.get("alt_of")
                and "abbreviation" not in s.get("tags", []) and "form-of" not in s.get("tags", [])]
        key = (w, pos)
        info = lemmas.setdefault(key, {"w": w, "pos": pos, "gl": [], "alt": False})
        if not good:
            info["alt"] = info["alt"] or bool([s for s in senses if s.get("alt_of")]) or True
            info.setdefault("allbad", True)
        else:
            info["allbad"] = False
            info["gl"] += [s["glosses"][-1] for s in good if s.get("glosses")][:6]
        form2lem[w].add(key)
        for fm in d.get("forms", []):
            t = set(fm.get("tags", []))
            fw = fm.get("form", "")
            if t & SKIP_TABLE or "canonical" in t or fw in ("-", "", w) or not re.fullmatch(r"[A-Za-zÄÖÜäöüß-]+", fw):
                continue
            form2lem[fw].add(key)               # 只收单个词的词形（可分动词的 "fährt ab" 不拆开）


def load(path, sep, colw, colf, lower):
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        p = line.split(sep)
        if len(p) <= max(colw, colf):
            continue
        try:
            out[p[colw]] = out.get(p[colw], 0) + int(p[colf])
        except ValueError:
            pass
    tot = sum(out.values())
    return {k: v * 1e6 / tot for k, v in out.items()}


news = load(news_f, "\t", 1, 2, False)
subs = load(subs_f, " ", 0, 1, True)
lower_index = defaultdict(set)
for form, ls in form2lem.items():
    lower_index[form.lower()] |= ls

def cands_news(form):
    ls = form2lem.get(form) or (form2lem.get(form.lower()) if form[:1].isupper() else None) or ()
    return {l for l in ls if l in lemmas}


def cands_subs(form):
    return {l for l in lower_index.get(form, ()) if l in lemmas}


# 两遍：先只算没有歧义的词形（只属于一个原形），再把有歧义的词形按第一遍的比例分配，
# 这样 "hast" 归 haben 而不是 hasten，"Stunden" 归 Stunde 而不是 stunden
uniq = defaultdict(float)
for src_, cf in ((news, cands_news), (subs, cands_subs)):
    for form, pm in src_.items():
        ls = cf(form)
        if len(ls) == 1:
            uniq[next(iter(ls))] += pm
score = defaultdict(lambda: [0.0, 0.0])
for col, (src_, cf) in enumerate(((news, cands_news), (subs, cands_subs))):
    for form, pm in src_.items():
        ls = cf(form)
        if not ls:
            continue
        tot = sum(uniq[l] for l in ls)
        for l in ls:
            score[l][col] += pm * (uniq[l] / tot if tot else 1 / len(ls))

rows = []
for key, (n, s) in score.items():
    info = lemmas[key]
    w, pos = key
    if info.get("allbad") or not info["gl"] or pos not in OUT_POS:
        continue
    if pos == "noun" and not w[:1].isupper():
        continue
    if pos != "noun" and w[:1].isupper():
        continue
    if not re.fullmatch(r"[A-Za-zÄÖÜäöüß-]+", w) or len(w) < 2 or w.isupper():
        continue
    rows.append({"w": w, "pos": pos, "news": round(n, 2), "subs": round(s, 2), "score": round(n + s, 2),
                 "have": w.lower() in have, "gl": info["gl"][:3]})
rows.sort(key=lambda r: -r["score"])
for i, r in enumerate(rows):
    r["rank"] = i + 1
dest.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
for N in (2000, 4000, 6000, 8000, 10000, 12000, 15000, 20000):
    top = rows[:N]
    print(N, "have", sum(r["have"] for r in top), "missing", sum(not r["have"] for r in top))
