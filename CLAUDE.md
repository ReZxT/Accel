# CLAUDE.md — AI Stack Project Context

## What This Project Is

**Project name: Accel** (potential future rename to "Evolution" if/when the system reaches a major self-improvement breakthrough)

A local-first personal operating system for Intelligence Amplification — not a chatbot, but an organism with distinct layers that share memory and a consistent perspective. The second brain (memory + reasoning) is one subsystem; the long-term goal is integrating agentic hands, proactive initiative, and sensory/physical extensions into a unified system that can act on behalf of the user across all domains.

Also a portfolio/career-transition project. Everything runs on local hardware with no cloud dependencies.

### System layers (direction, not all built yet):
- **Second brain** — memory and reasoning (all 6 layers active) ✓
- **Agentic hands** — code execution, file editing, bash, patch proposal and approval (next major focus)
- **Initiative layer** — task queue, deferred delivery, proactive orchestration (planned)
- **Sensory/motor extensions** — phone, Klipper, home automation, clipboard, screen context (longer term)
- **Identity coherence** — consistent personality, values, and cognitive profile across all domains (evolving)

## Hardware

- **CPU:** Ryzen 5 5600X
- **GPU:** RX6700XT (12GB VRAM, AMD — ROCm/HIP, not CUDA)
- **RAM:** 32GB
- **Storage:** ~3TB NVMe

When suggesting model configs or performance tradeoffs, account for AMD GPU (ROCm). llama.cpp is compiled with ROCm/HIP support. 12GB VRAM fits a Q6_K 9B model with room for KV cache. CPU offloading via RAM is viable for embeddings/curator.

## Running Stack

All services run via Docker Compose. Multiple start scripts for the GPU chat model:
- `start_chat_dimoe.sh` — current default (DIMOE Q5_K_M)
- `start_chat_gemma4.sh` — Gemma 4 E4B Q8_0
- `start_chat_step3.sh` — Step3-VL-10B Q6_K
- `start_chat_test.sh` — ad-hoc testing

| Service | Port | Notes |
|---|---|---|
| nginx (UI) | 80 | Serves `index.html`, `blob_ui.js`, `blob_ui.css` |
| n8n | 5678 | Main pipeline orchestration |
| Qdrant | 6333/6334 | Vector DB |
| llama.cpp chat | 8080 | GPU (ngl=99), started via `start_chat.sh`, 65K ctx |
| llama.cpp embeddings | 8081 | Docker container (llama-cpu-local image), bge-m3-q8_0, 8192 ctx, batch size 2048 |
| llama.cpp curator | 8082 | Docker container (llama-cpu-local image), Qwen INSTRUCT model, 8192 ctx |
| code-splitter | 9200 | Python/FastAPI service — tree-sitter code splitting, log chunking, text splitting, chat dump splitting, image preprocessing |
| Forgejo | 3000 | Self-hosted git |
| MinIO | 9000/9001 | Object storage |
| node-exporter | 9100 | Host metrics (CPU, RAM, disk, network) |
| Prometheus | 9090 | Metrics collection — scrapes node-exporter, Qdrant, AMD GPU (rocm-exporter on 9101) |
| Grafana | 3001 | Metrics dashboard — admin/admin |
| Portainer | 9003 | Docker container management UI |

### AMD GPU metrics
`rocm_exporter.py` runs as a systemd service (`rocm-exporter`) on the host at port 9101. Prometheus scrapes it at `172.17.0.1:9101`.

## Models

All models stored at `/mnt/WD/Models/`.

- **Chat model (current):** `Qwen3.5-9B-Deckard-Claude-DIMOE-Uncensored-Heretic-Thinking.Q5_K_M.gguf` — DavidAU DIMOE fine-tune (Claude 4.6 Opus + DECKARD datasets), vision-capable via mmproj, 65K context. THINKING variant — chain-of-thought active. DavidAU recommends smoothing_factor=1.5 (Quadratic Sampling).
- **Vision projector:** `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED.mmproj-Q8_0.gguf` — compatible across same-architecture fine-tunes (both INSTRUCT and THINKING variants use the same projector)
- **Embeddings:** `bge-m3-q8_0.gguf` — CPU, dedicated endpoint
- **Curator:** `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED.Q6_K.gguf` — CPU, 8192 ctx (INSTRUCT variant — thinking suppressed, good for structured JSON extraction)

