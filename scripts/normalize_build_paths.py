"""Keep generated Ninja/linker paths on an existing ASCII workspace alias.

ESP-IDF component metadata may canonicalize a directory junction back to a
Unicode path that the Windows Xtensa linker cannot open. Only generated
.ninja/.rsp files under the build directory are rewritten; SDK sources are not.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    alias = os.path.abspath(os.environ["LJYD_WORKSPACE"])
    real = os.path.realpath(alias)
    build = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(alias) / "artifacts" / "build"
    if not build.resolve().is_relative_to((Path(real) / "artifacts").resolve()):
        raise ValueError("Build directory must be under workspace artifacts")
    pairs = []
    for separator in ("/", "\\"):
        original = real.replace("\\", separator).replace("/", separator) + separator
        replacement = alias.replace("\\", separator).replace("/", separator) + separator
        pairs.append((original.encode("utf-8"), replacement.encode("utf-8")))
        pairs.append((original.replace(":", "$:").encode("utf-8"),
                      replacement.replace(":", "$:").encode("utf-8")))
    changed = 0
    for pattern in ("*.ninja", "*.rsp"):
        for path in build.rglob(pattern):
            before = path.read_bytes()
            after = before
            for original, replacement in pairs:
                after = after.replace(original, replacement)
            if after != before:
                path.write_bytes(after)
                changed += 1
    # The final app object aggregates all component include paths and can exceed
    # Windows' CreateProcess command-line limit. Keep its flags in a response file.
    rules_path = build / "CMakeFiles" / "rules.ninja"
    if rules_path.exists():
        text = rules_path.read_text(encoding="utf-8")
        start = text.find("rule C_COMPILER__vb701n.2eelf_unscanned_")
        if start >= 0:
            end = text.find("\n\n", start)
            section = text[start:end]
            if "$DEFINES $INCLUDES $FLAGS" in section and "rspfile =" not in section:
                section = section.replace("$DEFINES $INCLUDES $FLAGS", "@$out.flags.rsp")
                section += "\n  rspfile = $out.flags.rsp\n  rspfile_content = $DEFINES $INCLUDES $FLAGS"
                rules_path.write_text(text[:start] + section + text[end:], encoding="utf-8")
    print(f"ASCII workspace paths normalized in {changed} generated Ninja/response files.")


if __name__ == "__main__":
    main()
