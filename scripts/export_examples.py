from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import _app_metadata
from providers_manifest import get_provider_manifest
from runtime_validation import get_runtime_validation


def main() -> None:
    examples_dir = ROOT / "examples"
    examples_dir.mkdir(exist_ok=True)

    health = {
        "status": "ok",
        "runtime": _app_metadata()["runtime"],
        "validation": _app_metadata()["runtime_validation"],
    }
    meta = _app_metadata()
    providers = get_provider_manifest()
    runtime_validation = get_runtime_validation()

    (examples_dir / "health.example.json").write_text(json.dumps(health, indent=2), encoding="utf-8")
    (examples_dir / "meta.example.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (examples_dir / "providers.example.json").write_text(json.dumps(providers, indent=2), encoding="utf-8")
    (examples_dir / "runtime-validation.example.json").write_text(
        json.dumps(runtime_validation, indent=2), encoding="utf-8"
    )
    print("examples-exported")


if __name__ == "__main__":
    main()
