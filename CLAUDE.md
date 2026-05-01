# CLAUDE.md — AI Stack Project Context

## What This Project Is

**Project name: Accel** (potential future rename to "Evolution")

A local-first personal operating system for Intelligence Amplification — not a chatbot, but an organism with distinct layers that share memory and a consistent perspective. The long-term goal: agentic hands, proactive initiative, and sensory/physical extensions unified into one system that can act on behalf of the user across all domains. Also a portfolio/career-transition project.

### System layers:
- **Second brain** — memory and reasoning (all 6 layers active) ✓
- **Agentic hands** — tool execution, approval gate (active in bootstrap) ✓
- **Voice interface** — wake word → STT → chat → TTS pipeline (active, "Hey Jarvis") ✓
- **Initiative layer** — task queue, deferred delivery, proactive orchestration (planned)
- **Sensory/motor extensions** — phone, Klipper, home automation, clipboard, screen context (planned)
- **Identity coherence** — consistent personality + cognitive profile across all domains (evolving)

## Hardware

**CPU:** Ryzen 5 5600X | **GPU:** RX6700XT (12GB VRAM, AMD — ROCm/HIP, not CUDA) | **RAM:** 32GB | **Storage:** ~3TB NVMe

12GB VRAM fits Q6_K 9B + turbo4 KV cache + mmproj + 0.8B curator simultaneously (~10.5 GB). Always suggest ROCm-compatible approaches.

## Running Stack

| Service | Port | Notes |
|---|---|---|
| nginx (UI) | 80 | Serves Electron/React build via bootstrap compose |
| bootstrap | 8100 | Active pipeline — FastAPI + custom agentic loop |
| n8n | 5678 | Superseded — running but UI no longer calls it |
| Qdrant | 6333/6334 | Vector DB |
| llama.cpp chat | 8080 | GPU (ngl=99), 65K ctx, turbo4 KV, mmproj vision — `Qwen3.5-9B-Q6_K.gguf` via llama-cpp-turboquant |
| llama.cpp embeddings | 8081 | Docker (llama-cpu-local), bge-m3-q8_0, 8192 ctx |
| llama.cpp curator | 8082 | Native GPU (ngl=99), `Qwen3.5-0.8B-Q8_0.gguf`, 8192 ctx, ~163 t/s |
| llama.cpp qwen-mini | 8083 | Docker (llama-cpu-local), Qwen3.5-0.8B-Q8_0, 32K ctx (backup/unused) |
| code-splitter | 9200 | Docker (ai-stack compose) — tree-sitter splitting, log/text/chat, image preprocess |
| SearXNG | 8888 | Docker — web search backend |
| Playwright | 9300 | Docker — headless browser / screenshot |
| MCP Server | 9400 | Docker — tool MCP bridge |
| Forgejo | 3000 | Self-hosted git |
| MinIO | 9000/9001 | Object storage |
| Prometheus | 9090 | Scrapes node-exporter (9100), Qdrant, rocm-exporter (9101 host) |
| Grafana | 3001 | Metrics — admin/admin |
| Navidrome | 4533 | Local music server (Subsonic API) |
| Portainer | 9003 | Docker management |

`rocm_exporter.py` runs as systemd service `rocm-exporter` on the host.

**Start chat model (native, TurboQuant+):**
```
/home/rezxt/ai-stack/llama-cpp-turboquant/build/bin/llama-server \
  -m /mnt/WD/Models/Qwen3.5-9B-Q6_K.gguf \
  --mmproj /mnt/WD/Models/Qwen3.5-9B.mmproj-Q8_0.gguf \
  -c 65536 --host 0.0.0.0 --port 8080 \
  -ngl 99 --jinja --ubatch-size 256 \
  -ctk turbo4 -ctv turbo4
```
**Start curator (native GPU):** `llama-server -m /mnt/WD/Models/Qwen3.5-0.8B-Q8_0.gguf -c 8192 --host 0.0.0.0 --port 8082 -ngl 99 --jinja`  
Or use the Electron service dashboard → Chat Model → Start.  
**Run bootstrap:** `cd /home/rezxt/bootstrap && .venv/bin/python main.py`

## Models

All models at `/mnt/WD/Models/`.

**Active:**
- **Chat:** `Qwen3.5-9B-Q6_K.gguf` — clean base, 65K ctx, GPU (ngl=99), `--jinja`, turbo4 KV cache (~544 MB vs ~2 GB f16), mmproj vision, ubatch-size 256. Binary: `llama-cpp-turboquant`. ~40 t/s.
- **Embeddings:** `bge-m3-q8_0.gguf` — CPU, 1024-dim (locked in; swapping requires re-embedding all collections)
- **Curator:** `Qwen3.5-0.8B-Q8_0.gguf` — GPU (ngl=99), port 8082, ~163 t/s. Uses raw `/completion` endpoint with `<think>\n</think>\n` injection (thinking_budget_tokens=0 broken in this model). Handles preflight routing + episode compression.
- **Qwen Mini:** `Qwen3.5-0.8B-Q8_0.gguf` — CPU Docker, port 8083 (backup, unused while curator runs natively)

