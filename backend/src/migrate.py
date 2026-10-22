"""Startbefehl des Migrationscontainers: `python -m src.migrate`.

Laeuft einmal durch und endet:
  Rueckgabewert 0 - Datenbank ist auf Stand (auch wenn nichts zu tun war)
  Rueckgabewert 1 - Migration fehlgeschlagen
"""

import asyncio
import logging
import sys

from src.config import settings
from src.migrations.runner import run_all
from src.services import database
from src.version import VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("migrate")


async def _lauf() -> int:
    logger.info("Migrationslauf, Projektversion %s (env=%s)", VERSION, settings.app_env)
    try:
        await database.connect()
    except Exception as fehler:
        logger.error("Keine Verbindung zur Datenbank: %s", fehler)
        return 1

    try:
        await run_all(database.get_db())
    except Exception as fehler:
        logger.error("Migration abgebrochen: %s", fehler)
        return 1
    finally:
        database.disconnect()

    logger.info("Fertig.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_lauf()))
