"""base.json + chunk*_zh.json + chunk*_use.json + extra.json + overrides.json -> docs/words.json

用法：python -I scripts/merge.py .   （在仓库根目录）
所有人工 / 反馈修正都写进 data/overrides.json，不直接改 docs/words.json（重新合并会被覆盖）。"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
V = Path(sys.argv[1])
D = V / "data"
base = json.loads((D / "base.json").read_text(encoding="utf-8"))
zh, use = {}, {}
for i in range(8):
    zh.update(json.loads((D / f"chunk{i}_zh.json").read_text(encoding="utf-8")))
    f = D / f"chunk{i}_use.json"
    if f.exists():
        use.update(json.loads(f.read_text(encoding="utf-8")))


def stems(w):
    core = re.sub(r"\(.*?\)|^sich |^(der|die|das) ", "", w["lemma"]).strip().lower()
    out = {core[:max(4, len(core) - 3)] if len(core) > 5 else core}
    for f in (w.get("p2", ""), w.get("forms", ""), w.get("pl_full", "")):
        for tok in re.findall(r"[a-zäöüß]{3,}", f.lower()):
            if tok not in ("hat", "ist", "die", "der", "das"):
                out.add(tok[:max(4, len(tok) - 2)])
    return out


def fits(sentence, w):
    s = sentence.lower()
    return len(sentence) >= 12 and not sentence[0].islower() and any(st and st in s for st in stems(w))


out, dropped, exfix = [], 0, 0
for w in base:
    z = zh.get(w["id"], {})
    regional = re.search(r"[（(][^）)]*(瑞士|奥|CH|\bA\b)[^）)]*[）)]", z.get("zh", "")) and "德" not in z.get("zh", "")
    if z.get("drop") or not z.get("zh") or regional:   # 只在瑞士/奥地利用的词不要
        dropped += 1
        continue
    if z.get("fix"):
        m = re.match(r"^(der|die|das)\s+(.+)$", z["fix"])
        w["lemma"] = m.group(2) if m else z["fix"]
        if m:
            w["art"] = m.group(1)
    w["zh"], w["pos"] = z["zh"], z.get("pos", "")
    for k in ("pl_full", "gov"):
        if z.get(k):
            w[k] = z[k]
    ex = [re.sub(r"^[-–]\s*", "", e) for e in w.get("ex", [])]
    good = [e for e in ex if fits(e, w)]
    if ex and good and good[0] == ex[0]:
        w["ex_zh"] = z.get("ex_zh", "")
    if good != ex:
        exfix += 1
    w["ex"] = good[:2]
    if not w.get("ex_zh"):
        w.pop("ex_zh", None)
    u = use.get(w["id"], {})
    u = {k: u[k] for k in ("senses", "col", "tip") if u.get(k)}   # 不要英文对应（用户 10-28）
    if u:
        w["use"] = u
    if w.get("kind") == "noun" and w.get("pos") != "n":
        w.pop("art", None)
    w.pop("hw", None)
    out.append(w)

extra = json.loads((D / "extra.json").read_text(encoding="utf-8"))
out += extra
for w in out:
    w.pop("kind", None)

# 修正：{"w0123": {"zh": "...", "use": {"tip": "..."}, "_note": "#5"}, "w0999": {"_drop": true}, "_new": [{...}]}
# 字段值为 null = 删掉这个字段；use 按子字段合并；以 _ 开头的键是备注，不进词库
ov_path = D / "overrides.json"
overrides = json.loads(ov_path.read_text(encoding="utf-8")) if ov_path.exists() else {}
by_id = {w["id"]: w for w in out}
applied = 0
for wid, patch in overrides.items():
    if wid.startswith("_"):
        continue
    w = by_id.get(wid)
    if w is None:
        sys.exit(f"overrides.json: 找不到 {wid}")
    if patch.get("_drop"):
        out.remove(w)
    for k, v in patch.items():
        if k.startswith("_"):
            continue
        if k == "use" and isinstance(v, dict):
            u = {**w.get("use", {}), **v}
            w["use"] = {kk: vv for kk, vv in u.items() if vv is not None}
        elif v is None:
            w.pop(k, None)
        else:
            w[k] = v
    applied += 1
for w in overrides.get("_new", []):
    if w["id"] in by_id:
        sys.exit(f"overrides.json: _new 里的 {w['id']} 已存在")
    out.append(w)

dest = V / "docs" / "words.json"
dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
from collections import Counter
print(len(out), "words; dropped", dropped, "; examples trimmed on", exfix, "; with usage", sum(1 for w in out if "use" in w),
      "; overrides", applied, "+ new", len(overrides.get("_new", [])))
print(Counter(w["lv"] for w in out), Counter(w.get("pos") for w in out).most_common(8))
print("size KB", dest.stat().st_size // 1024)
