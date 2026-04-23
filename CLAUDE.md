# CLAUDE.md — AI Stack Project Context

## What This Project Is

**Project name: Accel** (potential future rename to "Evolution")

A local-first personal operating system for Intelligence Amplification — not a chatbot, but an organism with distinct layers that share memory and a consistent perspective. The long-term goal: agentic hands, proactive initiative, and sensory/physical extensions unified into one system that can act on behalf of the user across all domains. Also a portfolio/career-transition project.

### System layers:
- **Second brain** — memory and reasoning (all 6 layers active) ✓
- **Agentic hands** — tool execution, approval gate (active in bootstrap) ✓
- **Initiative layer** — task queue, deferred delivery, proactive orchestration (planned)
- **Sensory/motor extensions** — phone, Klipper, home automation, clipboard, screen context (planned)
- **Identity coherence** — consistent personality + cognitive profile across all domains (evolving)

## Hardware

**CPU:** Ryzen 5 5600X | **GPU:** RX6700XT (12GB VRAM, AMD — ROCm/HIP, not CUDA) | **RAM:** 32GB | **Storage:** ~3TB NVMe

12GB VRAM fits Q6_K 9B with room for KV cache. CPU offloading viable for embeddings/curator. Always suggest ROCm-compatible approaches.

## Running Stack

| Service | Port | Notes |
|---|---|---|
| nginx (UI) | 80 | Serves `index.html`, `blob_ui.js`, `blob_ui.css` |
| bootstrap | 8100 | Active pipeline — FastAPI + custom agentic loop |
| n8n | 5678 | Superseded — running but UI no longer calls it |
| Qdrant | 6333/6334 | Vector DB |
| llama.cpp chat | 8080 | GPU (ngl=99), 65K ctx, started via `start_chat_dimoe.sh` |
| llama.cpp embeddings | 8081 | Docker (llama-cpu-local), bge-m3-q8_0, 8192 ctx |
| llama.cpp curator | 8082 | Docker (llama-cpu-local), Qwen INSTRUCT, 8192 ctx |
| code-splitter | 9200 | FastAPI — tree-sitter splitting, log/text/chat, image preprocess, session/profile/ingest |
| Forgejo | 3000 | Self-hosted git |
| MinIO | 9000/9001 | Object storage |
| Prometheus | 9090 | Scrapes node-exporter (9100), Qdrant, rocm-exporter (9101 host) |
| Grafana | 3001 | Metrics — admin/admin |
| Portainer | 9003 | Docker management |

`rocm_exporter.py` runs as systemd service `rocm-exporter` on the host.

**Start chat model:** `start_chat_dimoe.sh` (default), `start_chat_gemma4.sh`, `start_chat_step3.sh`  
**Run bootstrap:** `cd /home/rezxt/bootstrap && .venv/bin/python main.py`

## Models

All models at `/mnt/WD/Models/`.

**Active:**
- **Chat:** `Qwen3.5-9B-Deckard-Claude-DIMOE-Uncensored-Heretic-Thinking.Q5_K_M.gguf` — DIMOE fine-tune, vision via mmproj, 65K ctx, THINKING variant. Use smoothing_factor=1.5 (Quadratic Sampling).
- **Vision projector:** `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED.mmproj-Q8_0.gguf` — compatible across same-architecture fine-tunes
- **Embeddings:** `bge-m3-q8_0.gguf` — CPU, 1024-dim (locked in; swapping requires re-embedding all collections)
- **Curator:** `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED.Q6_K.gguf` — CPU, INSTRUCT variant, thinking suppressed

**Also on disk:** DeepSeek-R1-Distill-Qwen-14B-Q5_K_M, GLM-4.1V-9B-Thinking-Q6_K, GLM-4.6V-Flash-Q8_0, Qwen3.5-9B-Q6_K (clean base), Qwen3.5-9B INSTRUCT Q6_K, Qwen3-14B-abliterated Q5_K_M, gemma-4-E4B Q8_0, Step3-VL-10B Q6_K, gemma-3-12b-vl-polaris Q6_K, Phi-4-mini variants, XTTS-v2 (TTS, not integrated)

## Bootstrap — Active Pipeline

`/home/rezxt/bootstrap/` — FastAPI + custom agentic loop, replacing n8n. No smolagents — custom loop is lighter and easier to control.

**Structure:**
```
bootstrap/
├── api/            # /chat (SSE), /approve, /settings/tools
├── agents/         # chat_agent.py, preprocessed_agent.py
├── tools/          # 19 tools
├── memory/         # Qdrant clients: facts, episodes, sessions, sources, profile, extraction
├── curator/        # preflight.py — personality + thinking depth
├── config.py
└── main.py         # uvicorn, port 8100
```

