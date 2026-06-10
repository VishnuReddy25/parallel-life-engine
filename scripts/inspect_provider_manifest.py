from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from providers_manifest import get_provider_manifest


def main() -> None:
    print(json.dumps(get_provider_manifest(), indent=2))


if __name__ == "__main__":
    main()
