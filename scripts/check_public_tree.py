"""Small public-tree hygiene check; not a complete secret-scanning product."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOTS = {
    ".espressif", ".local", "logs", "artifacts", "backups",
}
PRIVATE_PREFIXES = ("docs/reference/", "docs/research/")
BINARY_SUFFIXES = {".bin", ".elf", ".map", ".dump", ".key", ".p12", ".pfx"}
SECRET_PATTERNS = (
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----")),
    ("product secret", re.compile(r'CONFIG_XJIANG_CLOUD_SECERT\s+"[A-Za-z0-9]{16,}"')),
)
REQUIRED = (
    "README.md", "AGENTS.md", "CONTRIBUTING.md", ".gitignore", ".gitmodules",
    "docs/STATUS.md", "docs/build.md", "docs/hardware-bringup.md",
    "docs/development-guidelines.md", "scripts/setup.cmd", "scripts/build.cmd",
)


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    entries = []
    for item in result.stdout.split(b"\0"):
        if not item:
            continue
        metadata, raw_name = item.split(b"\t", 1)
        mode = metadata.split(b" ", 1)[0].decode("ascii")
        entries.append((mode, raw_name.decode("utf-8")))
    errors = []
    scanned = 0
    for mode, name in entries:
        if mode == "160000":
            if name != "ljyd-sdk":
                errors.append(f"Unexpected submodule: {name}")
            continue
        path = ROOT / name
        if name.split("/", 1)[0] in PRIVATE_ROOTS or name.startswith(PRIVATE_PREFIXES):
            errors.append(f"Private path is tracked: {name}")
        if path.suffix.lower() in BINARY_SUFFIXES:
            errors.append(f"Binary/credential file is tracked: {name}")
        if path.name.startswith(".env") and not path.name.endswith(".example"):
            errors.append(f"Environment secrets file is tracked: {name}")
        if not path.exists():
            errors.append(f"Tracked file is absent: {name}")
            continue
        blob = path.read_bytes()
        if b"\0" in blob:
            errors.append(f"Unexpected binary content: {name}")
            continue
        try:
            text = blob.decode("utf-8-sig")
        except UnicodeDecodeError:
            errors.append(f"Text is not UTF-8: {name}")
            continue
        scanned += 1
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"Possible {label}: {name} (value suppressed)")
        if path.suffix.lower() == ".md":
            for target in re.findall(r"\]\(([^\s)]+)\)", text):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                target = target.split("#", 1)[0]
                if target and not (path.parent / target).exists():
                    errors.append(f"Missing local Markdown target in {name}: {target}")
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            errors.append(f"Missing required project file: {name}")
    if errors:
        print("Public-tree check FAILED:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Public-tree check passed: {scanned} text files; SDK gitlink excluded from content scanning.")
    print("Scope: tracked working-tree paths and selected patterns only; manually review staged diff and history.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
