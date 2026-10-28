"""发布前校验：词库、修正文件、更新日志、页面脚本。任何一项不过就以非 0 退出，不发布。

用法：python -I scripts/check.py   （在仓库根目录）
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parent.parent
errors, warnings = [], []
POS = {"n", "v", "adj", "adv", "prep", "conj", "pron", "num", "art", "part", "phr", ""}

# 词库
try:
    words = json.loads((R / "docs/words.json").read_text(encoding="utf-8"))
except Exception as e:
    sys.exit(f"✗ docs/words.json 不是合法 JSON：{e}")
ids = [w.get("id") for w in words]
if len(words) < 3000:
    errors.append(f"词数只有 {len(words)}，少于 3000，可能误删")
dup = {i for i in ids if ids.count(i) > 1} if len(ids) != len(set(ids)) else set()
if dup:
    errors.append(f"重复 id：{sorted(dup)[:10]}")
for w in words:
    tag = f"{w.get('id')} {w.get('lemma')}"
    for k in ("id", "lemma", "zh", "lv"):
        if not isinstance(w.get(k), str) or not w[k].strip():
            errors.append(f"{tag}：缺少 {k}")
    if w.get("art") not in (None, "der", "die", "das"):
        errors.append(f"{tag}：冠词 {w.get('art')!r} 不对")
    if w.get("aux") not in (None, "hat", "ist"):
        errors.append(f"{tag}：助动词 {w.get('aux')!r} 不对")
    if w.get("pos") not in POS:
        errors.append(f"{tag}：词性 {w.get('pos')!r} 不认识")
    if not isinstance(w.get("ex", []), list) or any(not isinstance(e, str) for e in w.get("ex", [])):
        errors.append(f"{tag}：ex 必须是字符串列表")
    u = w.get("use")
    if u is not None:
        if not isinstance(u, dict) or set(u) - {"senses", "col", "tip"}:
            errors.append(f"{tag}：use 只能有 senses / col / tip")
        elif any(not (isinstance(c, list) and len(c) == 2) for c in u.get("col", [])):
            errors.append(f"{tag}：col 每项必须是 [德语, 中文]")
    if re.search(r"<\s*script|javascript:", json.dumps(w, ensure_ascii=False), re.I):
        errors.append(f"{tag}：内容里有脚本")

# 发音索引：新词没有音频只警告（会退回浏览器语音）
audio = json.loads((R / "docs/audio/index.json").read_text(encoding="utf-8"))
missing = [i for i in ids if i not in audio]
if missing:
    warnings.append(f"{len(missing)} 个词没有预录发音（会用浏览器语音）：{missing[:5]}")

# 修正文件
try:
    ov = json.loads((R / "data/overrides.json").read_text(encoding="utf-8"))
    if not isinstance(ov, dict):
        errors.append("data/overrides.json 必须是对象")
except Exception as e:
    errors.append(f"data/overrides.json 不是合法 JSON：{e}")

# 更新日志
try:
    log = json.loads((R / "docs/changelog.json").read_text(encoding="utf-8"))
    if not log or any(not isinstance(e.get("items"), list) or not e.get("date") for e in log):
        errors.append("docs/changelog.json 格式不对（每条要有 date 和 items）")
except Exception as e:
    errors.append(f"docs/changelog.json 不是合法 JSON：{e}")

# 页面脚本能解析
html = (R / "docs/index.html").read_text(encoding="utf-8")
scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
if not scripts or "APP_VERSION" not in html:
    errors.append("docs/index.html 里找不到主脚本或 APP_VERSION")
else:
    js = "new (require('vm').Script)(require('fs').readFileSync(0, 'utf8'))"
    try:
        p = subprocess.run(["node", "-e", js], input=scripts[-1], text=True, encoding="utf-8", capture_output=True, timeout=60)
        if p.returncode:
            errors.append("docs/index.html 脚本语法错误：" + (p.stderr.strip().splitlines() or ["?"])[-1])
    except FileNotFoundError:
        warnings.append("没有 node，跳过页面脚本语法检查")
sw = (R / "docs/sw.js").read_text(encoding="utf-8")
if 'startsWith("wortkarten-")' not in sw:
    errors.append("sw.js 必须只清理 wortkarten- 开头的缓存（同域名下有送报 App）")

for w_ in warnings:
    print("⚠", w_)
if errors:
    for e in errors[:40]:
        print("✗", e)
    sys.exit(f"校验失败：{len(errors)} 个问题")
print(f"✓ 校验通过：{len(words)} 个词")
