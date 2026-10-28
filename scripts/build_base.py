"""Merge parsed A1/A2/B1 entries into one cleaned base list with level tags."""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
D = Path(sys.argv[1])
load = lambda lv: json.loads((D / f"{lv}_raw.json").read_text(encoding="utf-8"))


def dehyphen(s):
    return re.sub(r"([a-zäöüß])- ([a-zäöüß])", r"\1\2", s)


def key(e):
    return re.sub(r"[^a-zäöüß]", "", e["lemma"].lower())


levels = {lv: {key(e) for e in load(lv)} for lv in ("A1", "A2")}
seen, out = set(), []
for lv in ("B1", "A2", "A1"):
    for e in load(lv):
        for f in ("hw", "lemma", "pl", "forms", "p2"):
            if f in e:
                e[f] = dehyphen(e[f])
        e["ex"] = [dehyphen(x) for x in e["ex"]]
        k = key(e)
        if not k or len(e["lemma"]) > 40 or k in seen or not re.match(r"^[A-Za-zÄÖÜäöü]", e["lemma"]) \
                or re.search(r"\d|→", e["lemma"]):
            continue
        seen.add(k)
        if e.get("kind") == "noun":
            pl = e["pl"]
            m = re.search(r"\s(die|der)\s+(\S+?),", " " + pl)
            if m:
                e["fem"] = m.group(2)
                pl = pl[: pl.find(m.group(1))].strip(" ,")
            e["pl"] = pl.strip(" ,")
        e["lv"] = "A1" if k in levels["A1"] else "A2" if k in levels["A2"] else "B1"
        e["id"] = f"w{len(out):04d}"
        out.append({f: e[f] for f in ("id", "lv", "kind", "lemma", "art", "pl", "fem", "aux", "p2", "forms", "hw", "ex") if e.get(f)})

(D / "base.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter
print(len(out), Counter(e["lv"] for e in out), Counter(e["kind"] for e in out))
print("no example:", sum(1 for e in out if not e.get("ex")))
for e in out[::300]:
    print(json.dumps(e, ensure_ascii=False))
