"""红宝书（《德语核心词汇与1000短语精解》OCR 结果）→ 每个词的「义项与用法」，私有，凭考试密码读取。

用法（在仓库根目录）：
  python -I scripts/book_usage.py <entries.json> exam_private/usage.json            只生成，打印统计
  python -I scripts/book_usage.py <entries.json> exam_private/usage.json --upload   生成并上传到 KV（bank:usage）
entries.json 是 德语\\导入\\核心词汇\\parse.py 的输出。书有版权，结果只放 gitignored 的 exam_private/ 和私有 KV，不进仓库。
输出：{词 id: {"us": [{"p": 句型, "zh": 意思, "ex": 例句, "exz": 例句翻译, "tip": 记忆提示}], "tip": 整词的记忆提示}}
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "scripts"))
from wikt_keys import word_keys  # noqa: E402

src, dest = Path(sys.argv[1]), Path(sys.argv[2])
E = json.loads(src.read_text(encoding="utf-8"))
W = json.loads((R / "docs/words.json").read_text(encoding="utf-8"))


def norm(s):
    s = re.sub(r"\(.*?\)|[/!?！？]|\s+", "", s.lower())
    return re.sub(r"^sich", "", s)


lib = {}
for w in W:
    for k in word_keys(w):
        lib.setdefault(norm(k), []).append(w["id"])


def fix(s):
    s = (s or "").replace("ı", "i").replace("十", "+")
    s = re.sub(r"\s+([,.?!;:])", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def tipclean(notes):
    out = []
    for n in notes or []:
        n = re.sub(r"^【记忆提示】\s*", "", fix(n))
        if n and not n.startswith("【英】"):
            out.append(n)
    return "；".join(out)


out, unmatched, multi = {}, [], 0
for e in E:
    head = e["word"].strip()
    if re.search(r"-,|^[A-ZÄÖÜa-zäöü]+-$", head):        # 前缀条目（Ab-, ab-）不是单词
        continue
    head = re.sub(r"[‘’'`´®]+", "", head)                   # OCR 留下的引号、符号
    ids = []
    for alt in re.split(r"[.,]\s+", head):                  # "nutzen. nützen" 两个写法
        ids += [i for i in lib.get(norm(alt), []) if i not in ids]
    if not ids:
        unmatched.append(head)
        continue
    us = []
    for s in e["senses"]:
        base = {"p": fix(s.get("phrase")), "zh": fix(s.get("zh")), "ex": "", "exz": "", "tip": tipclean(s.get("notes"))}
        cur = base if base["zh"] else None
        if cur:
            us.append(cur)
        for it in s.get("items", []):
            if it["type"] == "phrase":
                cur = {"p": fix(it["de"]), "zh": fix(it["zh"]), "ex": "", "exz": "", "tip": ""}
                us.append(cur)
            elif it["type"] == "example" and cur is not None and not cur["ex"] and re.search(r"[a-zäöüß]{3}", it["de"]):
                cur["ex"], cur["exz"] = fix(it["de"]), fix(it["zh"])
    us = [{k: v for k, v in u.items() if v} for u in us if u.get("zh")]
    if not us:
        continue
    rec = {"us": us}
    t = tipclean(e.get("notes"))
    if t:
        rec["tip"] = t
    multi += len(us) >= 2
    for i in ids:
        out[i] = rec
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"{len(E)} 条 → {len(out)} 个词（{multi} 条有 2 个以上用法）；没对上词库的 {len(unmatched)} 条：{unmatched[:30]}")
print("大小 KB", dest.stat().st_size // 1024)

if "--upload" in sys.argv:
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    p = subprocess.run([npx, "wrangler", "kv", "key", "put", "bank:usage", "--path", str(dest.resolve()), "--binding", "EXAM", "--remote"],
                       cwd=R / "worker", capture_output=True, text=True, encoding="utf-8", env={**os.environ, "CI": "1"})
    print("已上传" if p.returncode == 0 else "上传失败：" + (p.stderr or p.stdout)[-600:])
