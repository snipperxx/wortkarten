"""词库 vs Wiktionary：冠词、复数、助动词、Partizip II、动词变位、词性。输出 JSON 供人工复核。

用法（在仓库根目录，先跑 wikt_extract.py 生成 wiktionary/en_subset.json、de_subset.json）：
  python -I scripts/wikt_compare.py wiktionary/compare.json
"""
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
POSMAP = {"n": {"noun", "name"}, "v": {"verb"}, "adj": {"adj"}, "adv": {"adv"}, "prep": {"prep", "postp", "circumpos"},
          "conj": {"conj"}, "pron": {"pron", "det"}, "num": {"num"}, "art": {"article", "det"},
          "part": {"particle", "adv", "intj"}, "phr": None}
ART = {"der": "m", "die": "f", "das": "n"}


def our_plurals(w):
    s = w.get("pl_full") or ""
    return {re.sub(r"^die\s+", "", p.strip()) for p in s.split("/") if p.strip()} - {""}


issues = []


def add(w, kind, sev, ours, wikt, note=""):
    issues.append({"id": w["id"], "lv": w["lv"], "lemma": w["lemma"], "kind": kind, "sev": sev,
                   "ours": ours, "wikt": wikt, "zh": w["zh"], "note": note})


found = 0
for w in words:
    keys = word_keys(w)
    pos = w.get("pos", "")
    if re.search(r"\([^)]*$|\(Bsp\.|[“”]", w["lemma"]):
        add(w, "lemma 截断/乱码", 1, w["lemma"], "", "PDF 解析残留")
    en, de = entries(EN, keys, pos), entries(DE, keys, pos)
    if not en and not de:
        add(w, "查不到", 3 if w["lv"] in ("B2", "C1") else 4, w["lemma"], "", "两个 Wiktionary 都没有这个词条")
        continue
    found += 1
    allpos = {r["pos"] for r in en + de}
    want = POSMAP.get(pos)
    if want is not None and not (allpos & want):
        # 形容词当副词用、分词形容词等很常见，只在差得远时报
        soft = (pos in ("adj", "adv") and allpos & {"adj", "adv", "verb"}) or (pos == "part" and allpos & {"adv", "intj"})
        add(w, "词性", 4 if soft else 2, pos, sorted(allpos))
    if pos == "n":
        nouns = [r for r in en + de if r["pos"] in ("noun", "name")]
        g = set().union(*[set(r.get("g", [])) for r in nouns]) if nouns else set()
        art = w.get("art")
        plonly = "(Pl" in w["lemma"] or "Plural" in w["lemma"]
        if not art and not plonly:
            add(w, "缺冠词", 1, None, "".join(sorted(g)))
        elif art and g and not plonly:
            if ART[art] not in g and not ("p" in g and art == "die"):
                add(w, "冠词", 1, art, "".join(sorted(g)))
        # 复数：只看与我们冠词同性的词条（区分 der/die Leiter 这类同形词）
        same = [r for r in nouns if art and ART.get(art) in r.get("g", [])] or nouns
        wpl = {p for r in same for p in r.get("pl", [])}
        ours = our_plurals(w)
        if ours and wpl and not (ours & wpl) and not plonly:
            add(w, "复数", 1, sorted(ours), sorted(wpl))
        elif ours and not wpl and any(r.get("nopl") for r in same) and not plonly:
            add(w, "复数(维基说无复数)", 4, sorted(ours), "无复数")
        gens = {frozenset(r.get("g", [])) for r in nouns if r.get("g")}
        if len({x for x in gens if len(x) == 1}) > 1:
            add(w, "同形异性词", 3, art, ["/".join(sorted(x)) for x in gens], "确认中文释义对应这个冠词的义项")
    if pos == "v":
        verbs = [r for r in en + de if r["pos"] == "verb"]
        aux = {"haben": "hat", "sein": "ist"}
        waux = {aux[a] for r in verbs for a in r.get("aux", []) if a in aux}
        if w.get("aux") and waux and w["aux"] not in waux:
            add(w, "助动词", 1, w["aux"], sorted(waux))
        elif w.get("aux") and len(waux) == 2:
            add(w, "助动词(两者皆可)", 4, w["aux"], "hat/ist", "可在释义里注明")
        wp2 = {p for r in verbs for p in r.get("p2", [])}
        p2 = re.sub(r"^sich\s+", "", w.get("p2") or "")
        if p2 and wp2 and p2 not in wp2 and not any(x in wp2 for x in re.split(r"\s*/\s*", p2)):
            add(w, "Partizip II", 1, w["p2"], sorted(wp2))
        f = [re.sub(r"\s+", " ", re.sub(r"\bsich\b", "", x)).strip() for x in (w.get("forms") or "").split(",")]
        if len(f) == 3:
            pr3 = {p for r in verbs for p in r.get("pr3", [])}
            pt = {p for r in verbs for p in r.get("pt", [])}
            if pr3 and f[0] not in pr3 and not any(x.strip() in pr3 for x in f[0].split("/")):
                add(w, "现在时 er/sie/es", 2, f[0], sorted(pr3))
            if pt and f[1] not in pt and not any(x.strip() in pt for x in f[1].split("/")):
                add(w, "Präteritum", 2, f[1], sorted(pt))
        if len(f) == 3 and f[2] and w.get("p2") and not f[2].endswith(w["p2"]):
            add(w, "forms 与 p2 不一致", 2, f[2], w["p2"])
        if not w.get("aux") and verbs and not w["lemma"].startswith(("sich ",)):
            add(w, "缺助动词", 3, None, sorted(waux))

order = {1: 0, 2: 1, 3: 2, 4: 3}
issues.sort(key=lambda i: (order[i["sev"]], i["kind"], i["id"]))
Path(sys.argv[1]).write_text(json.dumps(issues, ensure_ascii=False, indent=0), encoding="utf-8")
from collections import Counter  # noqa: E402
print("found", found, "of", len(words))
print(Counter((i["sev"], i["kind"]) for i in issues))
