#!/usr/bin/env python3
"""
Patches cosméticos para la CLI de NanoBot.
Patch 3: Cambiar prefijo "You:" → "Eddy:"
Patch 4: Quitar mensaje "Goodbye!" al salir con Ctrl-C
"""

import re

path = "/usr/local/lib/python3.12/site-packages/nanobot/cli/commands.py"

try:
    with open(path) as f:
        code = f.read()
except FileNotFoundError:
    # Intentar con otra versión de Python
    import glob
    matches = glob.glob("/usr/local/lib/python*/site-packages/nanobot/cli/commands.py")
    if not matches:
        print("SKIP: commands.py not found")
        exit(0)
    path = matches[0]
    with open(path) as f:
        code = f.read()

original = code

# Patch 3: You: → Eddy:
code = code.replace("You:", ">")

# Patch 4: Quitar Goodbye!
code = code.replace('console.print("\\nGoodbye!")', 'console.print("\\nSe va la novia")')
code = code.replace("console.print('\\nGoodbye!')", "console.print('\\nSe va la novia')")

if code != original:
    with open(path, "w") as f:
        f.write(code)
    print(f"PATCHES OK: applied to {path}")
else:
    print("PATCHES SKIP: already applied or patterns not found")
