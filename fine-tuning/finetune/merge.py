"""Merge a QLoRA adapter into the base model weights for vLLM inference.

vLLM loads a plain HuggingFace model directory.  QLoRA adapters are separate
files (adapter_config.json + adapter_model.safetensors) that PEFT understands
but vLLM does not natively fuse at load time.  This module merges the low-rank
ΔW matrices back into the base weights (W ← W + BA) and saves a standard
model directory that vLLM can serve directly.

The merge is done in the dtype you specify (bfloat16 recommended) to avoid
precision loss.  No GPU is required — the operation runs on CPU if CUDA is
unavailable, though it is faster with a GPU.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoConfig, AutoModelForCausalLM, AutoProcessor, AutoTokenizer

from .config import MergeConfig

logger = logging.getLogger(__name__)

_DTYPE_MAP: dict[str, torch.dtype] = {
    "bfloat16": torch.bfloat16,
    "float16":  torch.float16,
}


def _write_preprocessor_config(base_dir: Path, output_dir: Path) -> None:
    """
    vLLM's HF renderer for Gemma 4 calls AutoFeatureExtractor / AutoImageProcessor
    which look for preprocessor_config.json. Gemma4Processor.save_pretrained
    doesn't write that file separately, so extract the image_processor sub-dict
    from the base's processor_config.json and write it ourselves.
    """
    src = base_dir / "processor_config.json"
    dst = output_dir / "preprocessor_config.json"
    if dst.exists():
        return
    if not src.exists():
        logger.warning(
            "Base dir has no processor_config.json; cannot synthesize "
            "preprocessor_config.json. vLLM will likely refuse to serve.",
        )
        return
    try:
        cfg = json.loads(src.read_text())
    except Exception as exc:
        logger.warning("Could not parse %s: %s", src, exc)
        return
    image_cfg = cfg.get("image_processor")
    if image_cfg is None:
        logger.warning(
            "processor_config.json has no 'image_processor' section; vLLM may "
            "refuse to serve this merged model.",
        )
        return
    dst.write_text(json.dumps(image_cfg, indent=2))
    logger.info("Wrote %s (extracted from base processor_config.json)", dst)


def merge_adapter(
    adapter_path: Path,
    base_model: str,
    output_dir: Path,
    dtype: str = "bfloat16",
) -> None:
    """
    Load base model + LoRA adapter, merge weights, save for vLLM.

    Steps
    ─────
    1. Load base model in target dtype (no quantization — we need exact weights).
    2. Wrap with PeftModel using the saved adapter.
    3. Call merge_and_unload() — fuses ΔW into W and strips PEFT wrappers.
    4. Save model + tokenizer with safetensors serialization.

    Args:
        adapter_path: Directory produced by train.py (contains adapter_config.json).
        base_model:   Original HF model path or ID used during training.
        output_dir:   Destination for the merged model (can be loaded by vLLM).
        dtype:        Weight dtype of the merged model.  bfloat16 is recommended
                      for A100/H100; use float16 for older GPUs.
    """
    torch_dtype = _DTYPE_MAP.get(dtype, torch.bfloat16)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load base in full precision (not quantized — we need exact float weights
    # for the merge arithmetic to be correct).
    #
    # NOTE: device_map="auto" silently dropped 18 RMSNorm tensors on Gemma 4 4B
    # (model.language_model.layers.24-41.self_attn.k_norm.weight) — accelerate's
    # offload hooks didn't round-trip them through save_pretrained. Pin to a
    # single device; the 8 GB bf16 base fits on H100 with room to spare.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Loading base model from %s in %s on %s ...", base_model, dtype, device)

    # Force num_kv_shared_layers=0 so all 42 K/V projections are materialized;
    # see finetune/model.py:_override_kv_sharing for the full rationale.
    cfg = AutoConfig.from_pretrained(base_model, trust_remote_code=True)
    text_cfg = cfg.text_config if hasattr(cfg, "text_config") else cfg
    if getattr(text_cfg, "num_kv_shared_layers", 0):
        logger.info(
            "Overriding num_kv_shared_layers: %d -> 0", text_cfg.num_kv_shared_layers
        )
        text_cfg.num_kv_shared_layers = 0

    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        config=cfg,
        torch_dtype=torch_dtype,
        device_map={"": device},
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )

    logger.info("Applying adapter from %s ...", adapter_path)
    model = PeftModel.from_pretrained(base, str(adapter_path))

    logger.info("Merging LoRA weights into base model ...")
    model = model.merge_and_unload()
    model.eval()

    logger.info("Saving merged model to %s ...", output_dir)
    # Force every tensor to its own allocation (avoid safetensors dedup).
    state_dict = {k: v.detach().clone().contiguous() for k, v in model.state_dict().items()}

    # transformers' Gemma 4 model class fails to instantiate some modules that
    # exist in the on-disk checkpoint (e.g. self_attn.k_norm for language-model
    # layers 24-41). vLLM, however, requires every tensor the architecture
    # declares. LoRA only targets q/k/v/o_proj + gate/up/down_proj, so any
    # tensor present in the base but missing after the merge is something
    # transformers dropped — copy it back from base verbatim.
    from safetensors import safe_open as _safe_open
    base_dir = Path(base_model)
    base_keys: set[str] = set()
    if base_dir.is_dir():
        patched = 0
        for sf in sorted(base_dir.glob("*.safetensors")):
            with _safe_open(str(sf), framework="pt") as h:
                for k in h.keys():
                    base_keys.add(k)
                    if k not in state_dict:
                        state_dict[k] = h.get_tensor(k).to(torch_dtype).contiguous()
                        patched += 1
        if patched:
            logger.info("Patched %d missing tensors from base", patched)

    model.save_pretrained(
        str(output_dir),
        state_dict=state_dict,
        safe_serialization=True,     # safetensors — required for vLLM
        max_shard_size="4GB",
    )
    del state_dict

    # Hard verification: every tensor in the base checkpoint must also be in
    # the merged dir. If not, vLLM will refuse to load. Fail loudly here
    # rather than after a 30-second vLLM startup.
    if base_keys:
        merged_keys: set[str] = set()
        for sf in sorted(output_dir.glob("*.safetensors")):
            with _safe_open(str(sf), framework="pt") as h:
                merged_keys.update(h.keys())
        missing = base_keys - merged_keys
        if missing:
            sample = sorted(missing)[:5]
            raise RuntimeError(
                f"Merge incomplete: {len(missing)} tensors from base are missing "
                f"in {output_dir}. Sample: {sample}. vLLM will refuse to load. "
                f"This is the same Gemma 4 architectural mismatch the patch above "
                f"is supposed to handle — investigate before serving."
            )
        logger.info("Verified: merged dir has all %d base tensors", len(base_keys))

    # The adapter directory also contains the tokenizer (we saved it there
    # during training).  Fall back to the base model tokenizer if not present.
    tokenizer_source = str(adapter_path) if (adapter_path / "tokenizer_config.json").exists() else base_model
    logger.info("Saving tokenizer from %s ...", tokenizer_source)
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source, trust_remote_code=True)
    tokenizer.save_pretrained(str(output_dir))

    # Gemma 4 is multimodal — vLLM's HF renderer demands preprocessor_config.json
    # / processor_config.json (image+audio processors) even when we serve text-only.
    # Always copy these from the base model so the merged dir is a complete HF
    # model directory.
    try:
        logger.info("Saving multimodal processor from %s ...", base_model)
        processor = AutoProcessor.from_pretrained(base_model, trust_remote_code=True)
        processor.save_pretrained(str(output_dir))
    except Exception as exc:
        logger.warning(
            "Could not save AutoProcessor (this is fine for text-only models, "
            "but vLLM will refuse to serve Gemma 4 without it): %s",
            exc,
        )

    # `Gemma4Processor.save_pretrained` writes processor_config.json but NOT a
    # separate preprocessor_config.json, which vLLM's HF renderer demands.
    # Extract the image_processor sub-dict from the base's processor_config.json
    # and write it as preprocessor_config.json in the merged dir.
    _write_preprocessor_config(Path(base_model), output_dir)

    logger.info("Merge complete.  Merged model: %s", output_dir)
    logger.info(
        "To serve with vLLM:\n"
        "  VLLM_MODEL=%s VLLM_TOOL_CALL_PARSER=gemma4 "
        "./evaluation_scripts/llm_eval/start_vllm.sh start",
        output_dir,
    )


def run_merge(cfg: MergeConfig) -> None:
    """Entry point called by the top-level merge.py CLI."""
    merge_adapter(
        adapter_path=cfg.adapter_path,
        base_model=cfg.base_model,
        output_dir=cfg.output_dir,
        dtype=cfg.dtype,
    )
