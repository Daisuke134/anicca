"""One cheap *cloud* forward-pass comparison: Qwen3-4B vs Be.FM 1.5-4B.

Requirements: personal Hugging Face access accepted for befm/BeFM1.5-4B;
a Modal Starter workspace with a Secret named hf-manager-models (HF_TOKEN).
Run: modal run products/manager/experiments/cloud/modal_befm4_probe.py

No BehaviorBench CC BY-NC-ND evaluation dataset is downloaded.
A generated answer is NOT a scientific claim of human predictive accuracy.
"""
import os
import modal

APP_NAME = "manager-behavior-befm4-pilot"
BASE_ID = "Qwen/Qwen3-4B-Instruct-2507"
BASE_REV = "cdbee75f17c01a7cc42f958dc650907174af0554"
ADAPTER_ID = "befm/BeFM1.5-4B"
ADAPTER_REV = "85b1fd83b707187533019e1fd8fc954382e8af1b"

app = modal.App(APP_NAME)
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "torch>=2.5,<3", "transformers>=4.55,<5", "peft>=0.15,<1",
    "accelerate>=1.0,<3", "safetensors>=0.5", "huggingface_hub>=0.29"
)
cache = modal.Volume.from_name("manager-befm-cache", create_if_missing=True)
hf_secret = modal.Secret.from_name("hf-manager-models", required_keys=["HF_TOKEN"])


@app.function(
    image=image, gpu="L4", timeout=900, cpu=4.0, memory=16384,
    secrets=[hf_secret], volumes={"/hf-cache": cache},
    max_containers=1,
)
def compare_base_and_adapter(question: str, max_new_tokens: int = 32) -> dict:
    """Forward pass on one safe NONPERSONAL question, not an accuracy benchmark."""
    if not 1 <= max_new_tokens <= 64:
        raise ValueError("max_new_tokens must be in [1,64]")
    if len(question) > 1000:
        raise ValueError("nonpersonal test question too long")
    os.environ["HF_HOME"] = "/hf-cache"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    token = os.environ["HF_TOKEN"]
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_ID, revision=BASE_REV, token=token
    )
    base = AutoModelForCausalLM.from_pretrained(
        BASE_ID,
        revision=BASE_REV,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        token=token,
        trust_remote_code=False,
    )
    base.eval()

    msgs = [
        {"role": "system", "content": "You are a participant in a behavioral study. Answer briefly."},
        {"role": "user", "content": question},
    ]
    encoded = tokenizer.apply_chat_template(
        msgs, add_generation_prompt=True, return_tensors="pt"
    ).to(base.device)

    def generate_text(model):
        with torch.inference_mode():
            ids = model.generate(
                encoded, max_new_tokens=max_new_tokens,
                do_sample=False, pad_token_id=tokenizer.eos_token_id
            )
        return tokenizer.decode(
            ids[0, encoded.shape[1]:], skip_special_tokens=True
        ).strip()

    base_answer = generate_text(base)
    adapted = PeftModel.from_pretrained(
        base, ADAPTER_ID, revision=ADAPTER_REV, token=token
    )
    adapted.eval()
    befm_answer = generate_text(adapted)
    cache.commit()
    return {
        "source": "actual_cloud_model_forward_pass",
        "baseline": BASE_ID,
        "base_revision": BASE_REV,
        "adapter": ADAPTER_ID,
        "adapter_revision": ADAPTER_REV,
        "prompt": question,
        "baseline_output": base_answer,
        "befm_output": befm_answer,
        "max_new_tokens": max_new_tokens,
        "predictive_accuracy_measured": False,
        "causal_benefit_measured": False,
    }


@app.local_entrypoint()
def main():
    question = (
        "In an anonymous one-round game, a participant receives ten tokens "
        "and may freely give any number from 0 to 10 to another participant. "
        "Answer only the number of tokens you choose to give."
    )
    # A GitHub Actions cloud job can call this; no Mac GPU or local model needed.
    result = compare_base_and_adapter.remote(question=question, max_new_tokens=24)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
