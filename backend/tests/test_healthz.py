"""Rauchtest: healthz liefert ok mit DB-Ping. (Kommt in Schritt 1,
sobald das Datenmodell steht - bis hierhin nur Geruest.)"""


async def test_healthz_smoke(mongomock_motor_db):
    # Platzhalter: wird mit dem echten Datenmodell ausgebaut.
    assert True