**27 tools:** `read_file`, `write_file`, `edit_file`, `delete_file`, `get_file_info`, `move_file`, `bash`, `search_files`, `list_dir`, `search_web`, `fetch_url`, `screenshot_url`, `calculate`, `calendar_today/get/add/delete`, `convert_units`, `convert_currency`, `search_knowledge_base`, `list_knowledge_base`, `search_notes`, `list_notes`, `ingest_note`, `ingest_file`, `search_audiobooks`, `add_torrent`

**Irreversible (require approval):** `bash`, `write_file`, `edit_file`, `delete_file`, `move_file`, `ingest_file`, `ingest_note`, `add_torrent`, `calendar_add_event`, `calendar_delete_event`

**Tool approval flow:** agentic loop yields `approval_request` SSE event → UI shows inline approve/deny. Each tool has `irreversible` flag; policy overridable per-tool in settings UI.

## Memory Architecture

**Qdrant collections (all active):** `facts`, `episodes`, `sessions`, `sources`, `procedures` — plus `insights` and `memory_changelog` planned (Memory Consolidation).

**Layers:**
- **L0** Working memory → `sessions` (full history, persists across restarts)
- **L1** Episodic memory → `episodes` (curator-compressed; threshold 50 turns, keep 20)
- **L2** Semantic memory → `facts` (extracted facts, content-hash dedup)
- **L3** Knowledge base → `sources` (documents, Obsidian vault)
- **L4** Procedural memory → `procedures` (interaction patterns; Procedure Extractor runs post-response)
- **L5** User profile → `user_profile.json` (always injected; `context_state`: work/study/free)

**Retrieval:** embed query → search at threshold → rerank `0.7×semantic + 0.3×recency` (decay 1/(1+days×0.05)) → top N. Facts threshold 0.55, sources 0.65.

**Personalities:** Teacher, Coder, Philosopher, Casual, Critic, Mentor — pre-flight curator decides based on context_state + last 2-3 turns.

**Thinking:** `enable_thinking` driven by pre-flight depth. `thinkingDepth=none` → false only (no hard suppression — causes empty output). `reasoning_content` captured; "Thinking Process:" blocks stripped in extract.

**Obsidian vault:** `notes/` symlink → `/mnt/WD/The Ideas/`. POST `/ingest/vault` to re-index. Chunking uses heading + paragraph-aware splitter.

**Ingest:** POST `/ingest` on code-splitter (PDF/EPUB/TXT/MD/RST) → MinIO + Qdrant `sources`. Semantic chunking: GPU model inserts `<<<CHUNK>>>` markers; falls back to heuristic. Per-file timing logged to `~/ai-stack/logs/ingest.log`.

## Architecture — What's Still Planned

Design authority: `notes/` (Obsidian vault). Read when context is needed — they represent intent, code may lag behind.

- **Skills system** — evolve L4 from passive recording into named executable patterns promoted through validated use
- **Autonomous task execution** — goal → result; task state in Qdrant or SQLite; frictionless goal capture is the hard part
- **Identity coherence** — cognitive profile: thinking style, decision values, overconfidence areas
- **Memory consolidation** — background dedup + synthesis → `insights` collection; user approves before changes apply; design in `notes/Memory_Consolidation.md`
- **Sandboxed code execution** — `bash` is currently unsandboxed; sandbox boundary TBD
- **Note writing to Obsidian vault** — tool to write back to `notes/`

## How to Work With This Project

**Work style varies by day.** Architecture/brainstorm vs. direct implementation — read the energy. Don't push for implementation when the conversation is design-focused.

**The notes are the design authority.** If code conflicts with notes, notes represent intent. Ask before deviating.

**Bootstrap is the primary pipeline.** All new logic goes into `bootstrap/`. Don't add to n8n.json.

**Git is safe.** Local git + Forgejo. Always prefer targeted edits over large rewrites.

**Browser conversations may not be in context.** User brainstorms in Claude.ai, important outcomes go into Obsidian notes. When told to read the notes, do it.

**User speaks English and Polish.** Match the language they write in.

## llama.cpp Build

- Source: `/home/rezxt/ai-stack/llama.cpp/`, ROCm build for gfx1030
- Host ROCm: 6.3.1 — prebuilt tarballs for ROCm 7.x will NOT work; must build from source
- Current binary: b8780
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
