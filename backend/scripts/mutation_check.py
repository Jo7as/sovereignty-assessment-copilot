"""Prüft die Tests selbst: Verändert jede Zahl 0 bis 4 in einer Datei einzeln und meldet,
welche Veränderungen die Tests nicht bemerken.

Aufruf im Ordner backend/:
    uv run python scripts/mutation_check.py app/scoring/rules.py tests/test_scoring.py

Ohne Bytecode-Zwischenspeicher: Sonst kann Python eine gleich große, in derselben Sekunde
geänderte Datei für unverändert halten und einen alten Stand testen. Die Originaldatei wird
in jedem Fall wiederhergestellt.
"""

import io
import os
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path


def main(target: Path, tests: list[str]) -> int:
    original = target.read_text()
    lines = original.splitlines(keepends=True)
    sites = [
        token
        for token in tokenize.generate_tokens(io.StringIO(original).readline)
        if token.type == tokenize.NUMBER and token.string in {"0", "1", "2", "3", "4"}
    ]
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    survived = []
    try:
        for token in sites:
            row, column = token.start
            for new in sorted({str((int(token.string) + 1) % 5), str((int(token.string) - 1) % 5)}):
                mutated = lines.copy()
                line = mutated[row - 1]
                mutated[row - 1] = line[:column] + new + line[column + 1 :]
                target.write_text("".join(mutated))
                shutil.rmtree(target.parent / "__pycache__", ignore_errors=True)
                result = subprocess.run(
                    ["uv", "run", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests],
                    capture_output=True,
                    env=environment,
                )
                if result.returncode == 0:
                    survived.append((row, token.string, new, lines[row - 1].strip()[:80]))
    finally:
        target.write_text(original)
    print(f"{len(sites)} Stellen, {2 * len(sites)} Veränderungen, unbemerkt: {len(survived)}")
    for row, old, new, code in survived:
        print(f"  Zeile {row}: {old} -> {new}   {code}")
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), sys.argv[2:]))
