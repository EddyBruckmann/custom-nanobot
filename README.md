<div align="center">
  <h1>🥃 Nelson — Agente Personal IA basado en NanoBot</h1>
  <p>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <img src="https://img.shields.io/badge/base-nanobot_v0.1.4.post2-orange" alt="Base">
    <img src="https://img.shields.io/badge/provider-Cerebras-purple" alt="Cerebras">
    <img src="https://img.shields.io/badge/canal-WhatsApp-25D366?logo=whatsapp&logoColor=white" alt="WhatsApp">
  </p>
</div>

**Nelson** es un agente personal de IA ultra-ligero construido sobre [NanoBot](https://github.com/HKUDS/nanobot) con modificaciones específicas para optimizar costos, mejorar la gestión de memoria y agregar routing inteligente de proveedores LLM.

> **Proyecto base:** [HKUDS/nanobot](https://github.com/HKUDS/nanobot) — un framework de agente IA ultra-liviano (~4,000 líneas de código core).
> Nelson extiende nanobot sin modificar el código fuente directamente, usando un sistema de patches que se aplican durante el build de Docker.

---

## ✨ ¿Qué cambia Nelson respecto al NanoBot original?

| Módulo | Cambio | Descripción |
|--------|--------|-------------|
| 🧠 **Provider Cerebras** | `patch.py` + `patch2.py` | Agrega Cerebras como proveedor LLM (registro + schema). Corrige conflicto de keywords con Dashscope. |
| 🔀 **Router Multi-Tier** | `patch_router.py` | Routing inteligente que sube de tier según la complejidad de la tarea para abaratar costos. Empieza con modelos baratos y escala. |
| 🗂️ **Gestión de Memoria** | `memory_manager.py` | Manager que corre en background: consolida historial antiguo en mega-resúmenes y trunca la memoria si supera límites. |
| 🌐 **Wrapper HTTP** | `nanobot_wrapper.py` | Servidor HTTP compatible con OpenAI API. Workaround para Issue [#510](https://github.com/HKUDS/nanobot/issues/510) donde el gateway no bindeaba el puerto. |
| 🐳 **Docker Custom** | `Dockerfile.nelson` | Dockerfile personalizado que aplica todos los patches y arranca gateway + wrapper + memory manager juntos. |

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│                                                          │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────┐   │
│  │ NanoBot  │   │   Wrapper    │   │    Memory       │   │
│  │ Gateway  │   │   HTTP :18790│   │    Manager      │   │
│  │(WhatsApp,│   │  (OpenAI API │   │  (cada 30 min)  │   │
│  │ Telegram,│   │   compatible)│   │                 │   │
│  │ etc.)    │   │              │   │                 │   │
│  └────┬─────┘   └──────┬───────┘   └────────┬────────┘   │
│       │                │                     │            │
│       ▼                ▼                     ▼            │
│  ┌─────────────────────────────────────────────────┐     │
│  │          NanoBot Core (con patches)              │     │
│  │   ┌─────────┐  ┌──────────┐  ┌──────────────┐   │     │
│  │   │ Agent   │  │ Providers│  │   Router v0   │   │     │
│  │   │ Loop    │  │(Cerebras,│  │  (Multi-Tier) │   │     │
│  │   │         │  │ Groq...) │  │               │   │     │
│  │   └─────────┘  └──────────┘  └──────────────┘   │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │         WhatsApp Bridge (Node.js/Baileys)        │     │
│  └─────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## 🔀 Router Multi-Tier: Cómo funciona

El router implementa un sistema de **cascada por prioridad** que optimiza costos usando el modelo más barato posible:

```
Mensaje entrante
       │
       ▼
  ┌──────────────┐
  │ Tier 0       │  Modelo barato (chat only, sin tools) ejemplo: Cerebras llama3.1-8b 
  │ priority: 0  │  → Rápido y gratis para consultas simples
  └──────┬───────┘
         │ si necesita tools o supera rate limit
         ▼
  ┌──────────────┐
  │ Tier 1       │  Modelo mediano (chat + tools) ejemplo: Cerebras gpt-oss-120b 
  │ priority: 1  │  → Modelo grande con soporte completo
  └──────┬───────┘
         │ si falla o supera rate limit
         ▼
  ┌──────────────┐
  │ Tier 2       │  Modelo grande con mayor contexto ejemplo: Groq llama-3.3-70b 
  │ priority: 2  │  → Respaldo con ventana de contexto grande
  └──────────────┘
```

Configurado en `routing.json`:
```json
{
  "strategy": "cascade",
  "cooldownSeconds": 60,
  "providers": [
    { "name": "cerebras-8b", "model": "llama3.1-8b", "priority": 0, "capabilities": ["chat"] },
    { "name": "cerebras", "model": "gpt-oss-120b", "priority": 1, "capabilities": ["chat", "tools"] },
    { "name": "groq", "model": "llama-3.3-70b-versatile", "priority": 2, "capabilities": ["chat", "tools"] }
  ]
}
```

---

## 🧠 Gestión de Memoria

Nelson extiende el sistema de memoria de NanoBot con un **Memory Manager** que corre en background:

### Niveles de Compresión

| Nivel | Qué es | Formato |
|-------|--------|---------|
| **Nivel 1** | Mensajes crudos | Últimos ~15 mensajes en contexto |
| **Nivel 2** | Resúmenes de sesión | `[YYYY-MM-DD HH:MM] Resumen de 2-5 oraciones` |
| **Nivel 3** | Mega-resúmenes | `[FECHA_INICIO → FECHA_FIN] Resumen condensado` |

- Cada 30 minutos, el memory manager consolida líneas de Nivel 2 en mega-resúmenes de Nivel 3 usando Groq.
- `MEMORY.md` (memoria a largo plazo) se trunca automáticamente a ~2000 caracteres (~500 tokens).

---

## 📦 Estructura del Proyecto

```
custom-nanobot/
├── nanobot/                  # 🧠 NanoBot core (upstream, sin modificar)
│   ├── agent/                #    Agent loop, memoria, skills, tools
│   ├── providers/            #    LLM providers (OpenRouter, Custom, etc.)
│   ├── channels/             #    Integraciones (Telegram, WhatsApp, etc.)
│   ├── bus/                  #    Message routing
│   ├── config/               #    Schema de configuración
│   └── ...
│
├── patches/                  # 🩹 Patches (se aplican en Docker build)
│   ├── patch.py              #    Agrega provider Cerebras
│   ├── patch2.py             #    Fix conflicto keywords Dashscope
│   ├── patch_branding.py     #    Rebranding nanobot → Nelson
│   ├── patch_cli.py          #    Personalización CLI
│   └── patch_router.py       #    Router multi-tier
│
├── wrapper/                  # 🌐 Capa de wrapper
│   ├── nanobot_wrapper.py    #    HTTP server OpenAI-compatible (:18790)
│   ├── memory_manager.py     #    Compresión jerárquica de memoria
│   └── entrypoint.sh         #    Orquestador de procesos
│
├── bridge/                   # 📱 WhatsApp bridge (Node.js/TypeScript)
│   └── src/
│       ├── server.ts         #    WebSocket bridge Python ↔ Node.js
│       └── whatsapp.ts       #    Cliente Baileys
│
├── routing.json              # ⚙️ Config del router multi-tier
├── Dockerfile.nelson         # 🐳 Dockerfile con todos los patches
├── docker-compose.yml        # 🐳 Orquestación Docker
└── pyproject.toml            # 📋 Dependencias Python
```

---

## 🚀 Quick Start

### Pre-requisitos

- Docker + Docker Compose
- API keys: [Cerebras](https://cloud.cerebras.ai/) y/o [Groq](https://console.groq.com/)

### 1. Clonar y configurar

```bash
git clone https://github.com/EddyBruckmann/custom-nanobot.git
cd custom-nanobot
```

Crear archivo `.env` en el root:
```env
GROQ_API_KEY=gsk_xxx
CEREBRAS_API_KEY=csk_xxx
```

### 2. Inicializar NanoBot

```bash
docker compose run --rm nanobot-cli onboard
```

Editar `~/.nanobot/config.json` para configurar el proveedor y los canales:

```json
{
  "providers": {
    "custom": {
      "apiKey": "tu-cerebras-key",
      "apiBase": "https://api.cerebras.ai/v1"
    }
  },
  "agents": {
    "defaults": {
      "model": "llama3.1-8b"
    }
  },
  "channels": {
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["+549xxxxxxxxxx"]
    }
  }
}
```

### 3. Vincular WhatsApp

```bash
docker compose run --rm nanobot-cli channels login
# Escanear el QR con WhatsApp → Configuración → Dispositivos vinculados
```

### 4. Levantar

```bash
docker compose up -d nanobot-gateway
```

Esto arranca:
- ✅ NanoBot gateway (WhatsApp + otros canales)
- ✅ Wrapper HTTP en puerto 18790
- ✅ Memory manager en background

### Verificar

```bash
# Ver logs
docker compose logs -f nanobot-gateway

# Health check del wrapper
curl http://localhost:18790/health

# Enviar mensaje via API
curl -X POST http://localhost:18790/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hola Nelson!"}]}'
```

---

## ⚙️ Configuración del Router

El router se configura en `~/.nanobot/routing.json` (se copia automáticamente al primer inicio):

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `strategy` | `"cascade"` o `"off"` | `"cascade"` |
| `cooldownSeconds` | Segundos de espera tras rate limit | `60` |
| `fallbackMessage` | Mensaje cuando todos los tiers fallan | `"Estoy saturado..."` |
| `providers[].priority` | Orden de cascada (menor = primero) | — |
| `providers[].capabilities` | `["chat"]` o `["chat", "tools"]` | — |
| `providers[].model` | Modelo a usar en ese tier | — |

Para desactivar el router y usar el provider directo de nanobot:
```json
{ "strategy": "off" }
```

---

## 🩹 Sistema de Patches

Los patches se aplican automáticamente durante `docker build`. Son scripts Python que modifican el código instalado de nanobot en la imagen Docker:

| Patch | Archivo(s) que modifica | Propósito |
|-------|------------------------|-----------|
| `patch.py` | `providers/registry.py` + `config/schema.py` | Registra Cerebras como provider |
| `patch2.py` | `providers/registry.py` | Quita `"qwen"` de los keywords de Dashscope |
| `patch_branding.py` | Múltiples `.py` | Rebranding nanobot → Nelson |
| `patch_cli.py` | `cli/commands.py` | Personalización de la CLI |
| `patch_router.py` | `providers/base.py` + `agent/loop.py` | Inyecta el router multi-tier |

> **Nota**: Los patches de Cerebras están comentados en el Dockerfile porque ahora se usa el provider `custom` de nanobot directamente.

---

## 📱 Canales Soportados

Nelson hereda todos los canales de NanoBot:

| Canal | Notas |
|-------|-------|
| **WhatsApp** | ✅ Principal. Bridge Node.js incluido en el Docker. |
| **Telegram** | Soportado via BotFather token |
| **Discord** | Soportado |
| **Slack** | Socket Mode |
| **Email** | IMAP/SMTP |
| **Feishu** | WebSocket |
| **DingTalk** | Stream Mode |
| **QQ** | WebSocket |

Para configurar otros canales, ver la [documentación de NanoBot](https://github.com/HKUDS/nanobot#-chat-apps).

---

## 🤖 Proveedores LLM

| Provider | Uso en Nelson |
|----------|---------------|
| **Cerebras** | Provider principal (rápido, gratis en tier gratuito) |
| **Groq** | Fallback para el router + transcripción de audio (Whisper) |
| **Custom** | Endpoint OpenAI-compatible (usado para Cerebras) |

Nelson también soporta todos los providers de NanoBot (OpenRouter, Anthropic, OpenAI, DeepSeek, Gemini, etc.).

---

## 🐳 Docker

### Build manual

```bash
docker build -f Dockerfile.nelson -t nelson .
docker run -v ~/.nanobot:/root/.nanobot -p 18790:18790 nelson
```

### Docker Compose (recomendado)

```bash
docker compose up -d nanobot-gateway     # Gateway + wrapper + memory manager
docker compose run --rm nanobot-cli agent -m "Hola!"  # CLI
docker compose logs -f nanobot-gateway   # Logs
docker compose down                      # Parar todo
```

---

## 🙏 Créditos

- **[NanoBot](https://github.com/HKUDS/nanobot)** — Framework base, por [HKUDS](https://github.com/HKUDS) (HKU Data Science Lab). Ultra-ligero, ~4,000 líneas de código core, licencia MIT.
- **[Baileys](https://github.com/WhiskeySockets/Baileys)** — Cliente WhatsApp Web API usado en el bridge.
- **[Cerebras](https://cerebras.ai/)** — Inferencia LLM ultra-rápida.
- **[Groq](https://groq.com/)** — Inferencia LLM rápida + transcripción de audio.

---

## 📄 Licencia

Este proyecto hereda la licencia [MIT](./LICENSE) de NanoBot.

<p align="center">
  <sub>Nelson es un proyecto personal para uso educativo y experimental</sub>
</p>
