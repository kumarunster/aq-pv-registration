"""The normal customer save path must retain embedded map and lookup provenance."""
from fastapi.encoders import jsonable_encoder
from src.models.entities import CustomerCreate, CustomerUpdate, PlantUpdate
from src.services import customers

ADDRESS = 'Im Schönenfelde 14, 21109 Hamburg'
PLANT = {
    'anlagetyp': 'pv', 'gemarkung': 'Wilhelmsburg', 'flur': None, 'flurstueck': '2798',
    'kataster': {'adresse': ADDRESS, 'abgerufen_am': '2026-11-03T10:00:00Z',
        'grundstueck_status': 'ok', 'bild_status': 'ok', 'hintergrund_uebernommen': True,
        'gemarkung': 'Wilhelmsburg', 'flur': None, 'flurstueck': '2798',
        'flurstueckskennzeichen': '020147___02798______', 'amtliche_flaeche_m2': 1005},
    'lageplan': {'title': 'Lageplan PV', 'background_image_url': 'data:image/png;base64,cG5n',
        'background_image_width': 1600, 'background_image_height': 1340,
        'elements': [{'id': 'panel1', 'x': 12}], 'metadata': {'adresse': ADDRESS, 'gemarkung': 'Wilhelmsburg'}},
}


async def test_create_update_and_read_keep_lookup_and_background(mongomock_motor_db, monkeypatch):
    monkeypatch.setattr(customers, 'get_db', lambda: mongomock_motor_db)
    body = CustomerCreate(firstname='Max', lastname='Muster', address_street='Im Schönenfelde 14',
        address_plz='21109', address_city='Hamburg', plants=[PLANT])
    saved = await customers.create(jsonable_encoder(body))
    update = CustomerUpdate(plants=[PLANT])
    saved = await customers.update(saved['_id'], jsonable_encoder(update), updated_by='installer')
    read = await customers.get_by_id(saved['_id'])
    p = read['plants'][0]
    assert p['kataster']['hintergrund_uebernommen'] is True
    assert p['kataster']['grundstueck_status'] == 'ok'
    assert p['flur'] is None
    assert p['gemarkung'] == 'Wilhelmsburg'
    assert p['lageplan']['background_image_url'].startswith('data:image/png;base64,')
    assert p['lageplan']['elements'] == PLANT['lageplan']['elements']


def test_plant_update_keeps_provenance_and_legacy_plants_remain_valid():
    assert jsonable_encoder(PlantUpdate(**PLANT))['kataster']['flurstueck'] == '2798'
    assert PlantUpdate(anlagetyp='pv').kataster is None
