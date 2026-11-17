"""词库 lemma → 可在 Wiktionary 里查的词形（去掉 (Pl.)、sich、der/die、斜杠变体、可省字母）。"""
import re

NOTE = re.compile(r"\s*\((?:Pl\.|Sg\.|nur Pl\.|Plural|sich|siehe [^)]*|D|A|CH|D, ?A|D, ?CH|A, ?CH)\)\s*")


def word_keys(w):
    lemma = w["lemma"]
    s = NOTE.sub(" ", lemma).strip()
    s = re.sub(r"\s*\([^)]*$", "", s)          # 截断的 "Obst (D"
    s = re.sub(r"^sich\s+", "", s)
    s = re.sub(r"^(?:der|die|das)(?:/(?:der|die|das))*\s+", "", s)
    out = []
    for part in re.split(r"\s*/\s*", s):
        part = part.strip().rstrip("-").strip()
        if not part or part.startswith("-"):
            continue
        m = re.search(r"\(([a-zäöüß]+)\)", part)
        if m:
            out.append(part.replace(m.group(0), ""))
            out.append(part.replace(m.group(0), m.group(1)))
        else:
            out.append(part)
    return [o for o in dict.fromkeys(out) if o and "…" not in o and "..." not in o]


def entries(src, keys, pos):
    out = []
    for k in keys:
        cands = [k] if pos == "phr" else ([k[:1].upper() + k[1:]] if pos == "n" else [k, k.lower()])
        for c in dict.fromkeys(cands):
            for r in src.get(c, []):
                if not r.get("formof") and not (r.get("gl") and all(re.match(
                        r"^(Genitiv|Dativ|Akkusativ|Nominativ|Plural|[0-9]\. Person|Partizip|Positiv|Komparativ|Superlativ|"
                        r"Variante|Nebenform|Imperativ|inflection of|plural of|genitive of|dative of)", g) for g in r["gl"])):
                    out.append(dict(r, _w=c))
    return out
