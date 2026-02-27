path = "/app/nanobot/providers/registry.py"
with open(path) as f:
    code = f.read()

old = 'keywords=("qwen", "dashscope")'
new = 'keywords=("dashscope",)'

if old in code:
    code = code.replace(old, new)
    with open(path, "w") as f:
        f.write(code)
    print("OK: removed qwen from dashscope keywords")
else:
    print("SKIP: already patched or not found")
