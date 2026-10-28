"""Generate one mp3 per word (article + lemma) with Microsoft neural German TTS, then pack into buckets."""
import asyncio
import base64
import json
import re
import sys
from pathlib import Path

import edge_tts

V = Path(sys.argv[1])
words = json.loads((V / "site" / "words.json").read_text(encoding="utf-8"))
RAW = V / "audio_small" if (V / "audio_small").exists() else V / "audio_raw"
RAW.mkdir(exist_ok=True)
VOICE = "de-DE-KatjaNeural"
BUCKET = 100


def say_text(w):
    t = re.sub(r"\(.*?\)", "", w["lemma"]).strip().rstrip("-").strip()
    return f"{w['art']} {t}" if w.get("art") else t


async def one(w, sem, stats):
    out = RAW / f"{w['id']}.mp3"
    if out.exists() and out.stat().st_size > 500:
        return
    async with sem:
        for attempt in range(4):
            try:
                await edge_tts.Communicate(say_text(w), VOICE, rate="-5%").save(str(out))
                stats["ok"] += 1
                return
            except Exception as e:  # network hiccup / throttling
                await asyncio.sleep(2 + attempt * 3)
        stats["fail"].append(w["id"])


async def main():
    sem, stats = asyncio.Semaphore(8), {"ok": 0, "fail": []}
    await asyncio.gather(*(one(w, sem, stats) for w in words))
    print("generated", stats["ok"], "failed", len(stats["fail"]), stats["fail"][:10])
    # pack: audio/b<k>.json = {id: base64 mp3}
    adir = V / "site" / "audio"
    adir.mkdir(exist_ok=True)
    order = sorted(w["id"] for w in words)
    index = {}
    for k in range(0, len(order), BUCKET):
        ids = order[k:k + BUCKET]
        pack = {}
        for i in ids:
            f = RAW / f"{i}.mp3"
            if f.exists():
                pack[i] = base64.b64encode(f.read_bytes()).decode()
                index[i] = k // BUCKET
        (adir / f"b{k // BUCKET}.json").write_text(json.dumps(pack, separators=(",", ":")), encoding="utf-8")
    (adir / "index.json").write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")
    total = sum(f.stat().st_size for f in adir.glob("*.json"))
    print("buckets", len(order) // BUCKET + 1, "total MB", round(total / 1e6, 1))


asyncio.run(main())
