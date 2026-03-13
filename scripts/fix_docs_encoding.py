from __future__ import annotations

from pathlib import Path
import re


DOCS_DIR = Path("docs")
BAD_PATTERNS = (
    re.compile("\ufffd"),
    re.compile("\u00c3[\u0080-\u00bf]"),
    re.compile("\u00c2[\u0080-\u00bf]"),
    re.compile("\u00e2[\u0080-\uffff]{1,2}"),
)
CP1252_REVERSE = {
    0x20AC: 0x80,
    0x201A: 0x82,
    0x0192: 0x83,
    0x201E: 0x84,
    0x2026: 0x85,
    0x2020: 0x86,
    0x2021: 0x87,
    0x02C6: 0x88,
    0x2030: 0x89,
    0x0160: 0x8A,
    0x2039: 0x8B,
    0x0152: 0x8C,
    0x017D: 0x8E,
    0x2018: 0x91,
    0x2019: 0x92,
    0x201C: 0x93,
    0x201D: 0x94,
    0x2022: 0x95,
    0x2013: 0x96,
    0x2014: 0x97,
    0x02DC: 0x98,
    0x2122: 0x99,
    0x0161: 0x9A,
    0x203A: 0x9B,
    0x0153: 0x9C,
    0x017E: 0x9E,
    0x0178: 0x9F,
}


def _bad_score(text: str) -> int:
    return sum(len(pattern.findall(text)) for pattern in BAD_PATTERNS)


def _repair_line(line: str) -> str:
    if "\ufffd" in line:
        manual = {
            "Agrega��o": "Agregação",
            "et�ria": "etária",
            "�nico": "único",
            "composi��o": "composição",
            "participa��o": "participação",
            "ordena��o": "ordenação",
            "espec�fica": "específica",
            "n�o": "não",
            "apresenta��o": "apresentação",
            "agrega��o": "agregação",
            "ru�do": "ruído",
            "informa��o": "informação",
            "Valida��o": "Validação",
            "�?ndice": "Índice",
            "�?cones": "Ícones",
        }
        for old, new in manual.items():
            line = line.replace(old, new)
    if "\u00c3" in line or "\u00c2" in line:
        try:
            candidate = line.encode("latin1").decode("utf-8")
        except UnicodeError:
            candidate = line
        score_before = line.count("\u00c3") + line.count("\u00c2")
        score_after = candidate.count("\u00c3") + candidate.count("\u00c2")
        if score_after < score_before:
            line = candidate
    return line


def _decode_cp1252_utf8(line: str) -> str:
    payload = bytearray()
    for char in line:
        code = ord(char)
        if code <= 0xFF:
            payload.append(code)
            continue
        reverse = CP1252_REVERSE.get(code)
        if reverse is None:
            raise UnicodeEncodeError("cp1252", char, 0, 1, "character not reversible")
        payload.append(reverse)
    return payload.decode("utf-8")


def _repair_text(text: str) -> str:
    repaired_lines: list[str] = []
    for line in text.splitlines():
        current = line
        current_score = _bad_score(current)
        for _ in range(4):
            candidates = [current]
            for candidate_factory in (
                lambda value: value.encode("latin1").decode("utf-8"),
                _decode_cp1252_utf8,
            ):
                try:
                    decoded = candidate_factory(current)
                except UnicodeError:
                    continue
                candidates.append(decoded)

            best = min(candidates, key=_bad_score)
            best_score = _bad_score(best)
            if best_score >= current_score:
                break
            current = best
            current_score = best_score
        repaired_lines.append(current)

    normalized = "\n".join(repaired_lines)
    if text.endswith(("\n", "\r\n")):
        normalized += "\n"
    return normalized


def normalize_docs() -> list[Path]:
    changed: list[Path] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        original = path.read_text(encoding="utf-8-sig")
        repaired = _repair_text(original)
        normalized_lines = [_repair_line(line) for line in repaired.splitlines()]
        normalized = "\n".join(normalized_lines) + ("\n" if original.endswith(("\n", "\r\n")) else "")
        if normalized != original.replace("\r\n", "\n"):
            path.write_text(normalized, encoding="utf-8", newline="\n")
            changed.append(path)
    return changed


if __name__ == "__main__":
    changed_files = normalize_docs()
    for file_path in changed_files:
        print(file_path)
