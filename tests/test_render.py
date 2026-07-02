import os
from scripts.models import make_result
from scripts.render import render

def _cfg(tmp_path):
    return {"notes_dir": str(tmp_path/"notes"), "assets_dir": str(tmp_path/"assets"),
            "keep_audio": False, "keep_video": False, "save_images": True}

def test_assets_dir_follows_deduped_note_dir(tmp_path):
    # 同标题不同链接：成稿目录去重后，素材目录也必须跟着去重，否则图片互相覆盖
    s1 = tmp_path/"s1"; s1.mkdir(); (s1/"p.jpg").write_bytes(b"AAA")
    s2 = tmp_path/"s2"; s2.mkdir(); (s2/"p.jpg").write_bytes(b"BBBB")
    cfg = _cfg(tmp_path)
    r1 = make_result("xhs", "image_text", "http://x/1", "同标题", "t1",
                     images=[{"path": str(s1/"p.jpg"), "url": ""}])
    r2 = make_result("xhs", "image_text", "http://x/2", "同标题", "t2",
                     images=[{"path": str(s2/"p.jpg"), "url": ""}])
    o1 = render(r1, cfg)
    o2 = render(r2, cfg)
    assert o1["note_dir"] != o2["note_dir"]       # 成稿去重
    assert o1["assets_dir"] != o2["assets_dir"]   # 素材也去重（修复点）
    assert open(os.path.join(o1["assets_dir"], "00_p.jpg"), "rb").read() == b"AAA"
    assert open(os.path.join(o2["assets_dir"], "00_p.jpg"), "rb").read() == b"BBBB"


def test_writes_transcript_with_link_on_top(tmp_path):
    r = make_result("douyin", "video", "http://x/v", "我的视频", "这是文字稿正文")
    out = render(r, _cfg(tmp_path))
    md = open(out["transcript_path"], encoding="utf-8").read()
    assert md.splitlines()[0] == "# 我的视频"
    assert "- 原文链接：http://x/v" in md
    assert "这是文字稿正文" in md
    assert out["summary_path"].endswith("总结.md")

def test_keep_audio_off_skips_media(tmp_path):
    audio = tmp_path/"a.mp3"; audio.write_bytes(b"x")
    r = make_result("podcast","audio","http://x","标题","稿", media={"audio": str(audio)})
    out = render(r, _cfg(tmp_path))
    assert out["assets_dir"] is None  # 无图片、音频开关关 → 不建素材目录

def test_keep_audio_on_copies_media(tmp_path):
    audio = tmp_path/"a.mp3"; audio.write_bytes(b"x")
    cfg = _cfg(tmp_path); cfg["keep_audio"] = True
    r = make_result("podcast","audio","http://x","标题","稿", media={"audio": str(audio)})
    out = render(r, cfg)
    assert os.path.exists(os.path.join(out["assets_dir"], "a.mp3"))

def test_images_referenced_and_copied(tmp_path):
    img = tmp_path/"img1.jpg"; img.write_bytes(b"x")
    r = make_result("xiaohongshu","image_text","http://x","图文","正文",
                    images=[{"path": str(img), "url": "http://x/i.jpg"}])
    out = render(r, _cfg(tmp_path))
    md = open(out["transcript_path"], encoding="utf-8").read()
    # The reference must NOT be an absolute path
    assert "img1.jpg" in md
    for line in md.splitlines():
        if "img1.jpg" in line and line.startswith("!["):
            assert not line.startswith("![](/"), \
                f"image reference should be relative, got: {line}"
    # The copied file must exist under assets_dir with the index prefix
    assert out["assets_dir"] is not None
    copied = [f for f in os.listdir(out["assets_dir"]) if "img1.jpg" in f]
    assert copied, "copied file not found in assets_dir"
    assert os.path.exists(os.path.join(out["assets_dir"], copied[0]))

def test_image_filename_collision(tmp_path):
    """Two images with the same basename from different dirs both survive."""
    dir_a = tmp_path / "a"; dir_a.mkdir()
    dir_b = tmp_path / "b"; dir_b.mkdir()
    img_a = dir_a / "img1.jpg"; img_a.write_bytes(b"aaa")
    img_b = dir_b / "img1.jpg"; img_b.write_bytes(b"bbb")
    r = make_result("xiaohongshu","image_text","http://x","碰撞测试","正文",
                    images=[{"path": str(img_a)}, {"path": str(img_b)}])
    out = render(r, _cfg(tmp_path))
    assert out["assets_dir"] is not None
    files = os.listdir(out["assets_dir"])
    # Both should exist with distinct indexed names
    assert len(files) == 2, f"expected 2 files, got {files}"
    assert any("img1.jpg" in f for f in files)
    md = open(out["transcript_path"], encoding="utf-8").read()
    # Both images should be referenced
    img_refs = [l for l in md.splitlines() if l.startswith("![") and "img1.jpg" in l]
    assert len(img_refs) == 2, f"expected 2 image references, got {img_refs}"
    # References are relative (do not start with /)
    for ref in img_refs:
        assert not ref.startswith("![](/"), f"reference should be relative: {ref}"

def test_missing_image_path_no_url_returns_none_assets_dir(tmp_path):
    """save_images=True but path doesn't exist and no url → assets_dir is None, no empty dir."""
    r = make_result("xiaohongshu","image_text","http://x","无效图","正文",
                    images=[{"path": "/nonexistent/no_such_file.jpg"}])
    out = render(r, _cfg(tmp_path))
    assert out["assets_dir"] is None
    # The assets dir itself must not exist on disk
    assets_root = str(tmp_path / "assets")
    assert not os.path.exists(assets_root), \
        f"assets dir should not have been created, but found: {assets_root}"