### Other models on disk:
- `Qwen3.5-9B-Q6_K.gguf` — clean base Qwen3.5 9B, no fine-tune (for baseline comparison testing)
- `Step3-VL-10B-Q6_K.gguf` — Step3 vision-language 10B, Q6_K, not yet tested
- `gemma-4-E4B.Q8_0.gguf` — Gemma 4 E4B, Q8_0, not yet tested
- `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED.Q6_K.gguf` — same base, INSTRUCT variant, thinking suppressed
- `DeepSeek-R1-Distill-Qwen-14B-Q5_K_M.gguf` — text-only, thinking works, 14B fits in 12GB VRAM with small context
- `GLM-4.1V-9B-Thinking-Q6_K.gguf` — vision + thinking simultaneously, 64K context
- `gemma-3-12b-it-vl-polaris-glm-4.7-flash-var-thinking-instruct-heretic-uncensored-q6_k.gguf` — vision, thinking suppressed (INSTRUCT template)
- `huihui-ai_Qwen3-14B-abliterated-Q5_K_M.gguf`
- `zai-org_GLM-4.6V-Flash-Q8_0.gguf` — GLM vision model
- `Phi-4-mini-reasoning-heretic-i1-IQ4_NL.gguf`, `Phi-4-mini-instruct-Q2_K_L.gguf`
- `dolphin-llama_8b.gguf`, `L3-3.3-8B-Stheno-Maid-Mahou-Heretic.i1-Q6_K.gguf`
- `gpt_20b.gguf` — unknown provenance, not yet tested
- `XTTS-v2/` — Coqui XTTS v2 TTS model (voice synthesis, not yet integrated)

## Pipeline — n8n Workflow (`n8n.json`)

The entire pipeline lives in n8n. Do not rewrite this in Python unless there is a specific reason.

**After editing n8n.json, always deploy to the running n8n instance:**
```python
import json, subprocess, os
with open(os.path.expanduser('~/.claude/settings.json')) as f:
    s = json.load(f)
with open('/home/rezxt/ai-stack/n8n.json') as f:
    wf = json.load(f)
payload = {'name': wf['name'], 'nodes': wf['nodes'], 'connections': wf['connections'], 'settings': {'executionOrder': 'v1'}}
with open('/tmp/wf_payload.json', 'w') as f:
    json.dump(payload, f)
subprocess.run(['curl', '-s', '-X', 'PUT', f"{s['env']['N8N_BASE_URL']}/api/v1/workflows/XycypIyUawQdZudx", '-H', f"X-N8N-API-KEY: {s['env']['N8N_API_KEY']}", '-H', 'Content-Type: application/json', '-d', '@/tmp/wf_payload.json'])
```

