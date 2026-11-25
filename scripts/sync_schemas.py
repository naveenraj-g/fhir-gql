"""
Refresh the FHIR R4 Pydantic models copied from fhir-server.

`app/schemas/fhir_datatypes/` and `app/schemas/fhir_resources/` are generated in the sibling
fhir-server repo (`scripts/generate_fhir_datatypes.py`, `scripts/generate_fhir_resources.py`) and
copied here unchanged, keeping the same module paths so the files need no editing. Run this after
regenerating them there:

    uv run python scripts/sync_schemas.py [path-to-fhir-server]
"""

import shutil
import sys
from pathlib import Path

# The two generated packages that are shared between the repos.
PACKAGES = ("fhir_datatypes", "fhir_resources")


def main() -> None:
    """Replace each shared package here with the current copy from fhir-server."""
    # Default: the sibling checkout next to this repo.
    server = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).parents[2] / "fhir-server"
    )
    source = server / "app" / "schemas"
    target = Path(__file__).parents[1] / "app" / "schemas"
    for package in PACKAGES:
        if not (source / package).is_dir():
            raise SystemExit(
                f"{source / package} not found - pass the fhir-server path"
            )
        # Remove the old copy first so a file deleted upstream disappears here too.
        shutil.rmtree(target / package, ignore_errors=True)
        shutil.copytree(
            source / package,
            target / package,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        print(f"synced {package}")


if __name__ == "__main__":
    main()
