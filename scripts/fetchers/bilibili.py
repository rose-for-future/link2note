"""B站 → ContentResult。字幕优先（有字幕免转写），无字幕才下音频转写。"""
import tempfile
from scripts.vendor.bilibili_dl import extract_bvid, get_info, try_subtitles, download_audio
from scripts.transcribe import transcribe_audio
from scripts.models import make_result
from scripts.fetchers import REGISTRY


def fetch(url, cfg):
    bvid = extract_bvid(url)
    title, author = get_info(url, bvid)
    workdir = tempfile.mkdtemp(prefix="bili-")
    audio_path = None
    sub = try_subtitles(url, workdir)          # (text, lang) | None
    if sub and sub[0]:
        text = sub[0]                          # 字幕优先
    else:
        audio_path = download_audio(url, workdir, title)
        text = transcribe_audio(audio_path, cfg)
    media = {"audio": audio_path if (audio_path and cfg.get("keep_audio")) else None, "video": None}
    return make_result("bilibili", "video", url, title, text, author=author, media=media)


REGISTRY["bilibili"] = fetch
