"""微博视频 → ContentResult（下音频 → 转写）。"""
import tempfile
from scripts.vendor.weibo_dl import get_video_info, download_audio
from scripts.transcribe import transcribe_audio
from scripts.models import make_result
from scripts.fetchers import REGISTRY


def fetch(url, cfg):
    info = get_video_info(url)
    workdir = tempfile.mkdtemp(prefix="weibo-")
    audio_path = download_audio(url, workdir)
    text = transcribe_audio(audio_path, cfg)
    media = {"audio": audio_path if cfg.get("keep_audio") else None, "video": None}
    return make_result("weibo", "video", url, info.get("title", "微博视频"), text, media=media)


REGISTRY["weibo"] = fetch