### Current flow:
```
Webhook POST /chat
  → Extract Webhook Payload
  → Load Stored Session (GET code-splitter:9200/session)
  → Resolve Chat History (use client history if present, else server session)
  → Route Request (classifier)
  → Switch (routeFamily)
    ├─ direct_chat:
    │    Compress Context (threshold 50 turns, keep 20, curator summarizes → episodes collection)
    │    → Embed query (8081) → Search facts (0.55 threshold, top 10 → rerank by recency → top 5)
    │    → Search sources (0.65 threshold)
    │    → Pre-flight Curator (curator:8082):
    │        reads session current_personality + context_state from profile + last 2-3 turns
    │        + retrieved procedures (top 8 → rerank by recency → top 4)
    │        → decides personality + thinking depth, updates session
    │    → Format Direct Chat Payload (personality + procedures + facts + sources + profile injected)
    │    → Call llama.cpp (8080, enable_thinking driven by thinking depth)
    │    → Extract output → Respond → Save Session (parallel)
    │    → Only Direct Chat IF:
    │        ├─ Memory JSON Chain (curator:8082) → facts → Save to facts collection
    │        └─ Procedure Extractor (curator:8082) → procedures → Save to procedures collection
    │
    ├─ preprocessed_text:
    │    Route Preprocessed Type (sub-switch on textType)
    │    ├─ code  → Code Splitter (9200/split/code) → Format
    │    │          → Embed (NL prefix extracted as query, not raw code) → Search facts → Format (Coder)
    │    │          → Call llama.cpp → Extract → Respond
    │    ├─ logs  → Code Splitter (9200/split/logs) → Format
    │    │          → Embed (NL prefix as query) → Search facts → Format (Coder)
    │    │          → Call llama.cpp → Extract → Respond
    │    ├─ chat_dump → Chat Dump Splitter (9200/split/chat_dump)
    │    │              → Format → Call llama.cpp → Extract → Respond
    │    └─ fallback (document/ocr/unknown) → Format (Teacher, progressive summarization if huge)
    │                                          → Call llama.cpp → Extract → Respond
    │
    └─ multimodal:
         Store Images to MinIO (images bucket, parallel) + Preprocess Images (resize 1280px)
         → Embed query (8081, skipped if chatInput is placeholder/empty)
         → Search facts → Format (session personality from Qdrant)
         → Call llama.cpp (8080, vision) → Extract → Respond → Save Session (parallel)
```

### Router (`Route Request` node):
Classifies every input before routing. Outputs:
- `routeFamily`: `direct_chat` | `multimodal` | `preprocessed_text`
- `pipeline`: granular pipeline name (e.g. `structured_analysis`, `log_analysis`, `chat_dump_analysis`)
- `textType`: `chat` | `code` | `logs` | `ocr` | `document` | `chat_dump` | `unknown`
- `sizeClass`: `none` | `short` | `medium` | `long` | `huge`
- `inputMode`: `text_only` | `image_present` | `file_present` | `multimodal`
- Various flags: `allowRawEmbedding`, `needsSummarization`, `needsLongProcessing`, `useRetrieval`, `retrievalAfterPreprocessing`

### Known state:
- Qdrant collections: `facts`, `episodes`, `sessions`, `sources`, `procedures` — all active; `insights` and `memory_changelog` planned (Memory Consolidation)
- Memory curator runs at `curator:8082` (CPU, dedicated Docker service)
- Pre-flight curator: runs before main model on direct_chat — decides personality + thinking depth; reads `context_state` from profile to bias personality selection
- Personalities: Teacher, Coder, Philosopher, Casual, Critic, Mentor — injected per path
- Layer 4 (procedural): Procedure Extractor runs post-response parallel to fact extraction
- Layer 5 (user profile): `user_profile.json` always-injected via code-splitter GET /profile; includes `context_state` field (work/study/free)
- Context State: stored in `user_profile.json` as `context_state`; UI toggle in settings (Work/Study/Free); injected into system prompt for work/study modes; biases curator personality selection
- Recency reranking: facts and procedures retrieved at 2× limit, reranked by `0.7×semantic + 0.3×recency` (decay: 1/(1+days×0.05)), top N returned
- `enable_thinking` flag driven by pre-flight thinking depth (none → false, else true)
- `thinkingDepth=none` sets `enable_thinking=false` only — hard suppression instruction was removed (caused empty model output). Thinking constrained to `<think>` tags in the extract node.
- Save Session does GET-then-PUT to preserve all session fields (current_personality etc.)
- Session recovery: UI disables send button during initial session load; n8n `Load Stored Session` + `Resolve Chat History` nodes inject stored history server-side when client sends empty chatHistory
- Obsidian vault (00–11 folders) indexed into sources; POST /ingest/vault to re-index
- Date/time injected into all system prompts (Europe/Warsaw timezone)
- Retrieval query: direct_chat uses raw chatInput (natural language, appropriate); preprocessed paths extract NL prefix before first code-like line, fall back to splitter symbol names
- Router flags enforced: `useRetrieval=false` skips embedding; multimodal skips embedding when chatInput is placeholder/empty; all search nodes fail gracefully (empty results, not throw)
- Progressive summarization: huge unclassified documents chunked (4K chars, max 8), each summarized by curator, combined, optionally compressed again if >5K chars
- `reasoning_content` captured; plain-text "Thinking Process:" blocks stripped in extract node
- Vision works end-to-end (base64 → image preprocessing → OpenAI vision format → mmproj model)
- SVG treated as code (routed through code branch, processed as XML text)
- Images archived to MinIO `images` bucket in parallel with preprocessing (multimodal path)
- Document ingestion: `/ingest` endpoint (PDF/EPUB/TXT/MD/RST) → MinIO + Qdrant `sources`
- **Semantic chunking for PDF/EPUB:** each page/chapter block sent to the main model (GPU, port 8080) via `CHAT_URL`; model inserts `<<<CHUNK>>>` markers at natural semantic boundaries; falls back to heuristic if model call fails
- **Vault note chunking:** uses `_split_text` (Markdown heading + paragraph-aware), not raw char cutting
- **Ingest logging:** per-file timing (extract / embed / qdrant / total) logged to `~/ai-stack/logs/ingest.log`; volume-mounted at `/app/logs` in container

