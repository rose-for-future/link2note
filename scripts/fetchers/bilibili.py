"""B站 → ContentResult。走开放 API(WBI签名)，不依赖 yt-dlp、无需登录。
字幕优先（有字幕免转写），无字幕才下音频转写。"""
import tempfile
from scripts.bili_api import extract_bvid, get_info, get_subtitle, download_audio
from scripts.transcribe import transcribe_audio
from scripts.models import make_result
from scripts.fetchers import REGISTRY


def fetch(url, cfg):
    bvid = extract_bvid(url)
    info = get_info(bvid)
    audio_path = None
    text = get_subtitle(bvid, info["cid"])      # 字幕优先
    if not text:
        workdir = tempfile.mkdtemp(prefix="bili-")
        audio_path = download_audio(bvid, info["cid"], workdir)
        text = transcribe_audio(audio_path, cfg)
    media = {"audio": audio_path if (audio_path and cfg.get("keep_audio")) else None, "video": None}
    return make_result("bilibili", "video", url, info["title"], text, author=info["author"], media=media)


REGISTRY["bilibili"] = fetch
