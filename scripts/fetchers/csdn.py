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


def fetch(url, cfg):
    req = urllib.request.Request(url, headers=_HEADERS)
    html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("h1.title-article, #articleContentId, h1")
    title = title_el.get_text(strip=True) if title_el else "CSDN文章"

    author = ""
    a_el = soup.select_one("a.follow-nickName, .nick-name, .user-name")
    if a_el:
        author = a_el.get_text(strip=True)
    else:
        meta = soup.select_one('meta[name="author"]')
        if meta:
            author = meta.get("content", "")

    body_el = soup.select_one("#content_views, article, .blog-content-box")
    content = body_el.get_text("\n", strip=True) if body_el else ""
    if not content:
        raise RuntimeError("CSDN 文章抓取失败（可能是付费/登录文章，或页面结构变动）")

    return make_result("csdn", "article", url, title, content, author=author)


REGISTRY["csdn"] = fetch