**Previously used / available:**
- `Qwen3.5-9B-Deckard-Claude-DIMOE-Uncensored-Heretic-Thinking.Q5_K_M.gguf` — DIMOE fine-tune with mmproj vision, THINKING variant
- Vision projector: `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED.mmproj-Q8_0.gguf`

**Voice models (active):**
- **STT:** faster-whisper `base` — CPU, int8, bilingual (Polish + English auto-detect), 16kHz
- **TTS:** Piper `en_US-lessac-medium.onnx` — offline, plays via sounddevice
- **Wake word:** openWakeWord `hey_jarvis_v0.1.onnx` — 80ms chunks, 0.5 threshold, built-in Silero VAD

**Also on disk:** DeepSeek-R1-Distill-Qwen-14B-Q5_K_M, GLM-4.1V-9B-Thinking-Q6_K, GLM-4.6V-Flash-Q8_0, Qwen3.5-9B-Q6_K (clean base), Qwen3.5-9B INSTRUCT Q6_K, Qwen3-14B-abliterated Q5_K_M, gemma-4-E4B Q8_0, Step3-VL-10B Q6_K, gemma-3-12b-vl-polaris Q6_K, Phi-4-mini variants, XTTS-v2 (TTS, superseded by Piper)

## Bootstrap — Active Pipeline

`/home/rezxt/bootstrap/` — FastAPI + custom agentic loop, replacing n8n. No smolagents — custom loop is lighter and easier to control.

**Structure:**
```
bootstrap/
├── api/            # /chat (SSE), /approve, /settings/tools, /voice, /embeddings
├── agents/         # chat_agent.py, preprocessed_agent.py
├── tools/          # ~37 tools
├── memory/         # Qdrant clients: facts, episodes, sessions, sources, notes, profile, extraction
├── curator/        # preflight.py — personality + thinking depth
├── voice/          # pipeline.py, stt.py, tts.py, listener.py, filter.py, models/
├── config.py
└── main.py         # uvicorn, port 8100
```

**~50 tools:**
- *File:* `read_file`, `write_file`, `edit_file`, `delete_file`, `get_file_info`, `move_file`, `download_file`
- *System:* `bash`, `search_files`, `list_dir`
- *Web:* `search_web`, `fetch_url`, `screenshot_url`
- *Compute:* `calculate`, `convert_units`, `convert_currency`
- *Calendar:* `calendar_today`, `calendar_get_events`, `calendar_add_event`, `calendar_delete_event`
- *Memory/KB:* `search_knowledge_base`, `list_knowledge_base`, `search_notes`, `list_notes`, `ingest_note`, `ingest_file`, `delete_source`, `delete_note`, `search_facts`, `search_procedures`, `search_episodes`, `save_memory`, `update_memory`, `delete_memory`
- *Music:* `search_music`, `download_music`, `navidrome_search`, `navidrome_get_playlists`, `navidrome_get_playlist`, `navidrome_create_playlist`, `navidrome_update_playlist`, `navidrome_delete_playlist`, `player_control`, `player_now_playing`, `player_load`, `soundcloud_get_playlists`, `soundcloud_get_playlist`
- *Media:* `search_audiobooks`, `add_torrent`

**Irreversible (require approval):** `bash`, `write_file`, `edit_file`, `delete_file`, `move_file`, `ingest_file`, `ingest_note`, `add_torrent`, `download_music`, `navidrome_create_playlist`, `navidrome_update_playlist`, `navidrome_delete_playlist`, `calendar_add_event`, `calendar_delete_event`, `delete_source`, `delete_note`, `save_memory`, `update_memory`, `delete_memory`

**Tool approval flow:** agentic loop yields `approval_request` SSE event → UI shows inline approve/deny. Each tool has `irreversible` flag; policy overridable per-tool in settings UI.

## Memory Architecture

**Qdrant collections (all active):** `facts`, `episodes`, `sessions`, `sources`, `notes`, `procedures` — plus `insights` and `memory_changelog` planned (Memory Consolidation).

**Layers:**
- **L0** Working memory → `sessions` (full history, persists across restarts)
- **L1** Episodic memory → `episodes` (curator-compressed; threshold 50 turns, keep 20)
- **L2** Semantic memory → `facts` (extracted facts, content-hash dedup)
- **L3** Knowledge base → `sources` (documents) + `notes` (Obsidian vault, separate collection)
- **L4** Procedural memory → `procedures` (interaction patterns; Procedure Extractor runs post-response)
- **L5** User profile → `user_profile.json` (always injected; `context_state`: work/study/free)

