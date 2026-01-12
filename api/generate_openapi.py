"""Generate OpenAPI schema for type generation."""

import json
from pathlib import Path

from api.main import app

if __name__ == "__main__":
    openapi_schema = app.openapi()

    # Write to app types directory
    output_path = Path(__file__).parent.parent / "app" / "src" / "types" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"✓ OpenAPI schema generated at {output_path}")
