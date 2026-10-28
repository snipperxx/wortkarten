"""Parse Goethe A1/A2/B1 Wortliste PDFs into headword entries (+ examples for B1)."""
import json
import re
import sys
from pathlib import Path

import pymupdf

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])

# per file: pages (0-based, inclusive range), list of (hw_x0, hw_x1, ex_x0, ex_x1) column bands
CONF = {
    "A1": ("A1_SD1_Wortliste_02.pdf", range(8, 28), [(100, 228, 228, 600)]),
    "A2": ("Goethe-Zertifikat_A2_Wortliste.pdf", range(7, 31), [(30, 100, 100, 298), (298, 370, 370, 600)]),
    "B1": ("Goethe-Zertifikat_B1_Wortliste.pdf", range(15, 102), [(30, 128, 128, 305), (305, 405, 405, 600)]),
}
HEADER = re.compile(r"^(WORTLISTE|VS_\d+.*|Seite \d+|Inventare|\d+|[A-ZÄÖÜ]|ZERTIFIKAT B1|GOETHE-ZERTIFIKAT A2|A2_Wortliste.*)$")


def column_lines(page, x0, x1):
    """Words inside [x0,x1) grouped into visual lines -> [(y, x, text)]."""
    rows = {}
    for w in page.get_text("words"):
        wx0, wy0, _, _, text = w[:5]
        if x0 <= wx0 < x1 and 40 < wy0 < 790:
            key = round(wy0 / 3)
            rows.setdefault(key, []).append((wx0, wy0, text))
    out = []
    for key in sorted(rows):
        ws = sorted(rows[key])
        s = " ".join(t for _, _, t in ws).strip()
        if s and not HEADER.match(s):
            out.append((ws[0][1], ws[0][0], s))
    return out


def is_continuation(prev, line, gap):
    if gap > 14:
        return False
    if prev.rstrip().endswith((",", "-", ":", "/", "(", "→")):
        return True
    return bool(re.match(r"^(hat |ist |-|¨|\(|sich\b|war |wurde )", line))


def parse(level):
    fname, pages, bands = CONF[level]
    doc = pymupdf.open(SRC / fname)
    entries = []
    for pi in pages:
        page = doc[pi]
        for hx0, hx1, ex0, ex1 in bands:
            hws = column_lines(page, hx0, hx1)
            exs = column_lines(page, ex0, ex1)
            groups = []
            for y, x, s in hws:
                if groups and is_continuation(groups[-1]["text"], s, y - groups[-1]["y_last"]):
                    groups[-1]["text"] += " " + s
                    groups[-1]["y_last"] = y
                else:
                    groups.append({"y": y, "y_last": y, "indent": x - hx0 > 15, "text": s})
            for i, g in enumerate(groups):
                y_next = groups[i + 1]["y"] if i + 1 < len(groups) else 10_000
                lines = [s for y, _, s in exs if g["y"] - 3 <= y < y_next - 3]
                entries.append({"level": level, "page": pi + 1, "hw": re.sub(r"\s+", " ", g["text"]).strip(),
                                "sub": g["indent"], "ex_raw": " ".join(lines)})
    return entries


def first_examples(raw, n=2):
    raw = re.sub(r"\s+", " ", raw).strip()
    parts = re.split(r"(?:^|\s)\d\.\s", raw)
    parts = [p.strip() for p in parts if p.strip()]
    return parts[:n]


ART = re.compile(r"^(der|die|das)\s+(.*)$")


def analyse(hw):
    """Split a headword line into lemma / article / plural / verb forms."""
    info = {"hw": hw}
    m = ART.match(hw)
    if m:
        info["art"] = m.group(1)
        rest = m.group(2)
        parts = [p.strip() for p in rest.split(",", 1)]
        info["lemma"] = parts[0]
        info["pl"] = parts[1] if len(parts) > 1 else ""
        info["kind"] = "noun"
        return info
    parts = [p.strip() for p in hw.split(",") if p.strip()]
    info["lemma"] = parts[0]
    perf = [p for p in parts if re.match(r"^(hat|ist) ", p)]
    if perf:
        info["kind"] = "verb"
        info["aux"] = perf[0].split()[0]
        info["p2"] = perf[0].split(" ", 1)[1]
        info["forms"] = ", ".join(parts[1:])
    else:
        info["kind"] = "other"
    return info


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    allsets = {}
    for level in ("A1", "A2", "B1"):
        ents = parse(level)
        for e in ents:
            e.update(analyse(e["hw"]))
            e["ex"] = first_examples(e.pop("ex_raw"))
        (OUT / f"{level}_raw.json").write_text(json.dumps(ents, ensure_ascii=False, indent=1), encoding="utf-8")
        allsets[level] = ents
        print(level, len(ents), "entries;", sum(1 for e in ents if not e["ex"]), "without example")
    for e in allsets["B1"][200:215]:
        print(json.dumps(e, ensure_ascii=False))


main()
