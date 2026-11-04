"""Guard the deployment boundary: nginx -> backend -> private cadastral port."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_kataster_has_no_host_port_and_only_backend_shares_its_private_network():
    compose = yaml.safe_load((ROOT / '_infrastructure/docker-compose.yml').read_text())
    services = compose['services']
    kataster = services['na-kataster']
    assert not kataster.get('ports')
    assert kataster['expose'] == ['8765']
    assert 'na-intranet' not in kataster['networks']
    assert compose['networks']['na-kataster-private']['internal'] is True
    peers = {name for name, service in services.items() if 'na-kataster-private' in service.get('networks', [])}
    assert peers == {'na-backend', 'na-kataster'}
    assert services['na-backend']['depends_on']['na-kataster']['condition'] == 'service_healthy'
    assert compose['networks']['na-kataster-egress'].get('internal', False) is False


def test_kataster_persistence_and_nginx_remain_separate():
    compose = yaml.safe_load((ROOT / '_infrastructure/docker-compose.yml').read_text())
    kataster = compose['services']['na-kataster']
    assert 'na-kataster-data:/data' in kataster['volumes']
    assert 'na-kataster-data' in compose['volumes']
    nginx = (ROOT / '_infrastructure/nginx/nginx.conf').read_text()
    assert 'na-kataster' not in nginx
    assert 'proxy_read_timeout 330s;' in nginx


def test_gateway_timeouts_allow_backend_relay_to_complete():
    config = yaml.safe_load((ROOT / '_infrastructure/auth-oathkeeper/oathkeeper-config/oathkeeper.yml').read_text())
    assert config['serve']['proxy']['timeout']['write'] == '330s'
    assert config['serve']['proxy']['timeout']['idle'] == '330s'
