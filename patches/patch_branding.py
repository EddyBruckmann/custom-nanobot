#!/usr/bin/env python3
"""
Patch de branding: reemplazar referencias a "nanobot" y el emoji 🐈
en los mensajes visibles del gateway y la CLI.

Busca recursivamente en /app/nanobot/ y en site-packages.
Solo toca strings de log/print, no nombres de módulos ni imports.
"""

import os
import glob

patched_files = 0 

# === Part 1: Patch __logo__ in __init__.py ===
LOGO_FILES = [
    "/app/nanobot/__init__.py",
]
import glob as _glob
LOGO_FILES.extend(_glob.glob("/usr/local/lib/python*/site-packages/nanobot/__init__.py"))
for lf in LOGO_FILES:
    if not os.path.isfile(lf):
        continue
    try:
        with open(lf) as f:
            content = f.read()
        original = content
        # Match __logo__ = "🐱" or __logo__ = "🐈" (any cat emoji)
        content = content.replace('__logo__ = "🐱"', '__logo__ = "🥃"')
        content = content.replace('__logo__ = "🐈"', '__logo__ = "🥃"')
        content = content.replace("__logo__ = '🐱'", "__logo__ = '🥃'")
        content = content.replace("__logo__ = '🐈'", "__logo__ = '🥃'")
        if content != original:
            with open(lf, "w") as f:
                f.write(content)
            print(f"LOGO PATCH: {lf}")
            patched_files += 1
    except Exception:
        continue
# === Part 2: Patch f-string references ===
# In source code, the prefix is f"{__logo__} nanobot" — not a literal emoji
REPLACEMENTS = [
    # f-string patterns (these are the ACTUAL strings in the .py source)
    ("__logo__} nanobot", "__logo__} Nelson"),
    # Startup messages (literal strings)
    ("🐈 Starting nanobot gateway", "🥃 Starting Nelson gateway"),
    ("🐈 Starting nanobot", "🥃 Starting Nelson"),
    ('"nanobot gateway"', '"Nelson gateway"'),
    ("nanobot gateway on port", "Nelson gateway on port"),
    ("Starting nanobot agent", "Starting Nelson agent"),
    # Fallback: literal emoji+name (por si algún archivo los tiene)
    ("🐈 nanobot", "🥃 Nelson"),
    ("🐱 nanobot", "🥃 Nelson"),
]

# Directories to scan
SCAN_DIRS = [
    "/app/nanobot/",
]

# Also scan site-packages for CLI
site_matches = glob.glob("/usr/local/lib/python*/site-packages/nanobot/")
SCAN_DIRS.extend(site_matches)

patched_files = 0

for scan_dir in SCAN_DIRS:
    if not os.path.isdir(scan_dir):
        continue
    for root, dirs, files in os.walk(scan_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath) as f:
                    content = f.read()
            except Exception:
                continue

            original = content
            for old, new in REPLACEMENTS:
                content = content.replace(old, new)

            if content != original:
                with open(fpath, "w") as f:
                    f.write(content)
                patched_files += 1
                print(f"BRANDING PATCH: {fpath}")

if patched_files:
    print(f"BRANDING OK: patched {patched_files} file(s)")
else:
    print("BRANDING SKIP: no matching patterns found (puede que los strings hayan cambiado en esta versión)")
