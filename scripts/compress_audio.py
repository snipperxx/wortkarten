"""把 audio_small/ 里新生成的 y*.mp3 压成和旧词一样的格式：单声道 22.05 kHz 32 kbps，去掉首尾静音。

用法：python -I scripts/compress_audio.py .     （之后再跑 gen_audio_adv.py 重新打包）
已经压过的文件（采样率 22050）会跳过。
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

R = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
RAW = R / "audio_small"
TRIM = "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse"


def rate(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    return r.stdout.strip()


def one(f):
    if rate(f) == "22050":
        return 0
    tmp = f.with_suffix(".tmp.mp3")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-af", TRIM, "-ac", "1", "-ar", "22050", "-b:a", "32k", str(tmp)],
                       capture_output=True, creationflags=0x08000000)
    if r.returncode or not tmp.exists() or tmp.stat().st_size < 500:
        tmp.unlink(missing_ok=True)
        return -1
    tmp.replace(f)
    return 1


files = sorted(RAW.glob("y*.mp3"))
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(one, files))
print("压缩", res.count(1), "跳过", res.count(0), "失败", res.count(-1))
