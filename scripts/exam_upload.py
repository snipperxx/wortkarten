"""把编译好的私有题库上传到 Cloudflare KV（wortkarten-exam，绑定 EXAM），App 凭密码读取。

用法（在仓库根目录，wrangler 已登录）：
  python -I scripts/exam_upload.py exam_private/out          上传 exam.json 和新的 / 改过的音频
  python -I scripts/exam_upload.py --clear                   删除线上题库索引（音频留着，App 里看到“题库是空的”）

密码在 exam_private/KEY.txt（Worker 的 secret EXAM_KEY）；用户在 App「考试」页输入一次，存在本机。
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parent.parent
NPX = "npx.cmd" if sys.platform == "win32" else "npx"


def wr(*args):
    p = subprocess.run([NPX, "wrangler", "kv", *args, "--binding", "EXAM", "--remote"], cwd=R / "worker",
                       capture_output=True, text=True, encoding="utf-8", env={**os.environ, "CI": "1"})
    if p.returncode:
        sys.exit("wrangler 出错：" + (p.stderr or p.stdout)[-800:])
    return p.stdout


if sys.argv[1:] == ["--clear"]:
    wr("key", "delete", "bank:index")
    print("已删除线上题库索引")
    sys.exit()
out = Path(sys.argv[1]).resolve()
state_f = out / ".uploaded.json"
state = json.loads(state_f.read_text(encoding="utf-8")) if state_f.exists() else {}
for f in sorted((out / "media").glob("*.mp3")):
    if state.get(f.name):
        continue
    wr("key", "put", "bank:media:" + f.name, "--path", str(f))
    state[f.name] = True
    print("音频", f.name)
idx = out / "exam.json"
h = hashlib.sha1(idx.read_bytes()).hexdigest()
if state.get("_index") != h:
    wr("key", "put", "bank:index", "--path", str(idx))
    state["_index"] = h
    print("题库索引已更新")
state_f.write_text(json.dumps(state), encoding="utf-8")
print("完成")
