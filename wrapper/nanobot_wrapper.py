#!/usr/bin/env python3
"""
Wrapper HTTP server para NanoBot gateway.
Workaround para Issue #510: el gateway no binds el puerto HTTP.

Recibe POST /v1/chat/completions (formato OpenAI) y ejecuta
`nanobot agent -m "mensaje"` por subprocess. Devuelve la respuesta
en formato OpenAI-compatible.

Puerto: 18790 (mismo que el gateway debería usar).
"""

import json
import subprocess
import time
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

WRAPPER_PORT = int(os.environ.get("WRAPPER_PORT", 18790))
NANOBOT_TIMEOUT = int(os.environ.get("NANOBOT_TIMEOUT", 120))  # segundos


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    """Endpoint compatible con OpenAI chat completions."""
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    messages = body.get("messages", [])
    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    # Tomar el último mensaje del usuario
    user_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break

    if not user_msg:
        return jsonify({"error": "No user message found"}), 400

    # Ejecutar nanobot agent -m "mensaje"
    try:
        result = subprocess.run(
            ["nanobot", "agent", "-m", user_msg],
            capture_output=True,
            text=True,
            timeout=NANOBOT_TIMEOUT,
        )
        assistant_reply = result.stdout.strip()

        # Si stdout está vacío pero hay stderr, reportar error
        if not assistant_reply and result.stderr:
            return jsonify({
                "error": f"NanoBot error: {result.stderr.strip()}"
            }), 502

        if not assistant_reply:
            assistant_reply = "(sin respuesta)"

    except subprocess.TimeoutExpired:
        return jsonify({"error": "NanoBot timeout"}), 504
    except Exception as e:
        return jsonify({"error": f"Subprocess error: {str(e)}"}), 500

    # Respuesta formato OpenAI
    return jsonify({
        "id": f"wrapper-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": assistant_reply
            },
            "finish_reason": "stop"
        }]
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check."""
    return jsonify({"status": "ok", "wrapper": True})


if __name__ == "__main__":
    print(f"Wrapper HTTP server listening on 0.0.0.0:{WRAPPER_PORT}")
    app.run(host="0.0.0.0", port=WRAPPER_PORT, threaded=True)
