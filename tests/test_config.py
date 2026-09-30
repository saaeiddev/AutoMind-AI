from core.config import ConfigManager


def test_config_persists(tmp_path):
    path = tmp_path / "settings.json"
    cfg = ConfigManager(path)
    cfg.set("general", "units", "imperial")
    cfg2 = ConfigManager(path)
    assert cfg2.get("general", "units") == "imperial"
    assert cfg2.get("ai", "enabled") is False
