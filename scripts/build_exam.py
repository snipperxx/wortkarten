"""考题库编译：<源目录>/*.txt（+ 听力 mp3）+ data/exam/meta.json → <输出目录>/exam.json + <输出目录>/media/*.mp3

题目来自用户自己下载的官方模拟题（Goethe Übungssatz）或备考书，有版权：
源文件和输出都放在 exam_private/（gitignored），只上传到加密码的私有存储（scripts/exam_upload.py），不进公开仓库 / 网站。

用法（在仓库根目录）：
  python -I scripts/build_exam.py exam_private/src exam_private/out           编译；官方 mp3 用 file= 引用
  python -I scripts/build_exam.py exam_private/src exam_private/out --audio   没有官方音频、只有原文的片段用 edge-tts 朗读

=== set | 级别 | 套题号 | 名称          套题名称，例如 Goethe-Zertifikat B1 · Übungssatz 01（官方）
@audio twice file=B1_Hoeren_Teil1_01.mp3   用官方音频（相对源目录）；后面可写原文 K: …（不用 voices:，用作答完后看原文）

—— 文件格式 ——
=== 任务id | 级别 | 套题号 | 模块 L/H/S/M | Teil 号
inst: 德语题目要求（和考试卷面一样）
zh: 中文说明
opts: a | b | c 或 a = 选项文字 | b = …       （m 题的选项：广告字母、说话人、要填的句子）
@text 标题            阅读材料；后面的行是段落，直到下一个 @ 标记
@ad a | 标题          广告 / 短启事（m 题对照用）；后面的行是正文
@audio twice|once     听力片段；后面写 voices: 和 K: 原文 // 中文
@q                    之后的题目不挂在某段材料下，放在全部材料后面
@write 80 / @speak    写作 / 口语题，后面写 p: 德语题目、zh: 中文、- 要点、model: 参考答案（可多行）
题目（挂在最近的一段材料下）：
  ! 陈述 => richtig|falsch // 解析
  y 陈述 => ja|nein // 解析
  ? 题干 => 正确选项 | 干扰项 | 干扰项 // 解析     （选项顺序编译时按 id 固定打乱）
  m 题干 => 选项键 // 解析
  = 带 ___ 的填空 => 答案|另一种写法 // 解析
"""
import asyncio
import hashlib
import json
import random
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]).resolve()
DST = Path(sys.argv[2]).resolve()
WANT_AUDIO = "--audio" in sys.argv
LEVELS = ["A1", "A2", "B1", "B2", "C1"]
MODS = {"L": "Lesen", "H": "Hören", "S": "Schreiben", "M": "Sprechen"}
VOICES = {
    "Katja": "de-DE-KatjaNeural", "Conrad": "de-DE-ConradNeural", "Amala": "de-DE-AmalaNeural",
    "Killian": "de-DE-KillianNeural", "Seraphina": "de-DE-SeraphinaMultilingualNeural",
    "Florian": "de-DE-FlorianMultilingualNeural", "Ingrid": "de-AT-IngridNeural", "Jonas": "de-AT-JonasNeural",
}
RATE = {"A1": "-10%", "A2": "-6%", "B1": "-2%", "B2": "+0%", "C1": "+4%"}
RAW = R / "audio_listen"
CACHE = DST / "audio_cache.json"
OUT = DST / "media"
SR = 24000
errors = []


def tail(body):
    parts = [p.strip() for p in body.split(" // ")]
    return parts[0], (parts[1] if len(parts) > 1 else "")


def parse_opts(line):
    out = []
    for x in line.split(" | "):
        k, sep, lab = x.partition(" = ")
        out.append({"k": k.strip(), "l": lab.strip()} if sep else {"k": x.strip(), "l": ""})
    return out


SETS = {}


