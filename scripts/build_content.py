"""语法课和听力材料：data/grammar/*.txt → docs/grammar.json；data/listen/*.txt → docs/listening.json + docs/listen/*.mp3

用法（在仓库根目录）：
  python -I scripts/build_content.py .           只编译文本；听力的德语原文没改时沿用已有音频，改了就报错
  python -I scripts/build_content.py . --audio   同时用 edge-tts 生成缺的听力音频（要联网、装 edge-tts 和 ffmpeg）

—— 语法文件格式 ——
=== g-id | A1 | 中文标题 | Deutscher Titel
讲解（简化 Markdown）：
  ## 小标题          - 列表项          | 表格 | 第一行是表头 |（|---| 分隔行可省略）
  » 德语例句 — 中文     > 提示框          **加粗**   ==高亮（词尾等）==
---
练习（每行一题，" // " 后面依次是中文翻译、解析，都可省略）：
  ? 题干，空格处写 ___ => 正确选项 | 干扰项 | 干扰项 // 中文 // 解析
  = 填空句，答案写在方括号里 [auf] 或 [wird|ist]（| 分隔可接受的写法） // 中文 // 解析
  ~ 词块 / 按 / 正确 / 顺序 || 另一种 / 也对的 / 顺序 // 中文 // 解析

—— 听力文件格式 ——
=== l-id | B1 | 对话 | Deutscher Titel | 中文标题
intro: 情景说明（中文）
voices: K=Katja:Verkäuferin, M=Conrad:Kunde
K: 德语原文 // 中文
---
! 判断题陈述 => richtig 或 falsch // 解析
? 选择题 => 正确选项 | 干扰项 | 干扰项 // 解析
+ 生词 // 中文
"""
import asyncio
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(sys.argv[1]).resolve()
WANT_AUDIO = "--audio" in sys.argv
LEVELS = ["A1", "A2", "B1", "B2"]
errors = []


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"==(.+?)==", r"<mark>\1</mark>", s)
    return s


