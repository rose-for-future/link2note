"""CSDN 博客文章 → ContentResult（抓正文+标题+作者，无需转写/登录）。依赖 beautifulsoup4。"""
import urllib.request
from scripts.models import make_result
from scripts.fetchers import REGISTRY

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.csdn.net/",
}


def parse(html: str, url: str) -> dict:
    """纯函数：HTML → ContentResult（可单测，不碰网络）。"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    def first(selectors):
        for sel in selectors:   # 按优先级逐个试（select_one(逗号) 取的是文档序最前，不可靠）
            el = soup.select_one(sel)
            if el:
                return el
        return None

    title_el = first(["h1.title-article", "#articleContentId", "h1"])
    title = title_el.get_text(strip=True) if title_el else "CSDN文章"

    author = ""
    a_el = first(["a.follow-nickName", ".profile-intro-name-boxTop a", ".bar-content .nick-name"])
    if a_el:
        author = a_el.get_text(strip=True)
    else:
        meta = first(['meta[property="og:article:author"]', 'meta[name="author"]'])
        if meta:
            author = meta.get("content", "")

    body_el = first(["#content_views", "article", ".blog-content-box"])
    content = body_el.get_text("\n", strip=True) if body_el else ""
    if not content:
        raise RuntimeError("CSDN 文章抓取失败（可能是付费/登录文章，或页面结构变动）")

    return make_result("csdn", "article", url, title, content, author=author)


def fetch(url, cfg):
    req = urllib.request.Request(url, headers=_HEADERS)
    html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    return parse(html, url)


REGISTRY["csdn"] = fetch
