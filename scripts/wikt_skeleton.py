"""新词骨架：wikt_missing.py 选出的词 → 从 Wiktionary 填好词性、冠词、复数、助动词、Partizip II、变位，
分成几批给生成代理补中文释义、例句和用法（规范见 data/adv/SPEC.md）。

用法（在仓库根目录）：python -I scripts/wikt_skeleton.py wiktionary/new_words.json wiktionary/gen 8
输出 wiktionary/gen/freqNN.todo.json（gitignored）；hint_en / hint_de 只给代理参考，不进词库。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wikt_keys import entries  # noqa: E402

src, outdir, n = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
NEW = json.loads(src.read_text(encoding="utf-8"))
EN = json.loads(Path("wiktionary/en_subset.json").read_text(encoding="utf-8"))
DE = json.loads(Path("wiktionary/de_subset.json").read_text(encoding="utf-8"))
POS = {"noun": "n", "verb": "v", "adj": "adj", "adv": "adv", "conj": "conj", "prep": "prep"}
ART = {"m": "der", "f": "die", "n": "das"}
AUX = {"haben": "hat", "sein": "ist"}

rows = []
for c in NEW:
    w, pos = c["w"], POS[c["pos"]]
    want = {"n": ("noun",), "v": ("verb",)}.get(pos, (c["pos"],))
    en = [r for r in entries(EN, [w], pos) if r["pos"] in want]
    de = [r for r in entries(DE, [w], pos) if r["pos"] in want]
    s = {"lv": c["lv"], "lemma": w, "pos": pos}
    if pos == "n":
        gs = []
        for r in de + en:
            for g in r.get("g", []):
                if g in ART and ART[g] not in gs:
                    gs.append(ART[g])
        if gs:
            s["art"] = gs[0]
        if len(gs) > 1:
            s["art_options"] = gs
        pl = next((p for r in de + en for p in r.get("pl", []) if p not in ("—", "-", w + "?")), None)
        if pl and not any(r.get("nopl") for r in en[:1]):
            s["pl_full"] = "die " + pl
    if pos == "v":
        aux = []
        for r in de + en:
            for a in r.get("aux", []):
                if a in AUX and AUX[a] not in aux:
                    aux.append(AUX[a])
        p2 = next((p for r in de + en for p in r.get("p2", [])), "")
        pr3 = next((p for r in en for p in r.get("pr3", [])), "")
        pt = next((p for r in en for p in r.get("pt", [])), "")
        if p2:
            s["p2"] = p2
        if len(aux) == 1:
            s["aux"] = aux[0]
            if pr3 and pt and p2:
                s["forms"] = f"{pr3}, {pt}, {aux[0]} {p2}"
        elif aux:
            s["aux_options"] = aux
            s["forms_parts"] = [pr3, pt, p2]
        elif pr3 or pt:
            s["forms_parts"] = [pr3, pt, p2]
    s["hint_en"] = [g[:120] for r in en for g in r.get("gl", [])][:5]
    s["hint_de"] = [g[:160] for r in de for g in r.get("gl", [])][:4]
    rows.append(s)

outdir.mkdir(parents=True, exist_ok=True)
for i in range(n):
    part = rows[i::n]
    (outdir / f"freq{i + 1:02d}.todo.json").write_text(json.dumps(part, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter  # noqa: E402
print(len(rows), "词，", n, "批；名词有冠词", sum(1 for r in rows if r.get("art")), "/", sum(1 for r in rows if r["pos"] == "n"),
      "；动词有完整 forms", sum(1 for r in rows if r.get("forms")), "/", sum(1 for r in rows if r["pos"] == "v"))
print(Counter(r["lv"] for r in rows))
