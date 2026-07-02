"""B站 → ContentResult。走开放 API(WBI签名)，不依赖 yt-dlp、无需登录。
字幕优先（有字幕免转写），无字幕才下音频转写。"""
import shutil
import tempfile
from scripts.bili_api import extract_bvid, extract_page, get_info, get_subtitle, download_audio
from scripts.transcribe import transcribe_audio
from scripts.models import make_result
from scripts.fetchers import REGISTRY


def fetch(url, cfg):
    bvid = extract_bvid(url)               # 支持 b23.tv 短链（内部跟随重定向）
    p = extract_page(url)                  # 多 P 视频取对应分 P
    info = get_info(bvid, p)
    text = get_subtitle(bvid, info["cid"])      # 字幕优先
    if text:
        return make_result("bilibili", "video", url, info["title"], text, author=info["author"])
    workdir = tempfile.mkdtemp(prefix="bili-")
    try:
        audio_path = download_audio(bvid, info["cid"], workdir)
        text = transcribe_audio(audio_path, cfg)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    media = {"audio": audio_path if cfg.get("keep_audio") else None, "video": None}
    return make_result("bilibili", "video", url, info["title"], text, author=info["author"],
                       media=media, extra={"_tempdir": workdir})


REGISTRY["bilibili"] = fetch
