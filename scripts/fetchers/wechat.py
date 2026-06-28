"""微信公众号文章 → ContentResult（抓正文+作者，无需转写）。依赖 beautifulsoup4。"""
from scripts.vendor.wechat_fetch import fetch_from_url
from scripts.models import make_result
from scripts.fetchers import REGISTRY


def fetch(url, cfg):
    title, author, content = fetch_from_url(url)
    if not content:
        raise RuntimeError("公众号文章抓取失败（文章可能已删除，或需先在浏览器打开过）")
    return make_result("wechat", "article", url, title or "公众号文章", content,
                       author=author or "")


REGISTRY["wechat"] = fetch
