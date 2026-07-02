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


def _data(resp: dict, what: str) -> dict:
    """校验 B站响应：code 非 0 或 data 为空时给可读报错，而不是裸 TypeError/KeyError。"""
    if not isinstance(resp, dict) or resp.get("code") not in (0, None) or resp.get("data") is None:
        msg = (resp or {}).get("message") or "视频不可用（可能已删除/地区限制/需登录）"
        raise RuntimeError(f"B站{what}失败：{msg}")
    return resp["data"]


def _resolve_redirect(url: str) -> str:
    """跟随 302 拿最终 URL（b23.tv 短链用）。"""
    try:
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{url_effective}",
                            "-L", "-H", f"User-Agent: {_UA}", url],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or url
    except Exception:
        return url


def extract_bvid(url: str) -> str:
    if "b23.tv" in url:                       # 短链先跟随重定向拿到 BV 号
        url = _resolve_redirect(url)
    m = re.search(r"(BV[0-9A-Za-z]+)", url)
    if not m:
        raise ValueError(f"无法从链接提取 BV 号：{url}")
    return m.group(1)


def extract_page(url: str) -> int:
    """多 P 视频的分 P 号，默认 1。"""
    m = re.search(r"[?&]p=(\d+)", url)
    return int(m.group(1)) if m else 1


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


def get_info(bvid: str, p: int = 1) -> dict:
    d = _data(_get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"), "取信息")
    pages = d.get("pages") or []
    cid = d["cid"]
    title = d["title"]
    if p > 1 and len(pages) >= p:             # 多 P：取对应分 P 的 cid + 分 P 标题
        cid = pages[p - 1]["cid"]
        part = (pages[p - 1].get("part") or "").strip()
        title = f"{title} - P{p}" + (f" {part}" if part else "")
    return {"title": title, "author": d["owner"]["name"], "cid": cid, "bvid": bvid, "p": p}


def get_subtitle(bvid: str, cid: int) -> str | None:
    """字幕优先：有官方/AI字幕则返回纯文字（优先简体中文），否则 None。"""
    try:
        q = _sign({"bvid": bvid, "cid": cid}, _mixin_key())
        d = _get(f"https://api.bilibili.com/x/player/wbi/v2?{q}")
        subs = d.get("data", {}).get("subtitle", {}).get("subtitles", [])
        if not subs:
            return None
        # 优先中文字幕，避免多语言时误取英文
        sub = next((s for s in subs if "zh" in (s.get("lan") or "").lower()), subs[0])
        url = sub["subtitle_url"]
        if url.startswith("//"):
            url = "https:" + url
        body = _get(url).get("body", [])
        text = "\n".join(x.get("content", "") for x in body).strip()
        return text or None
    except Exception:
        return None


def download_audio(bvid: str, cid: int, output_dir: str) -> str:
    """下 DASH 音频流（m4s）。返回本地路径。无 DASH 时给可读报错。"""
    q = _sign({"bvid": bvid, "cid": cid, "qn": 64, "fnval": 16, "fourk": 1}, _mixin_key())
    d = _data(_get(f"https://api.bilibili.com/x/player/wbi/playurl?{q}"), "取音频流")
    dash = d.get("dash")
    if not dash or not dash.get("audio"):
        raise RuntimeError("B站该视频无 DASH 音频流（老视频/互动视频/大会员专享等），暂不支持")
    au = dash["audio"][0]["baseUrl"]
    path = os.path.join(output_dir or tempfile.mkdtemp(prefix="bili-"), f"{bvid}.m4s")
    subprocess.run(["curl", "-s", "-L", "-o", path,
                    "-H", f"User-Agent: {_UA}", "-H", "Referer: https://www.bilibili.com/", au],
                   timeout=300, check=True)
    return path
