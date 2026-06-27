import pytest


@pytest.mark.smoke
def test_sensevoice_on_sample(tmp_path):
    # 放一个 5 秒中文 wav 到 tests/fixtures/sample_zh.wav 再跑
    from scripts.transcribe import transcribe_audio
    text = transcribe_audio("tests/fixtures/sample_zh.wav", {"transcribe_backend": "sensevoice"})
    assert isinstance(text, str) and len(text) > 0


@pytest.mark.smoke
def test_douyin_fetch_smoke():
    """End-to-end smoke test: real Douyin link -> ContentResult.
    Requires: network access, ffmpeg, SenseVoice model (iic/SenseVoiceSmall).
    Run manually: pytest tests/smoke -m smoke -k douyin -v
    Replace the URL below with a real Douyin share link before running.
    """
    from scripts.fetchers.douyin import fetch
    r = fetch(
        "https://v.douyin.com/粘贴真实分享链接/",
        {"transcribe_backend": "sensevoice", "keep_audio": False},
    )
    assert r["platform"] == "douyin"
    assert r["type"] == "video"
    assert isinstance(r["text"], str) and len(r["text"]) > 0


@pytest.mark.smoke
def test_xhs_fetch_smoke():
    from scripts.fetchers.xiaohongshu import fetch
    r = fetch("粘贴真实小红书链接", {"save_images": True, "xhs_cookie": ""})
    assert r["platform"] == "xiaohongshu"


@pytest.mark.smoke
def test_podcast_fetch_smoke():
    from scripts.fetchers.podcast import fetch
    r = fetch("粘贴真实小宇宙单集链接", {"keep_audio": False})
    assert r["platform"] == "podcast" and len(r["text"]) > 0