def parse_file(f):
    tasks, cur, block = [], None, None
    for n, raw in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()
        if line.startswith("==="):
            head = [x.strip() for x in line[3:].split("|")]
            where = f"{f.name}:{n}"
            if head[0] == "set" and len(head) == 4 and head[1] in LEVELS and head[2].isdigit():
                SETS[f"{head[1]}-{head[2]}"] = head[3]
                cur = None
                continue
            if len(head) != 5 or head[1] not in LEVELS or head[3] not in MODS or not head[2].isdigit() or not head[4].isdigit():
                errors.append(f"{where}：表头应为 === id | 级别 | 套题号 | L/H/S/M | Teil")
                cur = None
                continue
            tid, lv, st, mod, teil = head
            cur = {"id": tid, "lv": lv, "set": int(st), "mod": mod, "teil": int(teil), "name": f"{MODS[mod]} Teil {teil}",
                   "inst": "", "zh": "", "items": [], "q": [], "wq": [], "_where": where}
            tasks.append(cur)
            block = None
            continue
        if cur is None or not line.strip() or line.lstrip().startswith("#"):
            continue
        s = line.strip()
        where = f"{f.name}:{n} {cur['id']}"
        if s.startswith("@"):
            tag, _, rest = s[1:].partition(" ")
            rest = rest.strip()
            if tag == "text":
                block = {"k": "text", "title": rest, "de": []}
                cur["items"].append(block)
            elif tag == "ad":
                key, _, title = rest.partition(" | ")
                block = {"k": "ad", "key": key.strip(), "title": title.strip(), "de": []}
                cur["items"].append(block)
            elif tag == "audio":
                words = rest.split()
                src = next((w[5:] for w in words if w.startswith("file=")), None)
                block = {"k": "audio", "plays": 1 if "once" in words else 2, "s": [], "sp": {}, "_voice": {}}
                if src:
                    block["_file"] = src
                    if not (SRC / src).exists():
                        errors.append(f"{where}：找不到音频文件 {src}")
                cur["items"].append(block)
            elif tag == "q":
                block = None
            elif tag in ("write", "speak"):
                block = {"kind": tag, "p": "", "zh": "", "pts": [], "words": int(rest) if rest.isdigit() else 0, "model": []}
                cur["wq"].append(block)
            else:
                errors.append(f"{where}：不认识的标记 @{tag}")
            continue
        if block is not None and "kind" in block:                 # 写作 / 口语
            if s.startswith("p:"):
                block["p"] += (" " if block["p"] else "") + s[2:].strip()
            elif s.startswith("zh:"):
                block["zh"] = s[3:].strip()
            elif s.startswith("- "):
                block["pts"].append(s[2:].strip())
            elif s.startswith("model:"):
                block["model"].append(s[6:].strip())
            else:
                errors.append(f"{where}：写作 / 口语块里只能写 p: zh: - model:：{s[:40]}")
            continue
        if s.startswith("inst:"):
            cur["inst"] = s[5:].strip(); continue
        if s.startswith("zh:"):
            cur["zh"] = s[3:].strip(); continue
        if s.startswith("opts:"):
            cur["opts"] = parse_opts(s[5:].strip()); continue
        if block is not None and block["k"] == "audio" and s.startswith("voices:"):
            for item in s[7:].split(","):
                k, _, r = item.strip().partition("=")
                name, _, role = r.partition(":")
                if name not in VOICES:
                    errors.append(f"{where}：没有这个发音人 {name}")
                block["_voice"][k] = VOICES.get(name, "de-DE-KatjaNeural")
                block["sp"][k] = role or name
            continue
        kind = s[0]
        if kind in "!y?m=" and len(s) > 2 and s[1] == " ":
            main, e = tail(s[2:])
            q, sep, ans = main.partition(" => ")
            q, ans = q.strip(), ans.strip()
            it = len(cur["items"]) - 1 if block is not None else -1
            if not sep:
                errors.append(f"{where}：题目缺少 => 答案：{s[:50]}")
                continue
            d = {"q": q, "it": it}
            if e:
                d["e"] = e
            if kind == "!":
                if ans not in ("richtig", "falsch"):
                    errors.append(f"{where}：! 题答案只能是 richtig / falsch")
                d.update(t="rf", a=ans == "richtig")
            elif kind == "y":
                if ans not in ("ja", "nein"):
                    errors.append(f"{where}：y 题答案只能是 ja / nein")
                d.update(t="yn", a=ans == "ja")
            elif kind == "?":
                o = [x.strip() for x in ans.split(" | ")]
                if len(o) < 2 or len(set(o)) != len(o):
                    errors.append(f"{where}：选择题选项不对：{s[:50]}")
                d.update(t="mc", o=o)
            elif kind == "m":
                d.update(t="m", a=ans)
            else:
                d.update(t="gap", a=[x.strip() for x in ans.split("|")])
            cur["q"].append(d)
            continue
        if block is not None and block["k"] in ("text", "ad"):
            block["de"].append(s)
            continue
        if block is not None and block["k"] == "audio":
            m = re.match(r"^([A-Z]):\s*(.+)$", s)
            if m and "_file" in block and m.group(1) not in block["_voice"]:
                block["_voice"][m.group(1)] = "de-DE-KatjaNeural"
            if not m or m.group(1) not in block["_voice"]:
                errors.append(f"{where}：听力原文行要以已声明的说话人开头：{s[:50]}")
                continue
            de, zh = tail(m.group(2))
            block["s"].append({"p": m.group(1), "de": de, "zh": zh, "_v": block["_voice"][m.group(1)]})
            continue
        errors.append(f"{where}：这一行放错地方了：{s[:50]}")
    return tasks