def md(lines):
    out, para = [], []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    i = 0
    while i < len(lines):
        l = lines[i].rstrip()
        if not l.strip():
            flush()
        elif l.startswith("## "):
            flush()
            out.append(f"<h4>{inline(l[3:].strip())}</h4>")
        elif l.startswith("- "):
            flush()
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:].strip())}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif l.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                row = lines[i].strip()
                if not re.fullmatch(r"\|[\s:|-]+\|", row):
                    rows.append([c.strip() for c in row.strip("|").split("|")])
                i += 1
            head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
            out.append(f'<div class="tablebox"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        elif l.startswith("» "):
            flush()
            de, _, zh = l[2:].partition(" — ")
            out.append(f'<div class="gx"><span class="de">{inline(de.strip())}</span>' + (f'<span class="zh">{inline(zh.strip())}</span>' if zh else "") + "</div>")
        elif l.startswith("> "):
            flush()
            out.append(f'<div class="tip">{inline(l[2:].strip())}</div>')
        else:
            para.append(l.strip())
        i += 1
    flush()
    return "".join(out)


def split_tail(body):
    parts = [p.strip() for p in body.split(" // ")]
    return parts[0], (parts[1] if len(parts) > 1 else ""), (parts[2] if len(parts) > 2 else "")


def with_tail(d, z, e):
    if z:
        d["z"] = z
    if e:
        d["e"] = e
    return d


def parse_ex(line, where):
    kind, body = line[0], line[1:].strip()
    main, z, e = split_tail(body)
    if kind == "?":
        q, sep, opts = main.partition(" => ")
        o = [x.strip() for x in opts.split(" | ")]
        if not sep or len(o) < 2 or len(set(o)) != len(o) or not all(o):
            errors.append(f"{where}：选择题格式不对：{line[:60]}")
        return with_tail({"t": "mc", "q": q.strip(), "o": o}, z, e)
    if kind == "=":
        segs = re.split(r"\[([^\]]+)\]", main)
        a = [[x.strip() for x in s.split("|")] for s in segs[1::2]]
        if not a or any(not x for alts in a for x in alts):
            errors.append(f"{where}：填空题没有 [答案]：{line[:60]}")
        return with_tail({"t": "gap", "q": segs[0::2], "a": a}, z, e)
    if kind == "~":
        orders = [[t.strip() for t in o.split(" / ")] for o in main.split(" || ")]
        if len(orders[0]) < 3 or any(sorted(t.lower() for t in o) != sorted(t.lower() for t in orders[0]) for o in orders):
            errors.append(f"{where}：排序题的词块不一致或太少：{line[:60]}")
        return with_tail({"t": "ord", "w": orders[0], "a": [" ".join(o) for o in orders]}, z, e)
    errors.append(f"{where}：不认识的练习行：{line[:60]}")
    return None


def blocks(path):
    """按 === 切成块，返回 [(表头字段, 行号, 正文行)]。"""
    cur, out = None, []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if raw.startswith("==="):
            cur = ([x.strip() for x in raw[3:].split("|")], n, [])
            out.append(cur)
        elif cur is not None:
            cur[2].append(raw)
        elif raw.strip() and not raw.startswith("#"):
            errors.append(f"{path.name}:{n}：第一个 === 之前不能有内容")
    return out


def build_grammar():
    topics, seen = [], set()
    files = sorted((R / "data/grammar").glob("*.txt"))
    for f in files:
        for head, n, lines in blocks(f):
            where = f"{f.name}:{n}"
            if len(head) != 4 or head[1] not in LEVELS:
                errors.append(f"{where}：表头应为 === id | 级别 | 中文 | Deutsch")
                continue
            tid, lv, zh, de = head
            if tid in seen or not re.fullmatch(r"g\d{3}", tid):
                errors.append(f"{where}：id {tid} 重复或不是 g000 格式")
            seen.add(tid)
            cut = lines.index("---") if "---" in lines else len(lines)
            ex = [parse_ex(l.strip(), f"{where} {tid}") for l in lines[cut + 1:] if l.strip() and not l.startswith("#")]
            ex = [x for x in ex if x]
            if len(ex) < 6:
                errors.append(f"{where} {tid}：练习只有 {len(ex)} 题（至少 6 题）")
            topics.append({"id": tid, "lv": lv, "zh": zh, "de": de, "html": md(lines[:cut]), "ex": ex})
    topics.sort(key=lambda t: (LEVELS.index(t["lv"]), t["id"]))
    for i, t in enumerate(topics, 1):
        t["no"] = i
    return topics


# —— 听力 ——
VOICES = {
    "Katja": "de-DE-KatjaNeural", "Conrad": "de-DE-ConradNeural", "Amala": "de-DE-AmalaNeural",
    "Killian": "de-DE-KillianNeural", "Seraphina": "de-DE-SeraphinaMultilingualNeural",
    "Florian": "de-DE-FlorianMultilingualNeural", "Ingrid": "de-AT-IngridNeural", "Jonas": "de-AT-JonasNeural",
}
RATE = {"A1": "-12%", "A2": "-7%", "B1": "-3%", "B2": "+0%"}
KINDS = {"对话", "留言", "广播", "采访", "讲座", "新闻", "讨论", "独白", "播客", "电话"}
RAW = R / "audio_listen"           # 每句一个 mp3（不进仓库），按内容哈希命名
CACHE = R / "data/listen_cache.json"
SR = 24000


def parse_listen():
    texts, seen = [], set()
    for f in sorted((R / "data/listen").glob("*.txt")):
        for head, n, lines in blocks(f):
            where = f"{f.name}:{n}"
            if len(head) != 5 or head[1] not in LEVELS or head[2] not in KINDS:
                errors.append(f"{where}：表头应为 === id | 级别 | 类型 | Deutsch | 中文")
                continue
            lid, lv, kind, de, zh = head
            if lid in seen or not re.fullmatch(r"l\d{3}", lid):
                errors.append(f"{where}：id {lid} 重复或不是 l000 格式")
            seen.add(lid)
            t = {"id": lid, "lv": lv, "kind": kind, "de": de, "zh": zh, "sp": {}, "s": [], "q": [], "v": []}
            voice = {}
            part = "text"
            for l in lines:
                l = l.strip()
                if not l or l.startswith("#"):
                    continue
                if l == "---":
                    part = "q"
                    continue
                if part == "text":
                    if l.startswith("intro:"):
                        t["intro"] = l[6:].strip()
                    elif l.startswith("voices:"):
                        for item in l[7:].split(","):
                            k, _, rest = item.strip().partition("=")
                            name, _, role = rest.partition(":")
                            if name not in VOICES:
                                errors.append(f"{where} {lid}：没有这个发音人 {name}")
                            voice[k] = VOICES.get(name, "de-DE-KatjaNeural")
                            t["sp"][k] = role or name
                    else:
                        m = re.match(r"^([A-Z]):\s*(.+)$", l)
                        if not m or m.group(1) not in voice:
                            errors.append(f"{where} {lid}：原文行要以已声明的说话人开头（K: …）：{l[:50]}")
                            continue
                        de_s, zh_s, _ = split_tail(m.group(2))
                        t["s"].append({"p": m.group(1), "de": de_s, "zh": zh_s, "_v": voice[m.group(1)]})
                else:
                    kind_q, body = l[0], l[1:].strip()
                    main, e, _ = split_tail(body)
                    if kind_q == "+":
                        t["v"].append([main, e])
                        continue
                    q, sep, ans = main.partition(" => ")
                    if kind_q == "!" and sep and ans.strip() in ("richtig", "falsch"):
                        t["q"].append(with_tail({"t": "rf", "q": q.strip(), "a": ans.strip() == "richtig"}, "", e))
                    elif kind_q == "?" and sep:
                        o = [x.strip() for x in ans.split(" | ")]
                        if len(o) < 2 or len(set(o)) != len(o):
                            errors.append(f"{where} {lid}：选择题选项不对：{l[:50]}")
                        t["q"].append(with_tail({"t": "mc", "q": q.strip(), "o": o}, "", e))
                    else:
                        errors.append(f"{where} {lid}：题目格式不对：{l[:50]}")
            if len(t["s"]) < 3 or len(t["q"]) < 3:
                errors.append(f"{where} {lid}：原文至少 3 句、题目至少 3 道")
            t["rate"] = RATE[lv]
            texts.append(t)
    texts.sort(key=lambda t: (LEVELS.index(t["lv"]), t["id"]))
    return texts


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


def build_listen():
    texts = parse_listen()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    out_dir = R / "docs/listen"
    out_dir.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    if WANT_AUDIO:
        jobs = []
        for t in texts:
            for s in t["s"]:
                f = RAW / f"{skey(s, t['rate'])}.mp3"
                if not (f.exists() and f.stat().st_size > 500):
                    jobs.append((f, s["de"], s["_v"], t["rate"]))
        if jobs:
            print(f"生成 {len(jobs)} 句听力音频…")
            fails = asyncio.run(tts_all(jobs))
            if fails:
                errors.append(f"{len(fails)} 句音频生成失败：{fails[:3]}")
    keep = set()
    for t in texts:
        keys = [skey(s, t["rate"]) for s in t["s"]]
        h = hashlib.sha1("|".join(keys).encode()).hexdigest()[:8]
        c = cache.get(t["id"])
        if not (c and c["h"] == h and (out_dir / c["f"]).exists()):
            if not all((RAW / f"{k}.mp3").exists() for k in keys):
                errors.append(f"{t['id']}：德语原文改了，需要重新生成音频（加 --audio）")
                continue
            buf, ts, pos = bytearray(), [], 0
            lead = int(SR * 0.4) * 2
            buf += b"\0" * lead
            pos += lead
            prev = None
            for s, k in zip(t["s"], keys):
                if prev is not None:
                    gap = int(SR * (0.35 if prev == s["p"] else 0.65)) * 2
                    buf += b"\0" * gap
                    pos += gap
                data = pcm(RAW / f"{k}.mp3")
                ts.append([round(pos / 2 / SR, 2), round((pos + len(data)) / 2 / SR, 2)])
                buf += data
                pos += len(data)
                prev = s["p"]
            buf += b"\0" * (int(SR * 0.5) * 2)
            name = f"{t['id']}-{h}.mp3"
            p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                                "-c:a", "libmp3lame", "-b:a", "40k", str(out_dir / name)], input=bytes(buf), capture_output=True)
            if p.returncode:
                errors.append(f"{t['id']}：ffmpeg 编码失败")
                continue
            c = cache[t["id"]] = {"h": h, "f": name, "dur": round(len(buf) / 2 / SR, 1), "ts": ts}
        keep.add(c["f"])
        t["f"], t["dur"] = c["f"], c["dur"]
        for s, (a, b) in zip(t["s"], c["ts"]):
            s["a"], s["b"] = a, b
        for s in t["s"]:
            s.pop("_v", None)
        t.pop("rate", None)
    for f in out_dir.glob("*.mp3"):
        if f.name not in keep and not errors:
            f.unlink()
    CACHE.write_text(json.dumps({k: v for k, v in cache.items() if v["f"] in keep or k not in {t["id"] for t in texts}}, ensure_ascii=False, indent=0), encoding="utf-8")
    return [t for t in texts if "f" in t]


grammar = build_grammar()
listen = build_listen()
if errors:
    for e in errors[:50]:
        print("✗", e)
    sys.exit(f"编译失败：{len(errors)} 个问题")
(R / "docs/grammar.json").write_text(json.dumps(grammar, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
(R / "docs/listening.json").write_text(json.dumps(listen, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
from collections import Counter
print("语法", len(grammar), "课", dict(Counter(t["lv"] for t in grammar)), "练习", sum(len(t["ex"]) for t in grammar), "题")
print("听力", len(listen), "篇", dict(Counter(t["lv"] for t in listen)), "共", round(sum(t["dur"] for t in listen) / 60, 1), "分钟")
