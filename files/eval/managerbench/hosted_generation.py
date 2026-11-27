"""Classify public hosted demo receipts, never score provider errors as predictions."""
import json

def classify(receipt):
    model = receipt.get("config", {}).get("model")
    if not isinstance(model, str) or not model:
        return {"status": "MODEL_ID_UNVERIFIED", "valid": False}
    events = receipt.get("events", [])
    if receipt.get("status") == "failed":
        return {"status": "TRANSPORT_FAILURE", "valid": False, "model": model}
    if len(events) < 2 or events[-2] != "event: complete" or not events[-1].startswith("data: "):
        return {"status": "INCOMPLETE_STREAM", "valid": False, "model": model}
    try:
        data = json.loads(events[-1][6:])
        if not isinstance(data, list) or len(data) != 1:
            raise ValueError("invalid envelope")
        payload = json.loads(data[0])
        answer = payload["text"]
        if not isinstance(answer, str):
            raise ValueError("invalid text")
    except (ValueError, TypeError, KeyError):
        return {"status": "INVALID_ENVELOPE", "valid": False, "model": model}
    if "GPU limit" in answer and "Generation failed before any output" in answer:
        return {"status": "PROVIDER_GPU_LIMIT", "valid": False, "model": model}
    if payload.get("truncated") is not False or not answer.strip() or answer.startswith("⚠"):
        return {"status": "INCOMPLETE_OR_PROVIDER_ERROR", "valid": False, "model": model}
    return {"status": "OUTPUT_REQUIRES_TASK_EVALUATION", "valid": False, "model": model}
