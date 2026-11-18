"""Transcribe official exam audio with timestamps so conversion agents can cut per Teil.
usage: py -3.11 -I asr.py <official_dir> <work_dir> <setdir> [<setdir> ...]
writes <work_dir>/<setdir>/asr_<audio-stem>.txt  lines: [start-end] text  (seconds, 1 decimal)
"""
import sys, os, glob, time
sys.stdout.reconfigure(encoding="utf-8")
import site
for sp in site.getsitepackages():
    for sub in ("nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_runtime/bin"):
        d = os.path.join(sp, sub)
        if os.path.isdir(d):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
from faster_whisper import WhisperModel

off, work, sets = sys.argv[1], sys.argv[2], sys.argv[3:]
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
for s in sets:
    files = sorted(glob.glob(os.path.join(off, s, "**", "*.mp3"), recursive=True) + glob.glob(os.path.join(off, s, "*.mp4")))
    os.makedirs(os.path.join(work, s), exist_ok=True)
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0].replace(" ", "_")
        out = os.path.join(work, s, f"asr_{stem}.txt")
        if os.path.exists(out):
            continue
        t0 = time.time()
        segs, info = m.transcribe(f, language="de", beam_size=5, vad_filter=False, condition_on_previous_text=False)
        lines = [f"# {os.path.relpath(f, os.path.dirname(off))}  duration {info.duration:.1f}s"]
        for sg in segs:
            lines.append(f"[{sg.start:.1f}-{sg.end:.1f}] {sg.text.strip()}")
        open(out + ".tmp", "w", encoding="utf-8").write("\n".join(lines) + "\n")
        os.replace(out + ".tmp", out)
        print(f"{s}/{stem}: {info.duration:.0f}s audio in {time.time()-t0:.0f}s", flush=True)
print("ALL DONE", flush=True)
