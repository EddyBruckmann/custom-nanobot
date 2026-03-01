#!/usr/bin/env python3
"""
Patch: Multi-Tier Provider Router v0
Modifica base.py y loop.py para agregar routing multi-provider.

Archivos que toca:
  /app/nanobot/providers/base.py  — agrega routed_chat() a LLMProvider
  /app/nanobot/agent/loop.py      — reemplaza .chat( por .routed_chat(
"""

# ==========================================
# PATCH 1: base.py — agregar routed_chat()
# ==========================================

BASE_PATH = "/app/nanobot/providers/base.py"

ROUTER_CODE = '''

# ================================================================
# === Router v0: Multi-Tier Provider Routing ===
# ================================================================
import json as _json
import os as _os
import time as _time
from pathlib import Path as _Path

_routing_config = None
_routing_mtime = 0.0
_tier_clients: dict = {}
_cooldowns: dict = {}
_ROUTING_PATH = _Path("/root/.nanobot/routing.json")


def _load_routing():
    """Load routing.json, cached by file mtime."""
    global _routing_config, _routing_mtime
    if not _ROUTING_PATH.exists():
        return None
    try:
        mtime = _ROUTING_PATH.stat().st_mtime
        if mtime != _routing_mtime or _routing_config is None:
            _routing_config = _json.loads(_ROUTING_PATH.read_text())
            _routing_mtime = mtime
    except Exception:
        return None
    return _routing_config


def _get_tier_client(pcfg, fallback_key):
    """Get or create AsyncOpenAI client for a tier."""
    name = pcfg["name"]
    if name not in _tier_clients:
        from openai import AsyncOpenAI
        env_var = pcfg.get("apiKeyEnv", "")
        api_key = _os.environ.get(env_var, "") if env_var else ""
        if not api_key:
            api_key = fallback_key
        _tier_clients[name] = AsyncOpenAI(
            api_key=api_key, base_url=pcfg["apiBase"]
        )
    return _tier_clients[name]


def _parse_tier_response(response):
    """Parse OpenAI response into LLMResponse."""
    try:
        import json_repair
        _loads = json_repair.loads
    except ImportError:
        _loads = _json.loads

    choice = response.choices[0]
    msg = choice.message
    tool_calls = []
    for tc in (msg.tool_calls or []):
        args = tc.function.arguments
        tool_calls.append(ToolCallRequest(
            id=tc.id, name=tc.function.name,
            arguments=_loads(args) if isinstance(args, str) else args
        ))
    u = response.usage
    return LLMResponse(
        content=msg.content, tool_calls=tool_calls,
        finish_reason=choice.finish_reason or "stop",
        usage={"prompt_tokens": u.prompt_tokens,
               "completion_tokens": u.completion_tokens,
               "total_tokens": u.total_tokens} if u else {},
        reasoning_content=getattr(msg, "reasoning_content", None) or None,
    )


async def _routed_chat(self, messages, tools=None, model=None, **kwargs):
    """Chat with multi-tier routing. Falls back to self.chat() if no routing."""
    config = _load_routing()
    if not config or config.get("strategy") == "off":
        return await self.chat(messages, tools, model, **kwargs)

    has_tools = bool(tools)
    now = _time.time()
    cooldown_secs = config.get("cooldownSeconds", 60)
    fallback_msg = config.get("fallbackMessage",
                              "Estoy saturado, proba en un rato")

    # API key del provider original (fallback para tiers sin apiKeyEnv)
    fallback_key = "no-key"
    if hasattr(self, "_client") and hasattr(self._client, "api_key"):
        fallback_key = self._client.api_key
    elif hasattr(self, "api_key"):
        fallback_key = self.api_key

    providers = sorted(
        config.get("providers", []),
        key=lambda p: p.get("priority", 99)
    )

    last_error = None
    for pcfg in providers:
        caps = pcfg.get("capabilities", [])

        # Skip: necesita tools pero este tier es chat-only
        if has_tools and "tools" not in caps:
            continue

        # Skip: en cooldown
        if _cooldowns.get(pcfg["name"], 0) > now:
            continue

        client = _get_tier_client(pcfg, fallback_key)
        use_model = pcfg.get("model", model or "default")
        use_tools = tools if ("tools" in caps) else None

        call_kwargs = {
            "model": use_model,
            "messages": self._sanitize_empty_content(messages),
            "max_tokens": max(1, kwargs.get("max_tokens", 4096)),
            "temperature": kwargs.get("temperature", 0.7),
        }
        if use_tools:
            call_kwargs["tools"] = use_tools
            call_kwargs["tool_choice"] = "auto"

        try:
            resp = await client.chat.completions.create(**call_kwargs)
            return _parse_tier_response(resp)
        except Exception as e:
            err = str(e).lower()
            if any(kw in err for kw in ("429", "rate limit", "rate_limit",
                                         "too many", "tokens per minute")):
                _cooldowns[pcfg["name"]] = now + cooldown_secs
            elif any(kw in err for kw in ("context length", "too long",
                                           "maximum context")):
                _cooldowns[pcfg["name"]] = now + cooldown_secs
            else:
                _cooldowns[pcfg["name"]] = now + (cooldown_secs // 4)
            last_error = str(e)
            continue

    detail = f" ({last_error[:100]})" if last_error else ""
    return LLMResponse(
        content=f"{fallback_msg}{detail}", finish_reason="error"
    )


# Monkey-patch: agregar routed_chat a LLMProvider
LLMProvider.routed_chat = _routed_chat
# ================================================================
'''

with open(BASE_PATH) as f:
    code = f.read()

if "_routed_chat" in code:
    print("ROUTER PATCH base.py: SKIP — already patched")
else:
    code += ROUTER_CODE
    with open(BASE_PATH, "w") as f:
        f.write(code)
    print("ROUTER PATCH base.py: OK — appended routed_chat()")


# ==========================================
# PATCH 2: loop.py — usar routed_chat()
# ==========================================

LOOP_PATH = "/app/nanobot/agent/loop.py"

with open(LOOP_PATH) as f:
    loop_code = f.read()

OLD = "await self.provider.chat("
NEW = "await self.provider.routed_chat("

if NEW in loop_code:
    print("ROUTER PATCH loop.py: SKIP — already patched")
elif OLD in loop_code:
    # Solo reemplazar la primera ocurrencia (en _run_agent_loop)
    loop_code = loop_code.replace(OLD, NEW, 1)
    with open(LOOP_PATH, "w") as f:
        f.write(loop_code)
    print("ROUTER PATCH loop.py: OK — .chat( -> .routed_chat(")
else:
    print("ROUTER PATCH loop.py: FAILED — pattern not found")
