"""B2 / C1 词：data/adv/*.json（按主题生成的原始词条）→ data/adv_words.json（去重、校验、分配固定 id）

用法：python -I scripts/build_adv.py .   （在仓库根目录）
- 和现有词库（base + extra）重复的、主题文件之间重复的都去掉（同一个词在 B2 和 C1 都出现时保留 B2）。
- id 是 y0000 起，按 lemma 固定：已经分配过的词重跑时 id 不变（读旧的 adv_words.json），发音包编号也就不变。
- 有问题的词条直接丢弃并打印原因，不会进词库。
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
D = R / "data"
OUT = D / "adv_words.json"
POS = {"n", "v", "adj", "adv", "prep", "conj", "phr", "pron", "part"}
LV_RANK = {"B2": 0, "C1": 1}


def key(lemma):
    s = re.sub(r"\(.*?\)", "", lemma.lower())
    s = re.sub(r"^(sich|der|die|das)\s+", "", s.strip())
    return re.sub(r"[^a-zäöüß]", "", s)


def stems(w):
    core = key(w["lemma"])
    out = {core[:max(4, len(core) - 3)] if len(core) > 5 else core}
    for f in (w.get("p2", ""), w.get("forms", ""), w.get("pl_full", "")):
        for tok in re.findall(r"[a-zäöüß]{3,}", f.lower()):
            if tok not in ("hat", "ist", "die", "der", "das"):
                out.add(tok[:max(4, len(tok) - 2)])
    # 多词的（短语、je … desto、darüber hinaus）：任一实词出现即可
    if w.get("pos") == "phr" or re.search(r"[\s…]", w["lemma"]):
        out |= {t[:max(3, len(t) - 2)] for t in re.findall(r"[a-zäöüß]{3,}", w["lemma"].lower())
                if t not in ("sich", "jemanden", "jemandem", "etwas", "einer", "eines", "der", "die", "das", "den", "dem")}
    return {s for s in out if s}


# 释义里允许出现的拉丁字母缩写（语法标记、德国机构缩写、中文里通用的 GDP 等）
ZH_OK = {"Gen", "Dat", "Akk", "Nom", "Pl", "GmbH", "AG", "BIP", "GDP", "IT", "KI", "EU", "DSGVO", "App", "PC", "CO", "Sie", "du"}


def problems(w):
    p = []
    for k in ("lv", "lemma", "pos", "zh"):
        if not isinstance(w.get(k), str) or not w[k].strip():
            p.append(f"缺 {k}")
    if p:
        return p
    if w["lv"] not in LV_RANK:
        p.append(f"级别 {w['lv']}")
    if w["pos"] not in POS:
        p.append(f"词性 {w['pos']}")
    if w["pos"] == "n" and w.get("art") not in ("der", "die", "das"):
        p.append("名词缺冠词")
    if w["pos"] == "v" and (w.get("aux") not in ("hat", "ist") or not w.get("p2")):
        p.append("动词缺 aux/p2")
    if w.get("art") not in (None, "der", "die", "das"):
        p.append(f"冠词 {w.get('art')}")
    ex = w.get("ex")
    if not isinstance(ex, list) or not ex or not all(isinstance(e, str) and len(e) >= 12 for e in ex):
        p.append("例句")
    else:
        s = ex[0].lower()
        flat = re.sub(r"[^a-zäöüß]", "", s)
        if not any(st in s or st in flat for st in stems(w)):
            p.append("例句里没有这个词")
    if not w.get("ex_zh"):
        p.append("缺例句翻译")
    if [t for t in re.findall(r"[A-Za-z]{2,}", w["zh"]) if t not in ZH_OK]:
        p.append("释义里有拉丁字母")
    u = w.get("use")
    if u is not None and (not isinstance(u, dict) or set(u) - {"senses", "col", "tip"}
                          or any(not (isinstance(c, list) and len(c) == 2 and all(isinstance(x, str) for x in c)) for c in u.get("col", []))):
        p.append("use 格式")
    if re.search(r"<\s*script|javascript:", json.dumps(w, ensure_ascii=False), re.I):
        p.append("脚本")
    return p


existing = set()
for f in ("base.json", "extra.json"):
    for w in json.loads((D / f).read_text(encoding="utf-8")):
        existing.add(key(w["lemma"]))
zh_fix = {}
for i in range(8):
    zh_fix.update(json.loads((D / f"chunk{i}_zh.json").read_text(encoding="utf-8")))
for v in zh_fix.values():
    if v.get("fix"):
        existing.add(key(v["fix"]))

old_ids = {}
if OUT.exists():
    old_ids = {key(w["lemma"]): w["id"] for w in json.loads(OUT.read_text(encoding="utf-8"))}

cand, bad, dup_ex, dup_in = {}, [], 0, 0
for f in sorted((D / "adv").glob("*.json")):
    if ".part" in f.name:
        continue
    try:
        rows = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"✗ {f.name} 不是合法 JSON：{e}")
    for w in rows:
        if not isinstance(w, dict):
            continue
        w = {k: (v.strip() if isinstance(v, str) else v) for k, v in w.items() if v not in (None, "", [], {})}
        pr = problems(w)
        if pr:
            bad.append(f"{f.stem}: {w.get('lemma')} — {', '.join(pr)}")
            continue
        k = key(w["lemma"])
        if k in existing:
            dup_ex += 1
            continue
        if k in cand:
            dup_in += 1
            if LV_RANK[w["lv"]] < LV_RANK[cand[k]["lv"]]:
                cand[k] = {**w, "t": f.stem}
            continue
        w["ex"] = w["ex"][:1]
        if w.get("use") and not w["use"].get("senses"):
            w["use"].pop("senses", None)
        cand[k] = {**w, "t": f.stem}

used = set(old_ids.values())
nxt = max([int(i[1:]) for i in used] + [-1]) + 1
out = []
for k, w in sorted(cand.items(), key=lambda kv: (LV_RANK[kv[1]["lv"]], kv[1]["t"], kv[0])):
    if k in old_ids:
        wid = old_ids[k]
    else:
        wid = f"y{nxt:04d}"
        nxt += 1
    w.pop("t", None)
    out.append({"id": wid, **{f: w[f] for f in ("lv", "lemma", "art", "pl_full", "pos", "aux", "p2", "forms", "gov", "zh", "ex", "ex_zh", "use") if f in w}})
out.sort(key=lambda w: w["id"])
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter
print(f"{len(out)} 个 B2/C1 词 {dict(Counter(w['lv'] for w in out))}；和旧词库重复 {dup_ex}，主题间重复 {dup_in}，丢弃 {len(bad)}")
for b in bad[:60]:
    print("  ✗", b)
if len(bad) > 60:
    print(f"  … 还有 {len(bad) - 60} 条")
