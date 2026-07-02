import pytest
from scripts.router import classify

@pytest.mark.parametrize("url,platform,ctype", [
    ("https://v.douyin.com/abc123/", "douyin", "video"),
    ("https://www.douyin.com/video/7300000000000000000", "douyin", "video"),
    ("https://www.xiaohongshu.com/explore/abc", "xiaohongshu", "image_text"),
    ("https://xhslink.com/xyz", "xiaohongshu", "image_text"),
    ("https://www.xiaoyuzhoufm.com/episode/abc", "podcast", "audio"),
    ("https://www.bilibili.com/video/BV1xx411c7mD", "bilibili", "video"),
    ("https://weibo.com/1234/Abcdef", "weibo", "video"),
    ("https://www.zhihu.com/question/1/answer/2", "zhihu", "article"),
    ("https://mp.weixin.qq.com/s/abcDEF", "wechat", "article"),
    ("https://blog.csdn.net/user/article/details/123", "csdn", "article"),
    ("https://github.com/owner/repo", "github", "repo"),
    # Regression tests: ensure generic media/RSS rules don't shadow platform rules
    ("https://weibo.com/u/123/rss", "weibo", "video"),
    ("https://github.com/owner/repo/releases/download/v1.0/feed.xml", "github", "repo"),
    ("https://feeds.fireside.fm/show/rss", "podcast", "audio"),
    ("https://example.com/audio.mp3", "podcast", "audio"),
])
def test_classify(url, platform, ctype):
    r = classify(url)
    assert r["platform"] == platform
    assert r["type"] == ctype

def test_unknown_raises():
    with pytest.raises(ValueError):
        classify("https://example.com/foo")


def test_domain_spoofing_rejected():
    # 子串冒充域名不应被判成平台（否则会把 cookie 发给攻击者）
    with pytest.raises(ValueError):
        classify("http://xhslink.com.attacker.com/note")
    with pytest.raises(ValueError):
        classify("http://evil.com/?ref=github.com")
    with pytest.raises(ValueError):
        classify("http://notbilibili.com/video/BV1x")


def test_b23_and_subdomains_ok():
    assert classify("https://b23.tv/AbCdEf")["platform"] == "bilibili"
    assert classify("https://m.bilibili.com/video/BV1x")["platform"] == "bilibili"
    assert classify("https://blog.csdn.net/u/article/details/1")["platform"] == "csdn"
