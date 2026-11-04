import pytest
from nrm_api import config


def test_service_reads_shared_api_key(monkeypatch):
    monkeypatch.setattr(config, 'load_dotenv', lambda *args, **kwargs: None)
    for provider in ('ENM', 'MAINZER', 'ENETZ'):
        monkeypatch.delenv(provider + '_USERNAME', raising=False)
        monkeypatch.delenv(provider + '_PASSWORD', raising=False)
    monkeypatch.setenv('NRM_USERNAME', 'portal-user')
    monkeypatch.setenv('NRM_PASSWORD', 'portal-password')
    monkeypatch.setenv('NETZPORTAL_API_KEY', 'shared-service-key-' + 'x' * 32)
    settings = config.Settings.from_env()
    assert settings.api_key == 'shared-service-key-' + 'x' * 32
    assert settings.username == 'portal-user'
    assert settings.password == 'portal-password'
    monkeypatch.delenv('NETZPORTAL_API_KEY')
    with pytest.raises(ValueError, match='NETZPORTAL_API_KEY'):
        config.Settings.from_env()
