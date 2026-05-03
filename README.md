# Accel

A local-first personal operating system for Intelligence Amplification — not a chatbot, but an organism with persistent memory, context-aware routing, agentic tool execution, voice interface, and a consistent cognitive profile across all domains.

Built as a custom Python-native stack using **FastAPI + a custom agentic loop**. Inference runs locally via llama.cpp on an AMD GPU (ROCm), with optional cloud API fallback (OpenAI, Anthropic) through a pluggable model registry.

---

## Architecture

```
                         ┌─────────────┐
                         │   nginx:80  │  serves UI + proxies API
                         └──────┬──────┘
                                │
                    ┌───────────▼───────────┐
                    │   FastAPI :8100       │
                    │   /chat (SSE stream)  │
                    └───────────┬───────────┘
                                │
                 ┌──────────────▼──────────────┐
                 │  Tier 0 — regex fast-filter  │  greetings, acks, bare URLs → instant response
                 └──────────────┬──────────────┘
                                │ (no match)
                 ┌──────────────▼──────────────┐
                 │  Router — heuristic classify │  no LLM call
                 └──────────────┬──────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                  ▼
        direct_chat      preprocessed_text    multimodal
              │                 │                  │
              ▼                 ▼                  ▼
        (pre-flight        code-splitter       Image preprocess
         currently          (AST/log/doc        (1280px max)
         disabled)          chunking)
              │                 │                  │
              └─────────────────┼──────────────────┘
                                │
                 ┌──────────────▼──────────────┐
                 │   Hybrid Memory Retrieval    │  dense + sparse (BM25) → RRF fusion
                 │   facts, procedures, notes,  │
                 │   sources, episodes          │
                 └──────────────┬──────────────┘
                                │
                 ┌──────────────▼──────────────┐
                 │   Agentic Loop              │
                 │   ~50 tools, approval gate,  │
                 │   stall detection, streaming │
                 └─────────────────────────────┘
```

---

## Desktop App (Electron)

React + Vite + Electron 41 + Tailwind CSS 4. Built as AppImage on Linux.

- **Sessions:** persistent multi-session chat with session switching, each backed by Qdrant
- **Split panels:** chat + right panel (canvas, files, music, notes, images) — sessions like "architecture" auto-show the canvas panel
- **Canvas:** tldraw v2.4.0 embedded whiteboard — model can draw shapes via tool calls, canvas state persisted to backend, screenshot tool lets model read the canvas via vision
- **Music:** Navidrome/Subsonic in-browser player with Now Playing widget, playlist management, SoundCloud/YouTube search+download
- **Service dashboard:** start/stop/restart for all stack services (Docker, systemd, native processes) with health status, ports, and log viewer
- **Approval flow:** irreversible tool calls show inline approve/deny prompt — keyboard navigable (arrow keys + Enter)
- **Settings:** tool policy overrides, context state toggle, theme, Open DevTools
- **Notes browser:** Obsidian vault search and viewing
- **Build:** `npm run build:electron` → `release/Accel-0.0.0.AppImage`

### Tech Stack

| Layer | Tech |
|---|---|
| Framework | React 19, TypeScript 6 |
| Build | Vite 8, electron-builder |
| Styling | Tailwind CSS 4 |
| State | Zustand |
| Canvas | tldraw 2.4.0 |
| Markdown | marked + DOMPurify |
| Desktop | Electron 41 |

---

## Memory Layers

| Layer | Store | Description |
|-------|-------|-------------|
| L0 — Working | Qdrant `sessions` | Full message history, persists across restarts |
| L1 — Episodic | Qdrant `episodes` | Token-aware compression (24k threshold), curator-summarized |
| L2 — Semantic | Qdrant `facts` | Extracted facts about the user, content-hash dedup |
| L3 — Knowledge | Qdrant `sources` + `notes` | Ingested documents + Obsidian vault (separate collection) |
| L4 — Procedural | Qdrant `procedures` | Interaction patterns, extracted post-response |
| L5 — Profile | `user_profile.json` | Stable context injected into every prompt |

All collections use **named vectors** (`dense` + `sparse`) with hybrid search: BM25-style sparse vectors fused with dense embeddings via Qdrant's native Reciprocal Rank Fusion. Retrieval reranks by `0.7 * semantic + 0.3 * recency` with slow time decay.