### code-splitter service (`/home/rezxt/ai-stack/code_splitter/`):
Python/FastAPI service, built as Docker image `ai-stack-code-splitter`.
- `POST /split/code` — tree-sitter AST splitting for Python, JS, TS, Go, Rust, C/C++, Java, JSON, YAML, TOML, XML, CSS, HTML. Falls back to regex for unknown languages.
- `POST /split/logs` — log-aware chunking, keeps stack traces together, tags by level
- `POST /split/text` — section/paragraph splitting for prose documents
- `POST /split/chat_dump` — speaker-turn splitting for exported conversations
- `POST /preprocess/image` — resize to max 1280px, PNG stays lossless, JPEG/other → JPEG 85%
- `GET /session` — returns stored session messages from Qdrant `sessions` collection (filter by sessionId="default")
- `GET /profile` / `PUT /profile` — read/update `user_profile.json` (name, location, timezone, languages, background, hardware, notes, context_state)
- `POST /ingest` — ingest PDF/EPUB/TXT/MD/RST into MinIO + Qdrant `sources`
- `POST /ingest/vault` — walk numbered Obsidian vault folders, chunk+embed all .md files into sources
- `GET /health`

## Architecture — What's Planned

Full design lives in the Obsidian notes at `/mnt/WD/The Ideas/` (symlinked as `notes/`). Read them when context is needed. They are the source of truth for design intent.

### Memory layers:
- **Layer 0** — Working memory → Qdrant `sessions` (full message history, persists across restarts) ✓
- **Layer 1** — Episodic memory → Qdrant `episodes` (compressed summaries of older context) ✓
- **Layer 2** — Semantic memory → Qdrant `facts` (extracted facts about user, content-hash dedup) ✓
- **Layer 3** — Knowledge base → Qdrant `sources` (ingested documents/books/notes + Obsidian vault) ✓
- **Layer 4** — Procedural memory → Qdrant `procedures` (interaction patterns, how user learns) ✓
- **Layer 5** — User profile → `user_profile.json` (always-injected stable context block) ✓

### Completed phases:
- Phase 1 (Robust Input and Context Stabilization) ✓
- Phase 2 (Memory Separation) ✓
- Phase 3 (Temporal and Context Awareness) ✓
- Phase 4 (Model Role Separation) ✓
- Phase 5 partially — user profile done, workspace sandbox pending
- Phase 6 (Assistant Vault and Knowledge Base) ✓
- All memory layers 0–5 active

