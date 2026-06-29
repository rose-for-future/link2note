import re

# (正则, 平台, 类型) —— 顺序匹配，先到先得
_RULES = [
    (r"(v\.douyin\.com|douyin\.com/video)", "douyin", "video"),
    (r"(xiaohongshu\.com|xhslink\.com)", "xiaohongshu", "image_text"),
    (r"(xiaoyuzhoufm\.com|ximalaya\.com)", "podcast", "audio"),
    (r"(bilibili\.com|b23\.tv)", "bilibili", "video"),
    (r"(weibo\.com|weibo\.cn)", "weibo", "video"),
    (r"(zhihu\.com)", "zhihu", "article"),
    (r"(mp\.weixin\.qq\.com)", "wechat", "article"),
    (r"(csdn\.net)", "csdn", "article"),
    (r"(github\.com)", "github", "repo"),
    (r"(/rss|\.xml$|\.mp3$)", "podcast", "audio"),
]

PLATFORM_TYPE = {p: t for _, p, t in _RULES}

def classify(url: str) -> dict:
    for pat, platform, ctype in _RULES:
        if re.search(pat, url, re.IGNORECASE):
            return {"platform": platform, "type": ctype}
    raise ValueError(f"无法识别的链接：{url}")