---

## Routing

**Tier 0** (regex, <1ms): catches greetings, acknowledgments, farewells, bare URLs, memory commands, and short casual inputs. Matched intents get canned responses or optimized pipeline flags — skips model inference entirely when possible.

**Tier 1** (heuristic classifier): routes by content type with no LLM call.

| Route family | Text type | Pipeline |
|---|---|---|
| `direct_chat` | chat | Pre-flight + retrieval + chat model |
| `preprocessed_text` | code | AST splitting → Coder personality |
| `preprocessed_text` | logs | Log-aware chunking → Coder personality |
| `preprocessed_text` | chat_dump | Speaker-turn splitting → no retrieval |
| `preprocessed_text` | document | Section splitting → progressive summarization |
| `multimodal` | — | Image preprocessing + optional retrieval + vision model |

---

## Tools (~50)

The agentic loop executes tools with an **approval gate** — irreversible actions require user confirmation via inline UI prompt.

| Category | Tools |
|---|---|
| File | `read_file`, `write_file`, `edit_file`, `delete_file`, `get_file_info`, `move_file`, `download_file` |
| System | `bash`, `search_files`, `list_dir` |
| Web | `search_web`, `fetch_url`, `screenshot_url` |
| Compute | `calculate`, `convert_units`, `convert_currency` |
| Calendar | `calendar_today`, `calendar_get_events`, `calendar_add_event`, `calendar_delete_event` |
| Memory/KB | `search_knowledge_base`, `list_knowledge_base`, `search_notes`, `list_notes`, `ingest_note`, `ingest_file`, `delete_source`, `delete_note`, `search_facts`, `search_procedures`, `search_episodes`, `save_memory`, `update_memory`, `delete_memory` |
| Music | `search_music`, `download_music`, `navidrome_search`, `navidrome_get_playlists`, `navidrome_get_playlist`, `navidrome_create_playlist`, `navidrome_update_playlist`, `navidrome_delete_playlist`, `player_control`, `player_now_playing`, `player_load`, `soundcloud_get_playlists`, `soundcloud_get_playlist` |
| Media | `search_audiobooks`, `add_torrent` |
| Canvas | `canvas_draw`, `canvas_clear`, `canvas_get_state`, `canvas_screenshot` |

Idempotent guards on create operations (calendar events, playlists) prevent duplicates from agentic retries.

---

## Voice Pipeline

Wake word → STT → chat → TTS, runs as a background thread.

- **Wake word:** "Hey Jarvis" via openWakeWord (80ms chunks, Silero VAD)
- **STT:** faster-whisper `base`, CPU int8, auto language detection (Polish + English)
- **TTS:** Piper `en_US-lessac-medium`, offline WAV → sounddevice playback
- **Voice mode:** injects system addendum for concise spoken responses, strips markdown/code/URLs before TTS
- Tool status spoken mid-turn ("Let me search for that...")

---

## Model Registry

Pluggable model definitions with runtime switching. Three roles — chat, curator, embeddings — each independently swappable across local and cloud providers.

| ID | Provider | Context | Notes |
|---|---|---|---|
| `qwen-9b` | llama_cpp (local GPU) | 65K | Default chat. Vision, thinking, turbo4 KV cache. |
| `qwen-0.8b` | llama_cpp (local GPU) | 8K | Default curator. Episode compression. |
| `bge-m3` | llama_cpp (local CPU) | 8K | Default embeddings. 1024-dim (locked). |
| `gpt-4o` | openai | 128K | Cloud fallback. Vision. Needs API key. |
| `gpt-4.1` | openai | 1M | Cloud fallback. Vision. |
| `claude-sonnet` | anthropic | 200K | Cloud fallback. Vision, extended thinking. |

**Switching:** `/model gpt-4o` in chat, Settings UI selector, `CHAT_MODEL_ID` env var, or `PUT /models/active`. Custom models via `CUSTOM_MODELS` env var. Per-session override in SSE payload.

**Backend dispatch:** llama_cpp and openai use OpenAI-compatible `/v1/chat/completions`; anthropic translates to Messages API with SSE event conversion.

---

## Inference Stack

Three models run simultaneously on a single RX 6700 XT (12 GB VRAM):