def finish(t):
    where = t.pop("_where")
    keys = [o["k"] for o in t.get("opts", [])]
    for i, q in enumerate(t["q"]):
        if q["t"] == "mc":                                   # 第一个是正确答案 → 按 id 固定打乱
            o = q["o"][:]
            rnd = random.Random(f"{t['id']}.{i}")
            order = list(range(len(o)))
            rnd.shuffle(order)
            q["o"] = [o[j] for j in order]
            q["a"] = order.index(0)
        elif q["t"] == "m" and q["a"] not in keys:
            errors.append(f"{where} {t['id']} 第 {i + 1} 题：答案 {q['a']} 不在 opts 里")
    for it in t["items"]:
        if it["k"] == "audio":
            it.pop("_voice", None)
            if len(it["s"]) < 1 and "_file" not in it:
                errors.append(f"{where} {t['id']}：听力片段没有原文")
    if t["mod"] in "LH" and not t["q"]:
        errors.append(f"{where} {t['id']}：阅读 / 听力任务没有题目")
    if t["mod"] in "SM" and not t["wq"] and not t["q"]:
        errors.append(f"{where} {t['id']}：写作 / 口语任务没有题目")
    for w in t["wq"]:
        w["model"] = "\n".join(w["model"])
        if not w["p"]:
            errors.append(f"{where} {t['id']}：写作 / 口语题缺少 p:")
    if not t["inst"]:
        errors.append(f"{where} {t['id']}：缺少 inst:")


def skey(s, rate):
    return hashlib.sha1(f"{s['_v']}|{rate}|{s['de']}".encode()).hexdigest()[:16]


async def tts_all(jobs):
    import edge_tts
    sem = asyncio.Semaphore(6)
    fails = []

    async def one(path, text, voice, rate):
        async with sem:
            for attempt in range(5):
                try:
                    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))
                    if path.stat().st_size > 500:
                        return
                except Exception:
                    pass
                await asyncio.sleep(2 + attempt * 3)
            fails.append(text[:40])

    await asyncio.gather(*(one(*j) for j in jobs))
    return fails


def pcm(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True)
    if p.returncode:
        raise RuntimeError(f"ffmpeg 解码失败 {path}")
    return p.stdout


