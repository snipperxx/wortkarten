"""中文释义初筛：用 CC-CEDICT 把 zh 译回英文，和 Wiktionary 英文义项比重合度，挑出需要人工看的词。

用法（在仓库根目录）：python -I scripts/wikt_zh_screen.py wiktionary/zh_review.tsv
只是初筛（重合为 0 不代表错，有重合也不代表全对），结果要人工复核。
"""
import gzip
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wikt_keys import entries, word_keys  # noqa: E402

words = json.loads(Path("docs/words.json").read_text(encoding="utf-8"))
EN = json.loads(Path("wiktionary/en_subset.json").read_text(encoding="utf-8"))
DE = json.loads(Path("wiktionary/de_subset.json").read_text(encoding="utf-8"))

STOP = set("""a an the of to in on at by for with from as or and be is are was one oneself one's sb sth someone something
which that this it its into out up off over about who what when where how not no very more most some any other such
etc used use usu e g i ie also especially esp make do have get give take put go come form way kind thing person
people state act action quality being having""".split())


def stem(t):
    for suf in ("ings", "ing", "edly", "ed", "ly", "ies", "es", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[: -len(suf)] + ("y" if suf == "ies" else "")
    return t


def toks(s):
    s = re.sub(r"\(.*?\)", " ", s.lower())
    return {stem(t) for t in re.findall(r"[a-z]+", s) if t not in STOP and len(t) > 1}


CED = {}
with gzip.open("wiktionary/cedict/cedict.txt.gz", "rt", encoding="utf-8") as f:
    for line in f:
        if line.startswith("#"):
            continue
        m = re.match(r"(\S+) (\S+) \[[^\]]*\] /(.*)/", line)
        if not m:
            continue
        defs = [d for d in m.group(3).split("/") if not d.startswith(("variant of", "old variant", "surname", "CL:"))]
        CED.setdefault(m.group(2), set()).update(toks(" ".join(defs)))
MAXLEN = 6


def zh_toks(seg):
    seg = re.sub(r"[（(][^）)]*[）)]|[…\.~～]+|[「」“”\"'《》]", "", seg).strip()
    seg = re.sub(r"^(使|被|对|与|向|把|给|在)|(的|地|得|者|性|化)$", "", seg) if seg not in CED else seg
    if seg in CED:
        return CED[seg]
    out, i = set(), 0
    while i < len(seg):
        for L in range(min(MAXLEN, len(seg) - i), 0, -1):
            if seg[i:i + L] in CED and (L > 1 or not out):
                out |= CED[seg[i:i + L]]
                i += L
                break
        else:
            i += 1
    return out


rows = []
stat = {"no_en": 0, "zero": 0, "first_missed": 0, "ok": 0}
for w in words:
    keys = word_keys(w)
    en, de = entries(EN, keys, w["pos"]), entries(DE, keys, w["pos"])
    gl = [g for r in en for g in r.get("gl", [])]
    dezh = [z for r in de for z in r.get("zh", [])]
    segs = [s for s in re.split(r"[；;，,、/]", w["zh"]) if s.strip()]
    T = set().union(*[zh_toks(s) for s in segs]) if segs else set()
    if dezh:
        zchars = re.sub(r"[^一-鿿]", "", w["zh"])
        if any(any(z[i:i + 2] in zchars for i in range(len(z) - 1)) for z in dezh):
            stat["ok"] += 1
            continue
    if not gl:
        stat["no_en"] += 1
        if de and w["pos"] != "phr":
            rows.append(("no_en", w, [g[:90] for r in de for g in r.get("gl", [])][:4], dezh))
        continue
    E = set().union(*[toks(g) for g in gl[:8]])
    E1 = toks(gl[0])
    if not (T & E):
        stat["zero"] += 1
        rows.append(("zero", w, gl[:4], dezh))
    elif not (T & E1) and len(gl) > 1:
        stat["first_missed"] += 1
        rows.append(("first", w, gl[:4], dezh))
    else:
        stat["ok"] += 1
print(stat)
with open(sys.argv[1], "w", encoding="utf-8") as f:
    for kind, w, gl, dezh in rows:
        f.write("\t".join([kind, w["id"], w["lv"], w["pos"], (w.get("art") or "") + " " + w["lemma"], w["zh"],
                           " | ".join(g[:80] for g in gl), " ".join(dezh[:4])]) + "\n")
