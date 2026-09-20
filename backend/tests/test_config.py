from app.config import Settings, database_path_for_env


def test_database_path_fallback(monkeypatch):
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    assert database_path_for_env(None) == "data/meraki.db"
    assert database_path_for_env("") == "data/meraki.db"


def test_database_path_uses_volume_mount():
    assert database_path_for_env("/data") == "/data/meraki.db"


def test_settings_prefer_railway_volume(monkeypatch):
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
    loaded = Settings(secret_key="test-secret", database_path="data/meraki.db")
    assert loaded.database_path == "/data/meraki.db"
    again = Settings(secret_key="test-secret", database_path="/data/meraki.db")
    assert again.database_path == "/data/meraki.db"
