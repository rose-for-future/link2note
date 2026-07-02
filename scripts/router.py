import re
from urllib.parse import urlparse

# 按域名(host)匹配，避免子串冒充（如 xhslink.com.attacker.com 冒充小红书）
_DOMAIN_RULES = [
    (("douyin.com", "iesdouyin.com"), "douyin", "video"),
    (("xiaohongshu.com", "xhslink.com"), "xiaohongshu", "image_text"),
    (("xiaoyuzhoufm.com", "ximalaya.com"), "podcast", "audio"),
    (("bilibili.com", "b23.tv"), "bilibili", "video"),
    (("weibo.com", "weibo.cn"), "weibo", "video"),
    (("zhihu.com",), "zhihu", "article"),
    (("weixin.qq.com",), "wechat", "article"),
    (("csdn.net",), "csdn", "article"),
    (("github.com",), "github", "repo"),
]
# 兜底：非平台域名但看起来是播客/RSS/直接音频
_GENERIC = [(r"/rss|\.xml$|\.mp3$", "podcast", "audio")]

PLATFORM_TYPE = {p: t for _, p, t in _DOMAIN_RULES}


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _host_matches(host: str, domain: str) -> bool:
    # 精确等于该域名，或是其子域名（.domain 结尾）；防 domain.attacker.com 冒充
    return host == domain or host.endswith("." + domain)


def classify(url: str) -> dict:
    host = _host(url)
    if host:
        for domains, platform, ctype in _DOMAIN_RULES:
            if any(_host_matches(host, d) for d in domains):
                return {"platform": platform, "type": ctype}
    for pat, platform, ctype in _GENERIC:
        if re.search(pat, url, re.IGNORECASE):
            return {"platform": platform, "type": ctype}
    raise ValueError(f"无法识别的链接：{url}")