**Retrieval:** embed query → search at threshold → rerank `0.7×semantic + 0.3×recency` (decay 1/(1+days×0.05)) → top N. Facts threshold 0.55, sources 0.65.

**Personalities:** Teacher, Coder, Philosopher, Casual, Critic, Mentor — pre-flight curator decides based on context_state + last 2-3 turns.

**Thinking:** `enable_thinking` driven by pre-flight depth. `thinkingDepth=none` → false only (no hard suppression — causes empty output). `reasoning_content` captured; "Thinking Process:" blocks stripped in extract.

**Obsidian vault:** `notes/` symlink → `/mnt/WD/The Ideas/`. POST `/ingest/vault` to re-index. Chunking uses heading + paragraph-aware splitter.

**Ingest:** POST `/ingest` on code-splitter (PDF/EPUB/TXT/MD/RST) → MinIO + Qdrant `sources`. Semantic chunking: GPU model inserts `<<<CHUNK>>>` markers; falls back to heuristic. Per-file timing logged to `~/ai-stack/logs/ingest.log`.

## Canvas (Architecture Session)

tldraw v2.4.0 embedded in a split-pane view (50/50 with chat). Only visible on the "architecture" session.

- **JS:** loaded via esm.sh importmap (`tldraw@2.4.0`, React 18.3.1)
- **CSS:** pinned to `unpkg.com/tldraw@2.4.0/tldraw.css` — must match JS version or toolbar breaks
- **State:** persisted to `/canvas/state` (JSON snapshot, debounced 1s saves)
- **Backend:** `api/canvas.py` (GET/POST state), `tools/canvas_tools.py` (canvas_draw, canvas_clear, canvas_get_state)
- **Commands:** SSE `canvas_command` events → `window._canvasCommand()` (create_shapes, clear)
- **Viewport bounds fix:** `syncBounds()` in the module script gets the `Box` class from `editor.getViewportScreenBounds().constructor` and calls `editor.updateViewportScreenBounds()` with a fresh Box from the container's `getBoundingClientRect()`. This is needed after `loadSnapshot()` (which resets internal state) and on panel show/hide. tldraw's internal resize handler caches the last rect and skips updates when the container size hasn't changed, so dispatching `window.resize` alone doesn't work — the direct `updateViewportScreenBounds()` call bypasses the cache.
- **Container:** `#canvasRoot` uses `position: absolute; inset: 0` inside `.canvas-panel` (`position: relative; width: 50%`)

## Music Pipeline (Music Session)

Navidrome (Subsonic API) + Feishin desktop player + in-browser player, with SoundCloud/YouTube search+download.

- **Navidrome:** local music server at port 4533, accessed via Subsonic API (`/rest/` endpoints). Creds from env: `NAVIDROME_URL`, `NAVIDROME_USER`, `NAVIDROME_PASSWORD`
- **Feishin:** desktop player controlled via MPRIS/playerctl (`player_control`, `player_now_playing`)
- **In-browser player:** `player_load` sends song IDs → UI fetches streams from `/navidrome/rest/stream` (proxied via nginx to avoid CORS)
- **Now Playing widget:** bottom bar in music session, polls `/music/now_playing` every 3s, shows art/title/artist/progress/controls
- **SoundCloud:** `soundcloud_get_playlists`, `soundcloud_get_playlist` — reads via cookie auth (`cookies/soundcloud_cookies.json`)
- **YouTube/SoundCloud search+download:** `search_music` (yt-dlp search), `download_music` (downloads opus to `/mnt/WD/Music`, requires approval)
- **API:** `api/music.py` — `/music/now_playing` (GET), `/music/control` (POST) — wraps playerctl
- **Tools:** `tools/navidrome_tools.py` — 13 tools for search, playlists, playback, SoundCloud

## Architecture — What's Still Planned

Design authority: `notes/` (Obsidian vault). Read when context is needed — they represent intent, code may lag behind.

- **Skills system** — evolve L4 from passive recording into named executable patterns promoted through validated use
- **Autonomous task execution** — goal → result; task state in Qdrant or SQLite; frictionless goal capture is the hard part
- **Identity coherence** — cognitive profile: thinking style, decision values, overconfidence areas
- **Memory consolidation** — background dedup + synthesis → `insights` collection; user approves before changes apply; design in `notes/Memory_Consolidation.md`
- **Sandboxed code execution** — `bash` is currently unsandboxed; sandbox boundary TBD
- **Note writing to Obsidian vault** — tool to write back to `notes/`
- **Voice improvements** — Polish STT (fine-tuned Whisper), Polish TTS voice, wake-word tuning

