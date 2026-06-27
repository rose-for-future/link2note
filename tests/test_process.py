from scripts import process
from scripts.models import make_result

def test_run_routes_and_renders(tmp_path, monkeypatch):
    def fake_fetch(url, cfg):
        return make_result("douyin","video",url,"标题X","正文Y")
    monkeypatch.setitem(process.REGISTRY, "douyin", fake_fetch)
    cfg = {"notes_dir": str(tmp_path/"n"), "assets_dir": str(tmp_path/"a"),
           "keep_audio": False, "keep_video": False, "save_images": True}
    out = process.run("https://v.douyin.com/abc/", cfg)
    assert out["platform"] == "douyin"
    md = open(out["transcript_path"], encoding="utf-8").read()
    assert "正文Y" in md

def test_run_unknown_platform_raises(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        process.run("https://example.com/x", {"notes_dir": str(tmp_path)})