### Next focus areas (from Vision note):
- **Agentic coding loop** — the transformative jump. Primitives: `read_file`, `write_file`, `bash`, `search_files`, `list_dir`. Design questions: sandbox boundary (git-backed workspace root?), approval flow, irreversibility signaling, n8n integration.
- **Tool additions — high value near term:** SearXNG (self-hosted search), sandboxed code execution, note writing to Obsidian vault, document parsing improvements
- **Skills system** — evolve Layer 4 from passive observation recording into named executable patterns that can be deployed. Observations get promoted to skills through validated use.
- **Autonomous task execution** — hand it a goal, come back to a result. n8n as orchestration layer with task state in Qdrant or SQLite. Hardest part: frictionless goal capture (voice, clipboard, mention).
- **Identity coherence** — cognitive profile layer deeper than procedural memory: thinking style, decision values, where user is overconfident, what to challenge vs confirm.
- **Memory consolidation** — background GPU process (scheduled/manual) that semantically deduplicates facts, merges outdated entries, synthesizes cross-source insights → `insights` Qdrant collection. Produces a structured report; user approves before any changes apply. Change log tracked in `memory_changelog` collection. Separate n8n workflow, isolated from main chat pipeline. Design in `notes/Memory_Consolidation.md`.

## How to Work With This Project

**Work style varies by day.** Sometimes it's architecture and brainstorm discussion, sometimes it's direct implementation. Read the energy — don't push for implementation when the conversation is design-focused, and don't over-explain when there's a clear task to build.

**The notes are the design authority.** If something in code conflicts with the notes, assume the notes represent intent and the code is behind. Ask before deviating from the notes' design decisions.

**Bootstrap is the primary pipeline.** n8n is superseded. All new pipeline logic goes into `bootstrap/`. Don't add to n8n.json.

**Git is safe.** Local git + Forgejo. Safe to edit files. Always prefer targeted edits over large rewrites.

**Browser conversations may not be in context.** The user sometimes brainstorms in Claude.ai and moves important outcomes into the Obsidian notes. When told to read the notes, do it — they contain updated design decisions.

**User speaks English and Polish.** Match the language they write in.

## Bootstrap (accel-core — active, replacing n8n)

**Decision (2026-04-18):** Dropping n8n and qwen-code. The new stack lives at `/home/rezxt/bootstrap/` (was `accel-core/`). n8n stays running but is no longer the active pipeline. Bootstrap is now serving the web UI on port 8100.

**Stack:**
- **FastAPI** — replaces n8n webhook; same endpoint the web UI calls; SSE streaming
- **Python agentic loop** — `agents/chat_agent.py`; tool execution, approval gate, multi-turn
- **XML tool call parser** — handles 3 variants emitted by DIMOE/Claude-trained models
- **No smolagents** — the agentic loop is custom, lighter and easier to control

**Project structure:**
```
bootstrap/
├── api/            # FastAPI endpoints: /chat (SSE), /approve, /settings/tools
├── agents/         # chat_agent.py (agentic loop), preprocessed_agent.py
├── tools/          # 19 tools — see tool list below
├── memory/         # Qdrant clients: facts, episodes, sessions, sources, profile, extraction
├── curator/        # preflight.py — personality + thinking depth decisions
├── config.py
└── main.py         # uvicorn server on port 8100
```

**Tool list (19 tools):**
- `read_file`, `write_file`, `edit_file` — file operations
- `delete_file` — with safety checks (refuses .git, .env, .ssh, workspace root, directories)
- `get_file_info` — permissions, owner, size, timestamps
- `move_file` — rename/move with overwrite guard
- `bash` — shell execution (irreversible, requires approval by default)
- `search_files` — filename glob or content regex via ripgrep
- `list_dir` — directory listing
- `search_web` — SearXNG aggregated search
- `fetch_url` — fetch URL as readable text
- `screenshot_url` — Playwright screenshot with HEAD probe URL validation
- `calculate` — safe AST math evaluator (all `math` module functions)
- `calendar_today`, `calendar_get_events`, `calendar_add_event`, `calendar_delete_event` — SQLite calendar at `data/calendar.db`, Polish holidays via `holidays` library
- `convert_units` — pint-based unit conversion
- `convert_currency` — live rates via open.er-api.com

**Tool approval:** each tool has an `irreversible` flag; default policy is `require` for irreversible tools, `auto` for read-only. User can override per-tool in settings UI. Approval gate in agentic loop yields `approval_request` SSE event; UI shows inline approve/deny buttons.

**Irreversible tools (require approval by default):** `bash`, `write_file`, `edit_file`, `delete_file`, `move_file`, `calendar_add_event`, `calendar_delete_event`

