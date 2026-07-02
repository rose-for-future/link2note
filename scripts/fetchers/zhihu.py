"""知乎视频（zvideo）→ ContentResult（下音频 → 转写）。
注意：仅支持知乎视频；纯文字回答/专栏文章暂不支持。"""
import shutil
import tempfile
from scripts.vendor.zhihu_dl import get_video_info, download_audio
from scripts.transcribe import transcribe_audio
from scripts.models import make_result
from scripts.fetchers import REGISTRY


def fetch(url, cfg):
    info = get_video_info(url)
    workdir = tempfile.mkdtemp(prefix="zhihu-")
    try:
        audio_path = download_audio(url, workdir)
        text = transcribe_audio(audio_path, cfg)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    media = {"audio": audio_path if cfg.get("keep_audio") else None, "video": None}
    return make_result("zhihu", "video", url, info.get("title", "知乎视频"), text,
                       media=media, extra={"_tempdir": workdir})


REGISTRY["zhihu"] = fetch
