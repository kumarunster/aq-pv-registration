"""Eine Quelle fuer das ganze Monorepo: die Datei VERSION im Wurzel."""

from pathlib import Path

VERSION_FILE = Path("/opt/app-version")
if not VERSION_FILE.exists():
    # Fallback fuer lokale Tests ohne Docker:
    VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"

VERSION = VERSION_FILE.read_text().strip()