**What carries over unchanged:** all Docker services (llama.cpp, Qdrant, embeddings, curator, code-splitter, MinIO, MCP, searxng, playwright), web UI (nginx), Qdrant collections + memory architecture.

**Running:** `cd /home/rezxt/bootstrap && .venv/bin/python main.py` (port 8100, reload mode)

**n8n (superseded):** `n8n.json` and the n8n workflow remain in the repo as reference. The n8n container still runs but the UI no longer calls it.

## Qwen Code (accel CLI — superseded)

`qwen-code/` (v0.14.4) fork at `/home/rezxt/ai-stack/qwen-code/qwen-code-0.14.4/`. Being replaced by accel-core. Keep as reference during migration.

**Modifications made to source:**
- `storage.ts`: `QWEN_CONFIG_HOME` env var override
- `memoryTool.ts` + `extensionManager.ts`: uses `ACCEL.md` instead of `CLAUDE.md`
- WebFetchTool fully removed (used geminiClient, incompatible with local model)
- XML tool call parser added to `converter.ts` — handles 3 variants of XML tool syntax emitted by DIMOE/Claude-trained models
- `toolCallFormat: 'auto' | 'openai' | 'xml'` added to ContentGeneratorConfig

Launcher: `~/.local/bin/accel` with `QWEN_CONFIG_HOME=~/.accel`, `QWEN_CODE_MAX_OUTPUT_TOKENS=32768`

## llama.cpp Build

- Source at `/home/rezxt/ai-stack/llama.cpp/`, built with ROCm for gfx1030 (RX6700XT)
- Host ROCm version: 6.3.1 — prebuilt tarballs targeting ROCm 7.2 will NOT work, must build from source
- Current host binary: b8780 — updated for Gemma 4 architecture support
- Always use `--jinja` flag so llama.cpp uses the model's embedded chat template
- Embeddings and curator run in Docker (`llama-cpu-local` image) to avoid VRAM usage even with `-ngl 0`
- Docker image requires `LD_LIBRARY_PATH=/opt/llama` and `libgomp1` installed — both handled in current Dockerfile
- To rebuild after source update: `cmake --build build --config Release -j$(nproc)` then `sudo cp build/bin/llama-server /usr/local/bin/llama-server` (stop chat model first — binary is busy while running)

## n8n API Access

- API key stored in `~/.claude/settings.json` as `N8N_API_KEY` env var
- Base URL: `http://localhost:5678` as `N8N_BASE_URL`
- Use `curl -H "X-N8N-API-KEY: $N8N_API_KEY"` to interact with workflows directly
- Workflow ID: `XycypIyUawQdZudx`
- When pushing updates via API, payload must contain only `name`, `nodes`, `connections`, `settings: { executionOrder: "v1" }` — `active` and other fields are read-only

## Key Design Decisions (do not contradict without discussion)

- Local-first, no cloud inference
- **n8n is being replaced** by smolagents + FastAPI (accel-core). n8n stays running during migration only.
- smolagents for agent orchestration; FastAPI for HTTP/SSE API layer; Python throughout
- llama.cpp for all inference (ROCm build for GPU, CPU for embeddings/curator)
- Qdrant for all vector storage
- Separate model roles: chat (GPU, high ctx), curator (CPU, small ctx), embeddings (CPU)
- **bge-m3 is locked in as the embedding model** — all Qdrant collections use its 1024-dim vector space. Swapping requires re-embedding every stored point across all collections (facts, sources, procedures, episodes). Only worth doing for a major quality leap, not a casual upgrade.
- Router classifies input before any processing — never embed blindly
- Memory layers are separate concepts from input modalities
- Reasoning/thinking is visible and passed to the UI separately from the final answer
- Socratic teaching style baked into the system prompt
- SVG treated as code, not as image
- Image preprocessing (resize to 1280px max) happens before sending to vision model
- **Reversibility is the autonomy criterion** — not confidence level. Reversible actions can be autonomous; irreversible actions always need the user in the loop. Apply this to agentic features.
- **Identity coherence over capability** — as the system grows more integrations, what matters is consistent perspective across domains, not just shared memory. Personality + cognitive profile together.
