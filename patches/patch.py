path1 = "/app/nanobot/providers/registry.py"
with open(path1) as f:
    code = f.read()

if "cerebras" not in code:
    new_entry = """
    # Cerebras: fast inference
    ProviderSpec(
        name="cerebras",
        keywords=("cerebras",),
        env_key="CEREBRAS_API_KEY",
        display_name="Cerebras",
        litellm_prefix="cerebras",
        skip_prefixes=("cerebras/",),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),

"""
    code = code.replace("    # === Auxiliary", new_entry + "    # === Auxiliary")
    with open(path1, "w") as f:
        f.write(code)
    print("OK: registry.py patched")
else:
    print("SKIP: registry already has cerebras")

path2 = "/app/nanobot/config/schema.py"
with open(path2) as f:
    code = f.read()

if "cerebras" not in code:
    old = "    groq: ProviderConfig = Field(default_factory=ProviderConfig)"
    new = old + "\n    cerebras: ProviderConfig = Field(default_factory=ProviderConfig)"
    code = code.replace(old, new)
    with open(path2, "w") as f:
        f.write(code)
    print("OK: schema.py patched")
else:
    print("SKIP: schema already has cerebras")
