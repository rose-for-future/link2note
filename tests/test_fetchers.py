"""7 个网络 fetcher 的适配器单测：mock 掉网络/vendor/转写，只测字段映射、分支、临时目录处理。"""
import os
import shutil
import types

import pytest

from scripts.fetchers import douyin, podcast, bilibili, zhihu, weibo, xiaohongshu, wechat


def _rm(r):
    td = (r.get("extra") or {}).get("_tempdir")
    if td:
        shutil.rmtree(td, ignore_errors=True)


def _fail(*a, **k):
    raise AssertionError("不应被调用")


# ---------------- 抖音 ----------------
def test_douyin_maps_and_registers_tempdir(monkeypatch):
    monkeypatch.setattr(douyin, "extract_video_id", lambda url: "VID")
    monkeypatch.setattr(douyin, "download_audio", lambda vid, wd: (os.path.join(wd, "a.mp3"), "抖音标题"))
    monkeypatch.setattr(douyin, "transcribe_audio", lambda ap, cfg: "转写文字")
    r = douyin.fetch("https://v.douyin.com/x/", {"keep_audio": False})
    assert r["platform"] == "douyin" and r["type"] == "video"
    assert r["title"] == "抖音标题" and r["text"] == "转写文字"
    assert r["media"]["audio"] is None                 # keep_audio 默认不留
    assert os.path.isdir(r["extra"]["_tempdir"])        # 临时目录已登记
    _rm(r)


def test_douyin_keep_audio(monkeypatch):
    monkeypatch.setattr(douyin, "extract_video_id", lambda url: "V")
    monkeypatch.setattr(douyin, "download_audio", lambda vid, wd: (os.path.join(wd, "a.mp3"), "t"))
    monkeypatch.setattr(douyin, "transcribe_audio", lambda ap, cfg: "x")
    r = douyin.fetch("http://x", {"keep_audio": True})
    assert r["media"]["audio"].endswith("a.mp3")
    _rm(r)


def test_douyin_cleans_tempdir_on_failure(monkeypatch):
    cap = {}
    def dl(vid, wd):
        cap["wd"] = wd
        open(os.path.join(wd, "a.mp3"), "w").close()
        return os.path.join(wd, "a.mp3"), "t"
    monkeypatch.setattr(douyin, "extract_video_id", lambda url: "V")
    monkeypatch.setattr(douyin, "download_audio", dl)
    monkeypatch.setattr(douyin, "transcribe_audio", lambda ap, cfg: (_ for _ in ()).throw(RuntimeError("mlx缺失")))
    with pytest.raises(RuntimeError):
        douyin.fetch("http://x", {})
    assert not os.path.exists(cap["wd"])                # 失败时临时目录被清


# ---------------- 播客 ----------------
def test_podcast_maps(monkeypatch):
    monkeypatch.setattr(podcast, "download_audio", lambda url, wd: (os.path.join(wd, "a.mp3"), "播客标题"))
    monkeypatch.setattr(podcast, "transcribe_audio", lambda ap, cfg: "文字")
    r = podcast.fetch("https://xyz/ep", {})
    assert r["platform"] == "podcast" and r["type"] == "audio"
    assert r["title"] == "播客标题" and r["text"] == "文字"
    assert os.path.isdir(r["extra"]["_tempdir"])
    _rm(r)


# ---------------- 知乎 / 微博（同构） ----------------
@pytest.mark.parametrize("mod,plat", [(zhihu, "zhihu"), (weibo, "weibo")])
def test_zhihu_weibo_maps(monkeypatch, mod, plat):
    monkeypatch.setattr(mod, "get_video_info", lambda url: {"title": f"{plat}标题"})
    monkeypatch.setattr(mod, "download_audio", lambda url, wd: os.path.join(wd, "a.m4a"))
    monkeypatch.setattr(mod, "transcribe_audio", lambda ap, cfg: "文字")
    r = mod.fetch("http://x", {})
    assert r["platform"] == plat and r["type"] == "video"
    assert r["title"] == f"{plat}标题" and r["text"] == "文字"
    assert os.path.isdir(r["extra"]["_tempdir"])
    _rm(r)


