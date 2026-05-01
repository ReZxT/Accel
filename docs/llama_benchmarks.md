# llama-server Benchmark Results

Hardware: Ryzen 5 5600X | RX6700XT 12GB | 32GB RAM | ROCm 6.3.1

Prompt: "Write a detailed 500-word explanation of how transformers work in machine learning."
Max tokens: 500 | Context: 65536 | ngl: 99

## Speed (65K context)

| Model | Quant | KV cache | Binary | t/s | TTFT | VRAM |
|---|---|---|---|---|---|---|
| Qwen3.5-9B-Deckard-DIMOE-Uncensored-Heretic-Thinking | Q5_K_M | f16 (default) | Docker (llama-chat-gpu) | 42.9 | 0.10s | 11.1 GB |
| Qwen3.5-9B-Q6_K (clean base) | Q6_K | f16 (default) | Docker (llama-chat-gpu) | 40.0 | 0.10s | 11.7 GB |
| Qwen3.5-9B-Q6_K (clean base) | Q6_K | f16 (default) | Native (llama-server b8780) | 40.0 | 0.10s | 9.67 GB |
| Qwen3.5-9B-Q6_K (clean base) | Q6_K | turbo4 (TurboQuant+) | Native (llama-cpp-turboquant) | 38.3 | 0.11s | 9.55 GB |

## KV Cache Location (Qwen3.5-9B-Q6_K, 65K ctx, ngl=99)

| KV location | t/s | TTFT | VRAM | Notes |
|---|---|---|---|---|
| GPU (f16, default) | 40.0 | 0.10s | 9.67 GB | baseline |
| CPU RAM (-nkvo) | 24.6 | 0.14s | 7.39 GB | −38% speed, −2.3 GB VRAM; bottleneck: PCIe bandwidth |
| GPU (turbo4, TurboQuant+) | 38.3 | 0.11s | 9.55 GB | −4% speed, 4× KV compression — better tradeoff than -nkvo |

**Verdict:** `-nkvo` not worth it for decode speed. But see prefill table below — CPU KV enables 256K context on 12GB VRAM.

## Prefill Speed: GPU KV vs CPU KV (-nkvo, 256K ctx)

| Context (tokens) | CPU KV prefill t/s | Prefill time | Notes |
|---|---|---|---|
| ~3.6K | 679.7 | 5.3s | |
| ~14K | 698.1 | 16.0s | peak |
| ~28K | 611.4 | 24.1s | |
| ~57K | 503.2 | 57.6s | |
| ~114K | 369.1 | 155.5s | |
| ~171K | 265.6 | 216.1s | |
| ~228K | 194.7 | 294.8s | ~5 min cold load |

GPU baseline (f16, 65K max): ~700-800 t/s prefill, max 128K before VRAM OOM.

VRAM with 256K ctx + CPU KV: **8.69 GB** (vs 9.67 GB for 65K GPU KV). Model fits — all context is in RAM (8 GB KV allocation).

**Use case:** If your session history is large but decode throughput matters less than context depth, `-nkvo` at 256K is viable. Cold session swap at 228K takes ~5 min — not interactive but usable for background/batch tasks.

## Max Context (Qwen3.5-9B-Q6_K, ngl=99)

| KV cache | 65K | 128K | 192K | 256K | 384K | 448K | 512K |
|---|---|---|---|---|---|---|---|
| f16 (baseline) | ✓ 9.67 GB | ✓ 11.66 GB | ✗ OOM | ✗ OOM | ✗ | ✗ | ✗ |
| turbo4 (TurboQuant+) | ✓ 9.55 GB | ✓ 9.84 GB | ✓ 10.48 GB | ✓ 11.20 GB | ✓ 11.96 GB | ✓ 11.97 GB | ✗ OOM |

**Safe limit:** 256K (model's native training context). turbo4 hits this comfortably at 11.20 GB.
**f16 safe limit:** 128K (192K OOMs). Beyond 128K is unavailable without TurboQuant.

## Quality: PPL (Shakespeare corpus, 8 chunks, ctx=512)

| Model | Quant | KV cache | PPL | Δ vs baseline |
|---|---|---|---|---|
| Qwen3.5-9B | Q6_K | f16 | 3.2560 | baseline |
| Qwen3.5-9B | Q6_K | turbo4 | 3.2871 | +0.96% |

## Planned: Quant vs Model Size Shootout

Goal: determine if a larger model at lower quantization beats a smaller model at higher quantization.

Models to download:
- Qwen3.5-9B-Q5_K_M (clean base)
- Qwen3.5-9B-Q4_K_M (clean base)
- Qwen3.6-27B-Q2_K (~fits 12GB VRAM at ~8-9GB)

Test matrix (same prompts, thinking budget controlled):
| Model | Quant | Est. VRAM | Est. t/s |
|---|---|---|---|
| Qwen3.5-9B | Q6_K | 9.67 GB | 40 t/s |
| Qwen3.5-9B | Q5_K_M | ~8.5 GB | ~43 t/s |
| Qwen3.5-9B | Q4_K_M | ~7.5 GB | ~46 t/s |
| Qwen3.6-27B | Q2_K | ~9-10 GB | ~15-20 t/s |

Benchmarks to run: PPL, reasoning (multi-step logic), tool call stability, instruction following.
