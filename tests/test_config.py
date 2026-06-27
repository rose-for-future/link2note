import json, os
from scripts.config import load_config, DEFAULTS

def test_defaults_have_required_keys():
    for k in ["notes_dir", "assets_dir", "keep_audio", "keep_video",
              "transcribe_backend", "xhs_cookie"]:
        assert k in DEFAULTS

def test_load_missing_returns_defaults():
    cfg = load_config("/nonexistent/config.json")
    assert cfg["notes_dir"] == DEFAULTS["notes_dir"]
    assert cfg["keep_video"] is False

def test_user_config_overrides_and_backfills(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"keep_video": True, "notes_dir": "/x"}), encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg["keep_video"] is True          # override
    assert cfg["notes_dir"] == "/x"           # override
    assert cfg["keep_audio"] is False         # backfilled from DEFAULTS
    assert "transcribe_backend" in cfg        # backfilled