# ---------------- B站（两条分支） ----------------
def test_bilibili_subtitle_first_no_download(monkeypatch):
    monkeypatch.setattr(bilibili, "extract_bvid", lambda url: "BV1")
    monkeypatch.setattr(bilibili, "extract_page", lambda url: 1)
    monkeypatch.setattr(bilibili, "get_info", lambda bvid, p: {"title": "B标题", "author": "UP", "cid": 1})
    monkeypatch.setattr(bilibili, "get_subtitle", lambda bvid, cid: "字幕全文")
    monkeypatch.setattr(bilibili, "download_audio", _fail)      # 有字幕不该下载
    monkeypatch.setattr(bilibili, "transcribe_audio", _fail)
    r = bilibili.fetch("https://www.bilibili.com/video/BV1", {})
    assert r["text"] == "字幕全文" and r["author"] == "UP"
    assert "_tempdir" not in (r["extra"] or {})                # 字幕路径不建临时目录


def test_bilibili_no_subtitle_transcribes(monkeypatch):
    monkeypatch.setattr(bilibili, "extract_bvid", lambda url: "BV1")
    monkeypatch.setattr(bilibili, "extract_page", lambda url: 1)
    monkeypatch.setattr(bilibili, "get_info", lambda bvid, p: {"title": "T", "author": "U", "cid": 1})
    monkeypatch.setattr(bilibili, "get_subtitle", lambda bvid, cid: None)
    monkeypatch.setattr(bilibili, "download_audio", lambda bvid, cid, wd: os.path.join(wd, "a.m4s"))
    monkeypatch.setattr(bilibili, "transcribe_audio", lambda ap, cfg: "转写")
    r = bilibili.fetch("http://x", {})
    assert r["text"] == "转写" and os.path.isdir(r["extra"]["_tempdir"])
    _rm(r)


# ---------------- 小红书 ----------------
def test_xiaohongshu_image_note(monkeypatch):
    fakeV = types.SimpleNamespace(
        http_get=lambda url, cookie="": ("<html>", "https://www.xiaohongshu.com/explore/LONG"),
        extract_initial_state=lambda html: {"s": 1},
        find_note=lambda state: {"note": 1},
        parse_from_state=lambda note: {"title": "XHS标题", "desc": "正文", "author": "作者",
                                       "tags": ["t"], "note_type": "normal", "images": ["u1", "u2"]},
        parse_from_meta=lambda html: None,
        compute_title=lambda data: data["title"],
        download_images=lambda urls, wd, base, cookie: [("local", "xhs.assets/0.jpg"), ("url", "http://img/2")],
    )
    monkeypatch.setattr(xiaohongshu, "V", fakeV)
    r = xiaohongshu.fetch("https://xhslink.com/x", {"save_images": True})
    assert r["platform"] == "xiaohongshu" and r["type"] == "image_text"
    assert r["url"] == "https://www.xiaohongshu.com/explore/LONG"   # 用 final_url
    assert r["title"] == "XHS标题" and r["text"] == "正文" and r["author"] == "作者"
    assert len(r["images"]) == 2
    assert r["images"][0]["path"].endswith("xhs.assets/0.jpg")
    assert r["images"][1]["url"] == "http://img/2" and r["images"][1]["path"] is None
    assert os.path.isdir(r["extra"]["_tempdir"])
    _rm(r)


def test_xiaohongshu_parse_fail_raises(monkeypatch):
    fakeV = types.SimpleNamespace(
        http_get=lambda url, cookie="": ("<html>", "http://final"),
        extract_initial_state=lambda html: None,
        find_note=lambda state: None,
        parse_from_meta=lambda html: None,
    )
    monkeypatch.setattr(xiaohongshu, "V", fakeV)
    with pytest.raises(RuntimeError):
        xiaohongshu.fetch("http://x", {})


# ---------------- 公众号 ----------------
def test_wechat_maps(monkeypatch):
    monkeypatch.setattr(wechat, "fetch_from_url", lambda url: ("公众号标题", "作者", "文章正文"))
    r = wechat.fetch("https://mp.weixin.qq.com/s/x", {})
    assert r["platform"] == "wechat" and r["type"] == "article"
    assert r["title"] == "公众号标题" and r["author"] == "作者" and r["text"] == "文章正文"


def test_wechat_empty_raises(monkeypatch):
    monkeypatch.setattr(wechat, "fetch_from_url", lambda url: (None, None, None))
    with pytest.raises(RuntimeError):
        wechat.fetch("http://x", {})
