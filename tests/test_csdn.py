import pytest
from scripts.fetchers.csdn import parse

_HTML = """
<html><head><meta property="og:article:author" content="张三"></head>
<body>
<div class="blog-content-box">
  <h1 class="title-article">我的CSDN标题</h1>
  <div class="article-info-box">最新推荐文章 发布 · 7.2k 阅读 · 版权声明 CC 4.0 BY-SA</div>
  <div id="content_views"><p>第一段正文内容。</p><p>第二段正文内容。</p></div>
</div>
</body></html>
"""


def test_title_and_body_from_content_views():
    r = parse(_HTML, "https://blog.csdn.net/u/article/details/1")
    assert r["platform"] == "csdn" and r["type"] == "article"
    assert r["title"] == "我的CSDN标题"
    assert "第一段正文内容" in r["text"] and "第二段正文内容" in r["text"]


def test_body_excludes_header_boilerplate():
    # 关键回归：正文取 #content_views，不应夹页头元信息（阅读量/版权声明）
    r = parse(_HTML, "https://blog.csdn.net/u/article/details/1")
    assert "阅读" not in r["text"]
    assert "版权声明" not in r["text"]


def test_author_from_meta_fallback():
    r = parse(_HTML, "https://blog.csdn.net/u/article/details/1")
    assert r["author"] == "张三"


def test_empty_body_raises():
    with pytest.raises(RuntimeError):
        parse("<html><body><h1>只有标题</h1></body></html>", "http://x")
