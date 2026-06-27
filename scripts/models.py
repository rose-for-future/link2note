import re

def clean_title(name: str) -> str:
    s = re.sub(r'[/\\:*?"<>|]', "", name or "")
    s = re.sub(r"\s+", " ", s).strip()
    s = s[:80]
    return s or "未命名"

def make_result(platform, ctype, url, title, text, *,
                author="", images=None, media=None, extra=None) -> dict:
    return {
        "platform": platform, "type": ctype, "url": url,
        "title": title, "author": author, "text": text,
        "images": images or [], "media": media or {}, "extra": extra or {},
    }
