"""从 kaikki.org 的 Wiktionary 抽取数据里挑出词库用到的词，存成小文件，供 wikt_compare.py 核对。

用法（在仓库根目录，数据放在 gitignored 的 wiktionary/ 里）：
  python -I scripts/wikt_extract.py en wiktionary/kaikki-German.jsonl.gz wiktionary/en_subset.json
  python -I scripts/wikt_extract.py de wiktionary/dewikt/kaikki-Deutsch.jsonl.gz wiktionary/de_subset.json
en = 英文版 Wiktionary 的德语词条（词性、性、复数、助动词、Partizip II、英文义项）
de = 德语版 Wiktionary 的德语词条（同上 + 德语义项 + 中文译名）
数据许可 CC BY-SA；只用来核对，不把原文搬进词库。
"""
import gzip
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wikt_keys import word_keys  # noqa: E402

mode, src, dest = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
words = json.loads(Path("docs/words.json").read_text(encoding="utf-8"))
want = set()
for w in words:
    for k in word_keys(w):
        want.add(k)
        want.add(k.lower())
        want.add(k[:1].upper() + k[1:])

GENDER = {"masculine": "m", "feminine": "f", "neuter": "n", "plural-only": "p"}


def en_record(d):
    forms = d.get("forms", [])
    tags_of = [set(f.get("tags", [])) for f in forms]
    rec = {"pos": d.get("pos")}
    g = set()
    for h in d.get("head_templates", []):
        a = h.get("args", {})
        if h.get("name") == "de-noun":
            spec = a.get("1", "")
            first = spec.split(",")[0]
            for part in first.split(":"):
                letter = re.sub(r"\[.*?\]", "", part).strip()
                if letter in ("m", "f", "n", "p"):
                    g.add(letter)
            for key in ("g", "g2", "g3"):
                if a.get(key) in ("m", "f", "n", "p"):
                    g.add(a[key])
        exp = h.get("expansion", "")
        head = re.split(r"\((?:strong|weak|mixed|genitive|plural|no plural|indeclinable|uncountable)", exp)[0]
        for m in re.findall(r"\s(m|f|n|pl)(?=\s|$)", " " + head):
            g.add("p" if m == "pl" else m)
    for s in d.get("senses", []):
        for t in s.get("tags", []):
            if t in GENDER:
                g.add(GENDER[t])
    if g:
        rec["g"] = sorted(g)
    pl = []
    for f, t in zip(forms, tags_of):
        if "plural" in t and not ({"diminutive", "genitive", "dative", "accusative", "table-tags"} & t) \
                and not (f.get("source") and "nominative" not in t):
            if f["form"] not in pl and f["form"] not in ("-", "no-table-tags"):
                pl.append(f["form"])
    if pl:
        rec["pl"] = pl
    exp = " ".join(h.get("expansion", "") for h in d.get("head_templates", []))
    if "no plural" in exp or "uncountable" in exp:
        rec["nopl"] = 1
    aux = [f["form"] for f, t in zip(forms, tags_of) if t == {"auxiliary"} and f["form"] in ("haben", "sein")]
    if aux:
        rec["aux"] = sorted(set(aux))
    p2 = [f["form"] for f, t in zip(forms, tags_of) if {"participle", "past"} <= t and f["form"] not in ("-",)]
    if p2:
        rec["p2"] = list(dict.fromkeys(p2))
    pr3 = [f["form"] for f, t in zip(forms, tags_of) if t == {"present", "singular", "third-person"}]
    pt = [f["form"] for f, t in zip(forms, tags_of) if "past" in t and not ({"participle", "subjunctive"} & t)
          and not f.get("source")]
    if pr3:
        rec["pr3"] = list(dict.fromkeys(pr3))
    if pt:
        rec["pt"] = list(dict.fromkeys(pt))
    gl, formof = [], True
    for s in d.get("senses", []):
        st = set(s.get("tags", []))
        if not ("form-of" in st or s.get("form_of")):
            formof = False
        if "form-of" in st or s.get("form_of"):
            continue
        g_ = "; ".join(s.get("glosses", [])[-1:])
        if g_:
            q = [t for t in s.get("tags", []) if t in ("reflexive", "transitive", "intransitive", "colloquial",
                                                        "obsolete", "archaic", "regional", "dated", "rare")]
            gl.append((f"({','.join(q)}) " if q else "") + g_)
        if s.get("alt_of"):
            rec["alt_of"] = [a.get("word") for a in s["alt_of"]]
    if formof and d.get("senses"):
        rec["formof"] = 1
    rec["gl"] = gl[:8]
    return rec


def de_record(d):
    rec = {"pos": d.get("pos")}
    g = set()
    for t in d.get("tags", []):
        if t in GENDER:
            g.add(GENDER[t])
    if g:
        rec["g"] = sorted(g)
    pl, aux, p2 = [], [], []
    for f in d.get("forms", []):
        t = set(f.get("tags", []))
        if f.get("source"):
            continue
        if "plural" in t and "nominative" in t and f["form"] not in pl and f["form"] not in ("—", "-"):
            pl.append(f["form"])
        if "auxiliary" in t and f["form"] in ("haben", "sein"):
            aux.append(f["form"])
        if "participle-2" in t:
            p2.append(f["form"])
    if pl:
        rec["pl"] = pl
    if aux:
        rec["aux"] = sorted(set(aux))
    if p2:
        rec["p2"] = list(dict.fromkeys(p2))
    rec["gl"] = ["; ".join(s.get("glosses", [])) for s in d.get("senses", []) if s.get("glosses")][:10]
    zh = []
    for tr in d.get("translations", []):
        if tr.get("lang_code") in ("zh", "cmn") or tr.get("lang") in ("Chinesisch", "Mandarin"):
            w = tr.get("word", "")
            if w and w not in zh:
                zh.append(w + (f" [{tr['sense_index']}]" if tr.get("sense_index") else ""))
    if zh:
        rec["zh"] = zh
    return rec


out = {}
n = 0
with gzip.open(src, "rt", encoding="utf-8") as f:
    for line in f:
        n += 1
        if line.startswith('{"word": "'):         # 德语版：word 是第一个键，先粗筛省掉 json 解析
            j = line.find('"', 10)
            if line[10:j] not in want and "\\" not in line[10:j]:
                continue
        d = json.loads(line)
        w = d.get("word")
        if w not in want:
            continue
        if mode == "en" and d.get("lang_code") != "de":
            continue
        if mode == "de" and d.get("lang_code") not in ("de", None):
            continue
        out.setdefault(w, []).append(en_record(d) if mode == "en" else de_record(d))
        if n % 500000 == 0:
            print(n, len(out), flush=True)
dest.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print("lines", n, "matched words", len(out), "->", dest)
