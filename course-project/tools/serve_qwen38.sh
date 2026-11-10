#!/usr/bin/env bash
# Serve Qwen3.8-Flash-Next (NVFP4, fp8 hybrid) with vLLM on the Spark, for the BeaconMind L2 arm.
#
# Usage (Spark host):  bash course-project/tools/serve_qwen38.sh start|stop|status|wait|logs
#
# The server is the M1.T15 / OD8 server (container `qwen38-flash`, image qwen38-flash-dgx:v0.30 built from
# https://github.com/blazux/qwen3.8-Flash-DGX at 5d944b3, evidence/M1/M1.T15/qwen38-flash-server-args.txt)
# with ONE change: the served model name is the real checkpoint name, not the "Qwen/Qwen3.5-35B-A3B" alias the
# old harness needed, so every logged turn names the model that answered. Every other argument, the image,
# the chat template and the weights are the same. The container is a new one (`bm-qwen38`); `qwen38-flash`
# is left as it was.
#
# Memory: --gpu-memory-utilization 0.80 takes about 97 GB of the 121 GB unified memory, so Ollama's Gemma 4
# (about 52 GB) cannot be loaded at the same time. Stop this server before a Gemma run (and vice versa).
# Binds 127.0.0.1:8000 only.
#
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this launcher from `docker inspect qwen38-flash`.
set -euo pipefail

NAME=bm-qwen38
IMAGE=qwen38-flash-dgx:v0.30
SERVED=nvidia/Qwen3.8-Flash-Next-NVFP4
SNAP=/hf/hub/models--nvidia--Qwen3.8-Flash-Next-NVFP4/snapshots/fc694b54fb0174e0913e6adf86691ef85a4ead47-fp8hybrid
TEMPLATE_HOST="$HOME/.cache/huggingface/qwen38-flash-dgx/chat-templates/models--nvidia--Qwen3.8-Flash-Next-NVFP4--fc694b54fb0174e0913e6adf86691ef85a4ead47-fp8hybrid.jinja"
PORT=8000

SPLIT_OPS='["vllm::unified_attention_with_output","vllm::unified_mla_attention_with_output","vllm::mamba_mixer2","vllm::mamba_mixer","vllm::short_conv","vllm::qwen4_exp_ple_short_conv","vllm::qwen4_exp_qsa_with_output","vllm::linear_attention","vllm::qwen_gdn_attention_core","vllm::qwen_gdn_attention_core_fused_norm_packed","vllm::gdn_attention_core_xpu","vllm::olmo_hybrid_gdn_full_forward","vllm::sparse_attn_indexer","vllm::rocm_aiter_sparse_attn_indexer","vllm::deepseek_v4_attention","vllm::hpc_rope_norm_forward","vllm::unified_kv_cache_update","vllm::unified_mla_kv_cache_update","vllm::ple_mmap_lookup_ids"]'
HF_OVERRIDES='{"text_config": {"rope_parameters": {"mrope_interleaved": true, "mrope_section": [11, 11, 10], "rope_type": "yarn", "rope_theta": 10000000, "partial_rotary_factor": 0.25, "factor": 4.0, "original_max_position_embeddings": 262144}}}'
SPEC='{"method":"mtp","num_speculative_tokens":2,"max_model_len":500000}'

ready() { curl -sf -m 5 "http://127.0.0.1:${PORT}/v1/models" | grep -q "\"${SERVED}\""; }

case "${1:-}" in
  start)
    if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then echo "$NAME already running"; exit 0; fi
    if docker ps --format '{{.Names}} {{.Ports}}' | grep -q "127.0.0.1:${PORT}->"; then
      echo "port ${PORT} is taken by another container:"; docker ps --format '{{.Names}} {{.Ports}}' | grep ":${PORT}->"; exit 1
    fi
    if curl -s -m 3 http://127.0.0.1:11434/api/ps | grep -q '"name"'; then
      echo "Ollama has a model loaded; unload it first (curl .../api/generate -d '{\"model\":\"<m>\",\"keep_alive\":0}')"; exit 1
    fi
    docker rm "$NAME" >/dev/null 2>&1 || true
    # The recipe's run script set these on the container (they are not in the image); copied from
    # `docker inspect qwen38-flash` (Config.Env minus the image's Config.Env), unchanged.
    docker run -d --name "$NAME" --gpus all --ipc host --shm-size 16g \
      -p "127.0.0.1:${PORT}:8000" \
      -e VLLM_QSA_EXACT_TOPK=0 -e VLLM_QSA_DET_TOPK=1 \
      -e VLLM_MTP_DRAFT_VOCAB=/opt/llm/draft_vocab_65536.npy -e VLLM_PLE_MMAP_PREWARM=0 \
      -e VLLM_QSA_DET_LIB=/opt/llm/kernel-det/_C_det.so -e VLLM_PLE_MMAP_MADVISE=random \
      -e VLLM_PLE_MMAP_FAST_ROWS=0 -e VLLM_FP8_HYBRID=1 -e VLLM_PLE_MMAP=1 -e VLLM_PLE_MMAP_WORKERS=32 \
      -e VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 -e VLLM_USE_DEEP_GEMM=0 -e VLLM_USE_FLASHINFER_SAMPLER=1 \
      -e HF_HOME=/hf -e HF_HUB_OFFLINE=1 \
      -v "$HOME/.cache/huggingface:/hf" \
      -v "${TEMPLATE_HOST}:/qwen38/chat_template.jinja:ro" \
      "$IMAGE" \
      "$SNAP" --served-model-name "$SERVED" --host 0.0.0.0 --port 8000 --load-format safetensors \
      --max-model-len 500000 --max-num-seqs 8 --gpu-memory-utilization 0.80 \
      --enable-prefix-caching --enable-prompt-tokens-details --enable-chunked-prefill --max-num-batched-tokens 8192 \
      -cc.cudagraph_mode=PIECEWISE "-cc.splitting_ops=${SPLIT_OPS}" \
      --no-enable-flashinfer-autotune --kv-cache-dtype auto --hf-overrides "$HF_OVERRIDES" \
      --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
      --chat-template /qwen38/chat_template.jinja --speculative-config "$SPEC" >/dev/null
    echo "started $NAME (loading takes several minutes; run: $0 wait)"
    ;;
  wait)
    for _ in $(seq 1 180); do
      if ready; then echo "ready: ${SERVED} on 127.0.0.1:${PORT}"; exit 0; fi
      if ! docker ps --format '{{.Names}}' | grep -qx "$NAME"; then echo "$NAME exited:"; docker logs --tail 40 "$NAME"; exit 1; fi
      sleep 10
    done
    echo "not ready after 30 min"; exit 1
    ;;
  stop)
    docker stop "$NAME" >/dev/null 2>&1 && echo "stopped $NAME" || echo "$NAME was not running"
    ;;
  status)
    docker ps -a --filter "name=^${NAME}$" --format '{{.Names}}\t{{.Status}}'
    ready && echo "serving ${SERVED}" || echo "not serving"
    ;;
  logs)
    docker logs --tail "${2:-60}" "$NAME"
    ;;
  *)
    echo "usage: $0 start|stop|status|wait|logs [n]"; exit 2
    ;;
esac