| Model | Role | VRAM | Speed |
|---|---|---|---|
| Qwen3.5-9B Q6_K | Chat + vision | ~9.5 GB | 40 t/s |
| Qwen3.5-0.8B Q8_0 | Curator (episode compression) | ~0.8 GB | 163 t/s |
| bge-m3 Q8_0 | Embeddings (1024-dim) | CPU | — |
| **Total** | | **~10.5 GB** | |

**TurboQuant+ KV cache:** Chat model uses a [llama-cpp-turboquant](https://github.com/TheTom/llama-cpp-turboquant) fork with `-ctk turbo4 -ctv turbo4` — compresses KV cache from ~2 GB (f16) to 544 MB at 65K context with only +0.96% perplexity impact. This frees the VRAM headroom needed to fit the curator and vision projector alongside the chat model.

**Vision:** mmproj projector loaded with the chat model — image inputs are preprocessed to 1280px max and passed through the vision encoder.

**Curator:** 0.8B model handles episode compression at 163 t/s on GPU. Pre-flight (personality + thinking depth) is currently disabled — personality defaults to "Casual", thinking budget is fixed 16384 tokens. Uses raw `/completion` endpoint with `<think>\n</think>\n` injection.

---

## Reliability

**Circuit breakers** across 8 service domains (qdrant, splitter, chat_model, curator, embeddings, searxng, playwright, navidrome). Each breaker tracks failures with configurable thresholds and cooldowns, transitions through closed → open → half-open states, with per-domain fallback strategies (cached data, graceful degradation).

**Stall detection** in the agentic loop: fingerprints tool calls and response text via sliding window. Nudges the model on first repeat, force-stops on second.

**Centralized logging:** daily rotating log files with decision-point logging across router, preflight, retrieval, and tool execution.

Health endpoint at `/health` reports circuit breaker status for all domains.

---

## Services

All inference and storage runs locally. Optional cloud API fallback via model registry.

| Service | Port | Role |
|---|---|---|
| Bootstrap API | 8100 | FastAPI, custom agentic loop |
| nginx | 80 | Serves Electron/React build, proxies API + Navidrome |
| llama.cpp chat | 8080 | GPU (TurboQuant+, turbo4 KV, mmproj), 65K context |
| llama.cpp embeddings | 8081 | CPU (Docker), bge-m3 1024-dim |
| llama.cpp curator | 8082 | GPU (native), Qwen3.5-0.8B, 8K context |
| llama.cpp mini | 8083 | CPU (Docker), Qwen3.5-0.8B, 32K ctx (backup) |
| code-splitter | 9200 | AST chunking, log splitting, image preprocess, ingest |
| SearXNG | 8888 | Web search backend |
| Playwright | 9300 | Headless browser / screenshot |
| MCP Server | 9400 | Tool MCP bridge |
| Qdrant | 6333 | Vector database (6 collections, hybrid search) |
| MinIO | 9000 | Object storage |
| Navidrome | 4533 | Local music server (Subsonic API) |
| Forgejo | 3000 | Self-hosted git |
| Prometheus | 9090 | Metrics scraping |
| Grafana | 3001 | Dashboards |
| Portainer | 9003 | Docker management |

---

## Project Structure

```
bootstrap/
├── api/
│   ├── chat.py              # /chat SSE endpoint, tier0 + router dispatch
│   ├── canvas.py            # Canvas state + PNG snapshot persistence
│   ├── music.py             # Now playing, player control
│   └── voice.py             # Voice toggle, status
├── agents/
│   ├── chat_agent.py        # Agentic loop: retrieval, tool exec, stall detection, streaming
│   └── preprocessed_agent.py
├── router/
│   ├── tier0.py             # Regex fast-filter (greetings, acks, URLs, memory)
│   └── classifier.py        # Heuristic input classifier
├── memory/
│   ├── facts.py             # Hybrid search, recency reranking, shared _hybrid_search()
│   ├── sources.py           # Knowledge base search
│   ├── notes.py             # Obsidian vault search
│   ├── episodes.py          # Token-aware compression + episode storage
│   ├── extraction.py        # Post-response fact + procedure extraction
│   ├── profile.py           # User profile with circuit breaker fallback
│   ├── sessions.py          # Session persistence
│   └── sparse.py            # BM25-style sparse vector generation
├── curator/
│   └── preflight.py         # Personality + thinking depth selection
├── tools/
│   ├── llm.py               # chat_complete, curator_complete, embed
│   ├── web_tools.py         # search_web, fetch_url, screenshot_url
│   ├── code_tools.py        # read/write/edit/delete/move files, bash, search
│   ├── calendar_tools.py    # SQLite calendar with Polish holidays
│   ├── navidrome_tools.py   # 13 Navidrome/music tools
│   ├── canvas_tools.py      # Canvas draw/clear/state/screenshot
│   └── tool_descriptions.py # Tool registry with irreversibility flags
├── voice/
│   ├── pipeline.py          # Wake word → STT → chat → TTS orchestration
│   ├── stt.py               # faster-whisper wrapper
│   ├── tts.py               # Piper TTS wrapper
│   ├── listener.py          # Audio capture + wake word detection
│   └── filter.py            # Response cleaning for speech output
├── ui/                      # Electron + React desktop app
│   ├── electron/
│   │   ├── main.ts          # Electron main process, proxy server, IPC
│   │   ├── preload.ts       # Context bridge (IPC, window management)
│   │   ├── services.ts      # Service management (Docker, systemd, native)
│   │   ├── ipc-handlers.ts  # IPC handler registration
│   │   └── types.ts         # Electron-side type definitions
│   └── src/
│       ├── components/
│       │   ├── chat/        # InputBar, MessageItem, MessageStream, ApprovalBlock
│       │   ├── layout/      # AppShell, LeftNav, RightPanel, TitleBar
│       │   ├── panels/      # Canvas, Files, Music, Notes, ImagePreview
│       │   ├── services/    # ServiceDashboard, ServiceGroupCard, LogsModal
│       │   ├── sessions/    # SessionList, SessionButton
│       │   └── overlays/    # SettingsDialog
│       ├── stores/          # Zustand state (chat, sessions, settings)
│       └── api/             # Backend + Electron API clients
├── docs/
│   └── llama_benchmarks.md  # Speed, quality, VRAM benchmarks across quants
├── circuit_breaker.py       # Per-domain circuit breakers (8 services)
├── logging_config.py        # Centralized daily-rotating log setup
├── config.py                # Single config object, env vars
├── nginx.conf
└── main.py                  # uvicorn entry point
```

---

## Setup

**Prerequisites:** llama.cpp with ROCm support, Qdrant, MinIO, code-splitter running.

```bash
cd /home/rezxt/bootstrap
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python main.py
```

Start supporting services:
```bash
docker compose up -d
```

Start chat model (TurboQuant+ with vision):
```bash
/home/rezxt/ai-stack/llama-cpp-turboquant/build/bin/llama-server \
  -m /mnt/WD/Models/Qwen3.5-9B-Q6_K.gguf \
  --mmproj /mnt/WD/Models/Qwen3.5-9B.mmproj-Q8_0.gguf \
  -c 65536 --host 0.0.0.0 --port 8080 \
  -ngl 99 --jinja --ubatch-size 256 \
  -ctk turbo4 -ctv turbo4
```

Start curator:
```bash
llama-server -m /mnt/WD/Models/Qwen3.5-0.8B-Q8_0.gguf \
  -c 8192 --host 0.0.0.0 --port 8082 -ngl 99 --jinja
```

Build desktop app:
```bash
cd ui && npm install && npm run build:electron
ELECTRON_DISABLE_SANDBOX=1 ./release/Accel-0.0.0.AppImage --no-sandbox
```

---

## Hardware

Designed for **Ryzen 5 5600X + RX 6700 XT (12GB VRAM, ROCm) + 32GB RAM**.

- Chat (9B Q6_K) runs on GPU with TurboQuant+ KV compression (`-ctk turbo4 -ctv turbo4`) — 544 MB KV at 65K ctx vs ~2 GB with f16. Includes vision projector (mmproj).
- Curator (0.8B Q8_0) runs on GPU at ~163 t/s — preflight routing + episode compression in <0.5s
- Embeddings run on CPU in Docker
- All three services fit simultaneously: ~10.5 GB / 12 GB VRAM
- All models at `/mnt/WD/Models/`

---

## License

Personal project. Not currently accepting contributions.
