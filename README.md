# Accel

A local-first personal operating system for Intelligence Amplification — not a chatbot, but an organism with persistent memory, context-aware routing, agentic tool execution, voice interface, and a consistent cognitive profile across all domains.

Built as a custom Python-native stack using **FastAPI + a custom agentic loop**. All inference runs locally via llama.cpp on an AMD GPU (ROCm). No cloud dependencies.

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
        Pre-flight        code-splitter       Image preprocess
        (personality      (AST/log/doc        (1280px max)
         + thinking        chunking)
         depth)
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
| Canvas | `canvas_draw`, `canvas_clear`, `canvas_get_state` |

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

## Reliability

**Circuit breakers** across 8 service domains (qdrant, splitter, chat_model, curator, embeddings, searxng, playwright, navidrome). Each breaker tracks failures with configurable thresholds and cooldowns, transitions through closed → open → half-open states, with per-domain fallback strategies (cached data, graceful degradation).

**Stall detection** in the agentic loop: fingerprints tool calls and response text via sliding window. Nudges the model on first repeat, force-stops on second.

**Centralized logging:** daily rotating log files with decision-point logging across router, preflight, retrieval, and tool execution.

Health endpoint at `/health` reports circuit breaker status for all domains.

---

## Services

All inference and storage runs locally. No cloud APIs.

| Service | Port | Role |
|---|---|---|
| Bootstrap API | 8100 | FastAPI, custom agentic loop |
| nginx | 80 | Serves web UI, proxies API + Navidrome |
| llama.cpp chat | 8080 | GPU inference (ROCm), 65K context |
| llama.cpp embeddings | 8081 | CPU (Docker), bge-m3 1024-dim |
| llama.cpp curator | 8082 | CPU (Docker), personality/extraction |
| llama.cpp embeddings (GPU) | 8083 | On-demand, spun up/down dynamically |
| code-splitter | 9200 | AST chunking, log splitting, image preprocess, ingest |
| Qdrant | 6333 | Vector database (6 collections, hybrid search) |
| MinIO | 9000 | Object storage |
| Navidrome | 4533 | Local music server (Subsonic API) |
| Forgejo | 3000 | Self-hosted git |
| Prometheus | 9090 | Metrics scraping |
| Grafana | 3001 | Dashboards |

---

## Project Structure

```
bootstrap/
├── api/
│   ├── chat.py              # /chat SSE endpoint, tier0 + router dispatch
│   ├── canvas.py            # Canvas state persistence
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
│   ├── canvas_tools.py      # Canvas draw/clear/state
│   └── tool_descriptions.py # Tool registry with irreversibility flags
├── voice/
│   ├── pipeline.py          # Wake word → STT → chat → TTS orchestration
│   ├── stt.py               # faster-whisper wrapper
│   ├── tts.py               # Piper TTS wrapper
│   ├── listener.py          # Audio capture + wake word detection
│   └── filter.py            # Response cleaning for speech output
├── circuit_breaker.py       # Per-domain circuit breakers (8 services)
├── logging_config.py        # Centralized daily-rotating log setup
├── config.py                # Single config object, env vars
├── nginx.conf
├── blob_ui.js               # Web UI (vanilla JS, React migration planned)
├── blob_ui.css
├── index.html
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

Start chat model:
```bash
./start_chat_dimoe.sh
```

---

## Hardware

Designed for **Ryzen 5 5600X + RX 6700 XT (12GB VRAM, ROCm) + 32GB RAM**.

- Chat model runs fully on GPU (Q5_K_M 9B, 65K context)
- Embeddings and curator run on CPU in Docker to avoid VRAM contention
- 12GB VRAM fits Q6_K 9B with room for KV cache
- All models stored at `/mnt/WD/Models/`

---

## License

Personal project. Not currently accepting contributions.
