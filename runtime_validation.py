from __future__ import annotations

from typing import Any

from providers_manifest import get_provider_manifest


def get_runtime_validation() -> dict[str, Any]:
    manifest = get_provider_manifest()
    selected_model = manifest["selected"]["model_provider"]
    selected_traces = manifest["selected"]["traces_provider"]

    model_info = manifest["model_providers"].get(selected_model, {})
    trace_info = manifest["trace_providers"].get(selected_traces, {})

    issues: list[str] = []
    if selected_model != "mock":
        if not model_info.get("implemented", False):
            missing = model_info.get("missing_env") or model_info.get("requires_env") or []
            issues.append(
                f"Model provider '{selected_model}' is not implemented or configured. Missing: {', '.join(missing) or 'unknown'}."
            )
        elif model_info.get("missing_env"):
            issues.append(
                f"Model provider '{selected_model}' is missing env: {', '.join(model_info['missing_env'])}."
            )

    if selected_traces != "local" and not trace_info.get("implemented", False):
        missing = trace_info.get("missing_env") or trace_info.get("requires_env") or []
        issues.append(
            f"Trace provider '{selected_traces}' is not implemented or configured. Missing: {', '.join(missing) or 'unknown'}."
        )

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "selected_model_provider": selected_model,
        "selected_traces_provider": selected_traces,
    }
