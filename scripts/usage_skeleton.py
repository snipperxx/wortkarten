"""给已有词补「义项与用法」(use.us) 的骨架：挑出红宝书没覆盖、可能有多个用法的词，分成 N 批给生成代理。

用法（在仓库根目录）：python -I scripts/usage_skeleton.py [批数=8]
输出：wiktionary/gen/usNN.todo.json（gitignored）；代理写 data/usage_us/usNN.json，规范见 data/usage_us/SPEC.md，
自查 python -I scripts/usage_check.py data/usage_us/usNN.json；merge.py 会把 data/usage_us/*.json 并进 words.json。
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parent.parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
W = json.loads((R / "docs/words.json").read_text(encoding="utf-8"))
book_p = R / "exam_private/usage.json"            # 红宝书（私有）：App 里优先显示，这些词不用再写
BOOK = set(json.loads(book_p.read_text(encoding="utf-8"))) if book_p.exists() else set()
LV = {"A1": 0, "A2": 1, "B1": 2, "求职": 2, "办事": 2, "IT": 2, "B2": 3, "C1": 4}

rows = []
for w in W:
    u = w.get("use") or {}
    if w["id"] in BOOK or u.get("us"):
        continue
    nzh = len([x for x in re.split(r"[;；]", w.get("zh", "")) if x.strip()])
    multi = len(u.get("senses") or []) >= 2 or nzh >= 2
    if not (multi or w.get("pos") == "v"):       # 单义名词/形容词跳过；动词常有介词搭配，都给
        continue
    r = {k: w[k] for k in ("id", "lemma", "lv", "pos", "art", "zh", "gov") if w.get(k)}
    if u.get("senses"):
        r["senses"] = u["senses"]
    if w.get("ex"):
        r["ex"] = w["ex"][0]
    if u.get("col"):
        r["col"] = [c[0] for c in u["col"]]
    rows.append(r)

rows.sort(key=lambda r: (LV.get(r["lv"], 5), r["id"]))
out = R / "wiktionary/gen"
out.mkdir(parents=True, exist_ok=True)
for i in range(N):
    part = rows[i::N]                            # 轮流分，每批都是高频级别在前
    (out / f"us{i + 1:02d}.todo.json").write_text(json.dumps(part, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"{len(rows)} 个词（跳过红宝书 {len(BOOK)} 个）→ {N} 批，每批约 {len(rows) // N}")
