"""校验「义项与用法」文件：data/usage_us/<名字>.json = {词 id: [{p, zh, ex, exz}, …]}（给生成代理自查用）

用法（在仓库根目录）：python -I scripts/usage_check.py data/usage_us/us01.json
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parent.parent
W = {w["id"]: w for w in json.loads((R / "docs/words.json").read_text(encoding="utf-8"))}
ZH_OK = {"Gen", "Dat", "Akk", "Nom", "Pl", "GmbH", "AG", "BIP", "IT", "KI", "EU", "DSGVO", "App", "PC", "Sie", "du", "Python", "Java", "JavaScript", "LinkedIn", "SAP", "Excel"}  # 专有名词可以留
f = Path(sys.argv[1])
data = json.loads(f.read_text(encoding="utf-8"))
bad = []


def stems(w):
    core = re.sub(r"\(.*?\)|^sich |^(der|die|das) |[-/…]", " ", w["lemma"].lower()).split()
    out = {t[:max(3, len(t) - 3)] for t in core if len(t) >= 3}
    for fm in (w.get("p2", ""), w.get("forms", ""), w.get("pl_full", "")):
        out |= {t[:max(4, len(t) - 2)] for t in re.findall(r"[a-zäöüß]{3,}", (fm or "").lower()) if t not in ("hat", "ist", "die", "der", "das", "sich")}
    return out


for wid, us in data.items():
    w = W.get(wid)
    if not w:
        bad.append(f"{wid}：词库里没有这个 id")
        continue
    tag = f"{wid} {w['lemma']}"
    if not isinstance(us, list) or not 2 <= len(us) <= 4:
        bad.append(f"{tag}：要 2–4 条（只有一个用法就不要写这个词）")
        continue
    if len({x.get("zh") for x in us if isinstance(x, dict)}) < len(us):
        bad.append(f"{tag}：中文意思重复")
    for x in us:
        if not isinstance(x, dict) or set(x) - {"p", "zh", "ex", "exz"} or not all(x.get(k) for k in ("zh", "ex", "exz")):
            bad.append(f"{tag}：每条要有 zh / ex / exz（p 可选），不能有别的字段")
            continue
        if [t for t in re.findall(r"[A-Za-z]{2,}", x["zh"] + x["exz"]) if t not in ZH_OK]:
            bad.append(f"{tag}：中文里有拉丁字母：{x['zh']} / {x['exz']}")
        e = x["ex"]
        if len(e) < 12 or not e[0].isupper() or not re.search(r"[.!?“\"]$", e):
            bad.append(f"{tag}：例句要完整（大写开头、句号结尾）：{e}")
        short = [t for t in re.sub(r"\(.*?\)|^sich |^(der|die|das) |[-/…]", " ", w["lemma"].lower()).split() if len(t) < 3]
        if not any(s in e.lower() or s in re.sub(r"[^a-zäöüß]", "", e.lower()) for s in stems(w)) \
                and not any(re.search(rf"(?<![a-zäöüß]){re.escape(t)}(?![a-zäöüß])", e.lower()) for t in short):   # ja / um / zu 这类两个字母的词按整词找
            bad.append(f"{tag}：例句里没有这个词：{e}")
print(f"{f.name}: {len(data)} 个词，有问题 {len(bad)} 处")
for b in bad[:80]:
    print("  ✗", b)
sys.exit(1 if bad else 0)
