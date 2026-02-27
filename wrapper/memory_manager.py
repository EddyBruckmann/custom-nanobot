#!/usr/bin/env python3
"""
Memory Manager - corre cada 30 min en background.
- Nivel 3: condensa 10+ lineas nivel 2 en HISTORY.md -> 1 mega-resumen
- MEMORY.md: trunca si supera limite de caracteres
"""

import re
import time
import subprocess
import os

HISTORY_PATH = "/root/.nanobot/workspace/memory/HISTORY.md"
MEMORY_PATH = "/root/.nanobot/workspace/memory/MEMORY.md"
INTERVAL = 1800  # 30 minutos
MEMORY_MAX_CHARS = 2000  # ~500 tokens aprox
LEVEL2_PATTERN = re.compile(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\]')
LEVEL3_PATTERN = re.compile(r'^\[\d{4}-\d{2}-\d{2} .+ \d{4}-\d{2}-\d{2}\]')


def summarize_with_llm(lines):
    """Manda las lineas a Groq para un mega-resumen."""
    prompt = (
        "Condensa estas lineas de historial en 1-2 lineas de mega-resumen. "
        "Formato: [FECHA_INICIO -> FECHA_FIN] Resumen.\n\n"
        + "\n".join(lines)
    )
    try:
        import requests
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ.get('GROQ_API_KEY', '')}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[memory_manager] Error en LLM: {e}")

    # Fallback mecanico: solo contar y poner rango de fechas
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', "".join(lines))
    if dates:
        return f"[{dates[0]} -> {dates[-1]}] ({len(lines)} interacciones consolidadas)"
    return None


def process_history():
    """Consolida lineas nivel 2 en mega-resumenes nivel 3."""
    if not os.path.exists(HISTORY_PATH):
        return

    with open(HISTORY_PATH) as f:
        lines = f.readlines()

    level2 = [(i, l) for i, l in enumerate(lines) if LEVEL2_PATTERN.match(l)]

    if len(level2) < 10:
        return

    to_consolidate = level2[:10]
    consolidate_lines = [l for _, l in to_consolidate]
    consolidate_indices = {i for i, _ in to_consolidate}

    mega = summarize_with_llm(consolidate_lines)
    if not mega:
        return

    if not LEVEL3_PATTERN.match(mega):
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', "".join(consolidate_lines))
        if dates:
            mega = f"[{dates[0]} -> {dates[-1]}] {mega}"

    new_lines = [mega.strip() + "\n"]
    for i, l in enumerate(lines):
        if i not in consolidate_indices:
            new_lines.append(l)

    with open(HISTORY_PATH, "w") as f:
        f.writelines(new_lines)

    print(f"[memory_manager] Consolidadas {len(consolidate_lines)} lineas -> mega-resumen")


def process_memory():
    """Trunca MEMORY.md si supera el limite de caracteres."""
    if not os.path.exists(MEMORY_PATH):
        return

    with open(MEMORY_PATH) as f:
        content = f.read()

    if len(content) <= MEMORY_MAX_CHARS:
        return

    lines = content.split("\n")
    truncated = []
    total = 0
    for line in reversed(lines):
        if total + len(line) + 1 > MEMORY_MAX_CHARS:
            break
        truncated.insert(0, line)
        total += len(line) + 1

    with open(MEMORY_PATH, "w") as f:
        f.write("\n".join(truncated))

    print(f"[memory_manager] MEMORY.md truncado: {len(content)} -> {total} chars")


if __name__ == "__main__":
    print(f"[memory_manager] Iniciado. Intervalo: {INTERVAL}s")
    while True:
        try:
            process_history()
            process_memory()
        except Exception as e:
            print(f"[memory_manager] Error: {e}")
        time.sleep(INTERVAL)
