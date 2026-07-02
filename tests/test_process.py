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


def test_run_cleans_tempdir(tmp_path, monkeypatch):
    import tempfile, os
    td = tempfile.mkdtemp()
    open(os.path.join(td, "x.mp3"), "w").close()
    def fake(url, cfg):
        return make_result("douyin", "video", url, "标题T", "正文", extra={"_tempdir": td})
    monkeypatch.setitem(process.REGISTRY, "douyin", fake)
    cfg = {"notes_dir": str(tmp_path/"n"), "assets_dir": str(tmp_path/"a"), "save_images": True}
    process.run("https://v.douyin.com/abc/", cfg)
    assert not os.path.exists(td)   # 临时目录被清理


def test_run_dual_key_index_short_and_final_url(tmp_path, monkeypatch):
    import json
    def fake(url, cfg):
        return make_result("xiaohongshu", "image_text",
                           "https://www.xiaohongshu.com/explore/LONG", "标题", "正文")
    monkeypatch.setitem(process.REGISTRY, "xiaohongshu", fake)
    cfg = {"notes_dir": str(tmp_path/"n"), "assets_dir": str(tmp_path/"a"), "save_images": True}
    process.run("https://xhslink.com/SHORT", cfg)
    idx = json.load(open(str(tmp_path/"n"/".link2note_index.json"), encoding="utf-8"))
    assert "https://xhslink.com/SHORT" in idx           # 输入短链
    assert "https://www.xiaohongshu.com/explore/LONG" in idx   # 解析后长链也存了
