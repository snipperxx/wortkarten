"""B2 / C1 词的发音：edge-tts 生成 mp3 → 打包成 docs/audio/b<32+n>.json，并写进 docs/audio/index.json

用法：<装了 edge-tts 的 python> -I scripts/gen_audio_adv.py .
- 发音包在用户设备上是“听过就永久缓存”的，所以旧包（b0–b31）一个字节都不能改。
- 新词按 id 固定分包：y0000–y0099 → b32，y0100–y0199 → b33 …；重跑只会重写这些新包。
"""
import asyncio
import base64
import json
import re
import sys
from pathlib import Path

import edge_tts

sys.stdout.reconfigure(encoding="utf-8")
R = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
RAW = R / "audio_small"
RAW.mkdir(exist_ok=True)
ADIR = R / "docs" / "audio"
VOICE, FIRST = "de-DE-KatjaNeural", 32
words = [w for w in json.loads((R / "data" / "adv_words.json").read_text(encoding="utf-8"))]


def say_text(w):
    t = re.sub(r"\(.*?\)", "", w["lemma"]).strip().rstrip("-").strip()
    return f"{w['art']} {t}" if w.get("art") else t


async def one(w, sem, stats):
    out = RAW / f"{w['id']}.mp3"
    if out.exists() and out.stat().st_size > 500:
        return
    async with sem:
        for attempt in range(5):
            try:
                await edge_tts.Communicate(say_text(w), VOICE, rate="-5%").save(str(out))
                stats["ok"] += 1
                return
            except Exception:
                await asyncio.sleep(2 + attempt * 3)
        stats["fail"].append(w["id"])


async def main():
    sem, stats = asyncio.Semaphore(8), {"ok": 0, "fail": []}
    await asyncio.gather(*(one(w, sem, stats) for w in words))
    print("新生成", stats["ok"], "失败", len(stats["fail"]), stats["fail"][:10])
    index = json.loads((ADIR / "index.json").read_text(encoding="utf-8"))
    index = {k: v for k, v in index.items() if not k.startswith("y")}
    packs = {}
    for w in words:
        f = RAW / f"{w['id']}.mp3"
        if f.exists() and f.stat().st_size > 500:
            b = FIRST + int(w["id"][1:]) // 100
            packs.setdefault(b, {})[w["id"]] = base64.b64encode(f.read_bytes()).decode()
            index[w["id"]] = b
    for b, pack in packs.items():
        (ADIR / f"b{b}.json").write_text(json.dumps(pack, separators=(",", ":")), encoding="utf-8")
    (ADIR / "index.json").write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")
    print("新发音包", sorted(packs), "大小 MB", round(sum((ADIR / f"b{b}.json").stat().st_size for b in packs) / 1e6, 1))


asyncio.run(main())