## How to Work With This Project

**Work style varies by day.** Architecture/brainstorm vs. direct implementation — read the energy. Don't push for implementation when the conversation is design-focused.

**The notes are the design authority.** If code conflicts with notes, notes represent intent. Ask before deviating.

**Bootstrap is the primary pipeline.** All new logic goes into `bootstrap/`. Don't add to n8n.json.

**Git is safe.** Local git + Forgejo. Always prefer targeted edits over large rewrites.

**Browser conversations may not be in context.** User brainstorms in Claude.ai, important outcomes go into Obsidian notes. When told to read the notes, do it.

**User speaks English and Polish.** Match the language they write in.

## Voice Pipeline

`voice/` — wake word → STT → chat → TTS, runs as background thread.

- **Wake word:** "Hey Jarvis" via openWakeWord (80ms chunks, Silero VAD built-in)
- **STT:** faster-whisper `base`, CPU int8, auto language detection (Polish + English)
- **TTS:** Piper `en_US-lessac-medium.onnx` → WAV → sounddevice playback
- **API:** `POST /voice/toggle?enabled=true/false`, `GET /voice/status`
- **Voice mode flag** (`voice_mode: true`) injects system addendum: concise spoken sentences, no markdown
- Tool status spoken mid-turn ("Let me search for that...", etc.) via `voice/filter.py`
- Response filtered before TTS: strips `<think>` blocks, markdown, code blocks, URLs
- Piper binary: `voice/models/piper/piper/piper`; model: `voice/models/piper/en_US-lessac-medium.onnx`

## Electron Desktop App

`/home/rezxt/bootstrap/ui/` — React + Vite + Electron 41, built as AppImage.

- **Production build:** `npm run build:electron` → `release/Accel-0.0.0.AppImage`
- **Launch:** `ELECTRON_DISABLE_SANDBOX=1 ./release/Accel-0.0.0.AppImage --no-sandbox`
- **Local proxy server:** main process spins up a Node HTTP proxy on a random loopback port in production (mirrors Vite dev proxy). All `/chat`, `/notes`, `/navidrome`, etc. routes forward to the right backends. This is why fetch works from `file://` without CORS issues.
- **Service dashboard:** manages all stack services (start/stop/restart + health, ports, logs). Process-type services (native llama-server) are NOT auto-detected on launch — only docker/systemd services are, to avoid false-positives when a container serves the same port.
- **Services config:** `~/.config/accel/services.json` — auto-created from defaults on first run. Delete to reset to current DEFAULT_SERVICES.
- **Key UX:** window focus → textarea auto-focuses. Approval blocks: `←`/`→` switch Allow/Deny, Enter confirms. Only the latest pending approval shown (previous ones replaced).
- **Logs:** each service row has a logs button → `docker compose logs --tail 300` or `journalctl`.

## llama.cpp Build

- Source: `/home/rezxt/ai-stack/llama.cpp/`, ROCm build for gfx1030
- Host ROCm: 6.3.1 — prebuilt tarballs for ROCm 7.x will NOT work; must build from source
- Current binary: b8780 (latest: b8994 as of 2026-05-01)
- Always use `--jinja` flag (embedded chat template)
- Embeddings/curator run in Docker to avoid VRAM usage even at `-ngl 0`
- Rebuild: `cmake --build build --config Release -j$(nproc)` then `sudo cp build/bin/llama-server /usr/local/bin/llama-server` (stop chat model first)

## n8n API (reference only)

- API key: `N8N_API_KEY` in `~/.claude/settings.json`; base URL: `N8N_BASE_URL` (`http://localhost:5678`)
- Workflow ID: `XycypIyUawQdZudx`
- Push payload: only `name`, `nodes`, `connections`, `settings: {executionOrder: "v1"}` — `active` is read-only

## Key Design Decisions

- Local-first, no cloud inference
- **Bootstrap (custom FastAPI + agentic loop) replaced n8n** — custom loop, no smolagents
- llama.cpp for all inference (ROCm GPU chat, CPU embeddings/curator)
- Qdrant for all vector storage; bge-m3 locked in at 1024-dim (re-embedding cost is high)
- Separate model roles: chat (GPU, high ctx), curator (CPU, small ctx), embeddings (CPU)
- Router classifies input before any processing — never embed blindly
- Memory layers are separate concepts from input modalities
- Reasoning/thinking visible and passed to the UI separately from the final answer
- SVG treated as code, not as image; images preprocessed to 1280px max before vision model
- **Reversibility is the autonomy criterion** — reversible = autonomous; irreversible = approval required
- **Identity coherence over capability** — consistent perspective across domains matters more than raw integrations
