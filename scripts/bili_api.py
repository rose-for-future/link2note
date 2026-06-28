"""B站开放 API 抓取（WBI 签名）。无需 yt-dlp、无需登录，公开视频即可用。

比 yt-dlp 更稳：不受 yt-dlp 版本/B站网页端反爬(412)影响，纯标准库 + curl + ffmpeg。
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_HDR = {"User-Agent": _UA, "Referer": "https://www.bilibili.com/"}
# WBI mixin 置换表（B站固定）
_TAB = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
        26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36,
        20, 34, 44, 52]


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=_HDR)
    return json.load(urllib.request.urlopen(req, timeout=25))


def extract_bvid(url: str) -> str:
    m = re.search(r"(BV[0-9A-Za-z]+)", url)
    if not m:
        raise ValueError(f"无法从链接提取 BV 号：{url}")
    return m.group(1)


def _mixin_key() -> str:
    nav = _get("https://api.bilibili.com/x/web-interface/nav")["data"]["wbi_img"]
    raw = (nav["img_url"].rsplit("/", 1)[-1].split(".")[0]
           + nav["sub_url"].rsplit("/", 1)[-1].split(".")[0])
    return "".join(raw[i] for i in _TAB)[:32]


def _sign(params: dict, mixin: str) -> str:
    params["wts"] = int(time.time())
    q = urllib.parse.urlencode(sorted(params.items()))
    params["w_rid"] = hashlib.md5((q + mixin).encode()).hexdigest()
    return urllib.parse.urlencode(params)


def get_info(bvid: str) -> dict:
    d = _get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")["data"]
    return {"title": d["title"], "author": d["owner"]["name"], "cid": d["cid"], "bvid": bvid}


def get_subtitle(bvid: str, cid: int) -> str | None:
    """字幕优先：有官方/AI字幕则返回纯文字，否则 None。"""
    try:
        q = _sign({"bvid": bvid, "cid": cid}, _mixin_key())
        d = _get(f"https://api.bilibili.com/x/player/wbi/v2?{q}")
        subs = d.get("data", {}).get("subtitle", {}).get("subtitles", [])
        if not subs:
            return None
        url = subs[0]["subtitle_url"]
        if url.startswith("//"):
            url = "https:" + url
        body = _get(url).get("body", [])
        text = "\n".join(x.get("content", "") for x in body).strip()
        return text or None
    except Exception:
        return None


def download_audio(bvid: str, cid: int, output_dir: str) -> str:
    """下 DASH 音频流（m4s）。返回本地路径。"""
    q = _sign({"bvid": bvid, "cid": cid, "qn": 64, "fnval": 16, "fourk": 1}, _mixin_key())
    d = _get(f"https://api.bilibili.com/x/player/wbi/playurl?{q}")
    au = d["data"]["dash"]["audio"][0]["baseUrl"]
    path = os.path.join(output_dir or tempfile.mkdtemp(prefix="bili-"), f"{bvid}.m4s")
    subprocess.run(["curl", "-s", "-L", "-o", path,
                    "-H", f"User-Agent: {_UA}", "-H", "Referer: https://www.bilibili.com/", au],
                   timeout=300, check=True)
    return path
