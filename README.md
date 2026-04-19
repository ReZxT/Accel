# Accel

A local-first personal AI assistant built for Intelligence Amplification — not a chatbot, but a system with persistent memory, context-aware routing, and a consistent cognitive profile across sessions.

Rebuilt from an n8n pipeline to a Python-native stack using **smolagents + FastAPI**. All inference runs locally via llama.cpp on an AMD GPU (ROCm).

---

## Architecture

```
FastAPI (port 8100)
  └─ /chat (SSE)
       ├─ Router — classifies every input before processing
       ├─ direct_chat     → pre-flight → memory retrieval → chat model
       ├─ preprocessed_text → code-splitter → memory retrieval → chat model
       └─ multimodal      → image preprocess → memory retrieval → vision model
```

### Memory layers

| Layer | Store | Description |
|-------|-------|-------------|
| 0 — Working | Qdrant `sessions` | Full message history, persists across restarts |
| 1 — Episodic | Qdrant `episodes` | Curator-compressed summaries of older context |
| 2 — Semantic | Qdrant `facts` | Extracted facts about the user |
| 3 — Knowledge | Qdrant `sources` | Ingested documents, notes, Obsidian vault |
| 4 — Procedural | Qdrant `procedures` | How the user likes to work and learn |
| 5 — Profile | `user_profile.json` | Stable context always injected into every prompt |

Retrieval uses recency reranking: `0.7 × semantic + 0.3 × recency` with slow time decay.

---

## Routing

Every request is classified by `router/classifier.py` before any processing:

| Route family | Text type | Pipeline |
|---|---|---|
| `direct_chat` | chat | Pre-flight + retrieval + chat model |
| `preprocessed_text` | code | AST splitting → Coder personality |
| `preprocessed_text` | logs | Log-aware chunking → Coder personality |
| `preprocessed_text` | chat_dump | Speaker-turn splitting → no retrieval |
| `preprocessed_text` | document | Section splitting → progressive summarization if huge |
| `multimodal` | — | Image preprocessing + optional retrieval + vision model |

Classification is heuristic (regex patterns, file extensions, size thresholds) — no LLM call.

---

## Services

All inference and storage runs locally. Docker Compose handles supporting services; the bootstrap FastAPI server runs directly on the host.

| Service | Port | Role |
|---|---|---|
| Bootstrap API | 8100 | FastAPI chat endpoint |
| nginx | 80 | Serves web UI, proxies `/chat` |
| llama.cpp chat | 8080 | GPU inference (ROCm), 65K context |
| llama.cpp embeddings | 8081 | CPU, bge-m3 1024-dim |
| llama.cpp curator | 8082 | CPU, structured JSON extraction |
| code-splitter | 9200 | AST chunking, log splitting, image preprocessing |
| Qdrant | 6333 | Vector database |
| MinIO | 9000 | Image archive |

---

## Project structure

```
bootstrap/
├── api/
│   └── chat.py          # FastAPI endpoint, SSE event stream, route dispatch
├── agents/
│   ├── chat_agent.py    # Direct chat + multimodal: retrieval, session, streaming
│   └── preprocessed_agent.py  # Code/logs/document paths with code-splitter
├── router/
│   └── classifier.py    # Heuristic input classifier, RouteDecision dataclass
├── memory/
│   ├── facts.py         # Semantic memory search + recency reranking
│   ├── sources.py       # Knowledge base search
│   ├── episodes.py      # Context compression → Qdrant episodes
│   ├── extraction.py    # Post-response fact + procedure extraction
│   ├── profile.py       # User profile read/write
│   └── sessions.py      # Session load/save via code-splitter
├── curator/
│   └── preflight.py     # Personality + thinking depth selection before each turn
├── tools/
│   └── llm.py           # chat_complete, curator_complete, embed
├── config.py            # Single config object, all URLs from env vars
└── main.py              # FastAPI app entry point
```

---

## Setup

**Prerequisites:** llama.cpp with ROCm support, Qdrant, MinIO, code-splitter service running.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The web UI is served by nginx (Docker Compose). Start supporting services:

```bash
docker compose up -d
```

---

## Hardware

Designed for a Ryzen 5 5600X + RX 6700 XT (12GB VRAM, ROCm) + 32GB RAM. llama.cpp runs the chat model fully on GPU; embeddings and curator run on CPU in Docker to avoid VRAM contention.
