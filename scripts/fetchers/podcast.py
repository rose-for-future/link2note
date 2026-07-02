"""播客（小宇宙/喜马拉雅/RSS/直接音频 URL）→ ContentResult。"""
import shutil
import tempfile
from scripts.vendor.podcast_dl import download_audio
from scripts.transcribe import transcribe_audio
from scripts.models import make_result
from scripts.fetchers import REGISTRY

def fetch(url, cfg):
    workdir = tempfile.mkdtemp(prefix="pod-")
    try:
        audio_path, title = download_audio(url, workdir)
        text = transcribe_audio(audio_path, cfg)  # 走 cfg 后端（默认 auto→苹果芯片用 mlx）
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    media = {"audio": audio_path if cfg.get("keep_audio") else None, "video": None}
    return make_result("podcast", "audio", url, title, text, media=media,
                       extra={"_tempdir": workdir})

REGISTRY["podcast"] = fetch
