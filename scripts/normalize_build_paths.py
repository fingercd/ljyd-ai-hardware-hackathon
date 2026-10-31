"""Keep generated Ninja/linker paths on an existing ASCII workspace alias.

ESP-IDF component metadata may canonicalize a directory junction back to a
Unicode path that the Windows Xtensa linker cannot open. Only generated
.ninja/.rsp files under the build directory are rewritten; SDK sources are not.
"""
from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    alias = os.path.abspath(os.environ["LJYD_WORKSPACE"])
    real = os.path.realpath(alias)
    build = Path(alias) / "artifacts" / "build"
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
    print(f"ASCII workspace paths normalized in {changed} generated Ninja/response files.")


if __name__ == "__main__":
    main()
