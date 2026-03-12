from __future__ import annotations

from pathlib import Path


DOCS_DIR = Path("docs")


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


def normalize_docs() -> list[Path]:
    changed: list[Path] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        original = path.read_text(encoding="utf-8-sig")
        normalized_lines = [_repair_line(line) for line in original.splitlines()]
        normalized = "\n".join(normalized_lines) + ("\n" if original.endswith(("\n", "\r\n")) else "")
        if normalized != original.replace("\r\n", "\n"):
            path.write_text(normalized, encoding="utf-8", newline="\n")
            changed.append(path)
    return changed


if __name__ == "__main__":
    changed_files = normalize_docs()
    for file_path in changed_files:
        print(file_path)
