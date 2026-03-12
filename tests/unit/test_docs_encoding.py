from __future__ import annotations

from pathlib import Path
import re


DOCS_DIR = Path("docs")

BAD_PATTERNS = {
    "replacement_char": re.compile("\ufffd"),
    "utf8_latin1_double_decode_a_tilde": re.compile("\u00c3[\u00a0-\u00bf]"),
    "utf8_latin1_double_decode_a_circumflex": re.compile("\u00c2[\u00a0-\u00bf]"),
    "utf8_cp1252_punctuation_mojibake": re.compile("\u00e2[\u0080-\uffff]{1,2}"),
}


def test_docs_do_not_contain_mojibake_sequences() -> None:
    offenders: list[str] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        hits = [name for name, pattern in BAD_PATTERNS.items() if pattern.search(text)]
        if hits:
            offenders.append(f"{path}: {', '.join(hits)}")
    assert not offenders, "Documentos com encoding corrompido:\n" + "\n".join(offenders)