def build_audio(tasks):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    OUT.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    keep = set()
    for t in tasks:                                   # 官方音频：转成单声道 48k 的 mp3
        for i, it in enumerate(t["items"]):
            if it["k"] != "audio" or "_file" not in it:
                continue
            srcf = SRC / it.pop("_file")
            if not srcf.exists():
                continue
            h = hashlib.sha1(srcf.read_bytes()).hexdigest()[:8]
            name = f"{t['id']}-{i}-{h}.mp3"
            if not (OUT / name).exists():
                p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(srcf), "-ac", "1", "-ar", "24000", "-c:a", "libmp3lame", "-b:a", "48k", str(OUT / name)], capture_output=True)
                if p.returncode:
                    errors.append(f"{t['id']}：ffmpeg 转换失败 {srcf.name}")
                    continue
            d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(OUT / name)], capture_output=True, text=True)
            it["f"], it["dur"] = name, round(float(d.stdout.strip() or 0), 1)
            keep.add(name)
            for s in it["s"]:
                s.pop("_v", None)
    clips = [(t, i, it) for t in tasks for i, it in enumerate(t["items"]) if it["k"] == "audio" and "f" not in it]
    if WANT_AUDIO:
        jobs = []
        for t, _, it in clips:
            for s in it["s"]:
                f = RAW / f"{skey(s, RATE[t['lv']])}.mp3"
                if not (f.exists() and f.stat().st_size > 500) and f not in {j[0] for j in jobs}:
                    jobs.append((f, s["de"], s["_v"], RATE[t["lv"]]))
        if jobs:
            print(f"生成 {len(jobs)} 句考试听力音频…")
            fails = asyncio.run(tts_all(jobs))
            if fails:
                errors.append(f"{len(fails)} 句音频生成失败：{fails[:3]}")
    for t, i, it in clips:
        rate = RATE[t["lv"]]
        keys = [skey(s, rate) for s in it["s"]]
        h = hashlib.sha1("|".join(keys).encode()).hexdigest()[:8]
        cid = f"{t['id']}-{i}"
        c = cache.get(cid)
        if not (c and c["h"] == h and (OUT / c["f"]).exists()):
            if not all((RAW / f"{k}.mp3").exists() for k in keys):
                errors.append(f"{cid}：听力原文改了，需要重新生成音频（加 --audio）")
                continue
            buf, ts, pos, prev = bytearray(), [], 0, None
            lead = int(SR * 0.5) * 2
            buf += b"\0" * lead
            pos += lead
            for s, k in zip(it["s"], keys):
                if prev is not None:
                    gap = int(SR * (0.35 if prev == s["p"] else 0.6)) * 2
                    buf += b"\0" * gap
                    pos += gap
                data = pcm(RAW / f"{k}.mp3")
                ts.append([round(pos / 2 / SR, 2), round((pos + len(data)) / 2 / SR, 2)])
                buf += data
                pos += len(data)
                prev = s["p"]
            buf += b"\0" * (int(SR * 0.6) * 2)
            name = f"{cid}-{h}.mp3"
            p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                                "-c:a", "libmp3lame", "-b:a", "40k", str(OUT / name)], input=bytes(buf), capture_output=True)
            if p.returncode:
                errors.append(f"{cid}：ffmpeg 编码失败")
                continue
            c = cache[cid] = {"h": h, "f": name, "dur": round(len(buf) / 2 / SR, 1), "ts": ts}
        keep.add(c["f"])
        it["f"], it["dur"] = c["f"], c["dur"]
        for s, (a, b) in zip(it["s"], c["ts"]):
            s["a"], s["b"] = a, b
    for t, _, it in clips:
        for s in it["s"]:
            s.pop("_v", None)
    if not errors:
        for f in OUT.glob("*.mp3"):
            if f.name not in keep:
                f.unlink()
        CACHE.write_text(json.dumps({k: v for k, v in cache.items() if v["f"] in keep}, ensure_ascii=False, indent=0), encoding="utf-8")


tasks, seen = [], set()
DST.mkdir(parents=True, exist_ok=True)
for f in sorted(SRC.glob("*.txt")):
    for t in parse_file(f):
        if t["id"] in seen:
            errors.append(f"任务 id 重复：{t['id']}")
        seen.add(t["id"])
        finish(t)
        tasks.append(t)
build_audio(tasks)
meta = json.loads((R / "data/exam/meta.json").read_text(encoding="utf-8"))
# 每个级别的 Teil 必须在 meta 里有说明
for t in tasks:
    teile = meta["levels"].get(t["lv"], {}).get("mods", {}).get(t["mod"], {}).get("teile", [])
    if t["teil"] > len(teile):
        errors.append(f"{t['id']}：meta.json 里 {t['lv']} {t['mod']} 没有 Teil {t['teil']}")
if errors:
    for e in errors[:60]:
        print("✗", e)
    sys.exit(f"编译失败：{len(errors)} 个问题")
tasks.sort(key=lambda t: (LEVELS.index(t["lv"]), t["set"], "LHSM".index(t["mod"]), t["teil"]))
meta["sets"] = SETS
(DST / "exam.json").write_text(json.dumps({"meta": meta, "tasks": tasks}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
from collections import Counter
print("考题", len(tasks), "个 Teil", dict(Counter(f"{t['lv']}-{t['set']}" for t in tasks)),
      "客观题", sum(len(t["q"]) for t in tasks), "写作/口语", sum(len(t["wq"]) for t in tasks))
