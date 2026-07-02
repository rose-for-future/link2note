"""Douyin (抖音) fetcher — turns a Douyin link into a ContentResult.

Limitations:
- keep_video is NOT supported: the vendor (douyin_dl.download_audio) downloads
  the video, extracts audio via ffmpeg, then os.remove()s the video file.
  Intercepting that would require duplicating vendor internals, which is deferred.
- keep_audio=True preserves the extracted mp3 at its temp path.
"""

import shutil
import tempfile

from scripts.vendor.douyin_dl import extract_video_id, download_audio
from scripts.transcribe import transcribe_audio
from scripts.models import make_result
from scripts.fetchers import REGISTRY


def fetch(url: str, cfg: dict) -> dict:
    vid = extract_video_id(url)
    workdir = tempfile.mkdtemp(prefix="dyt-")
    try:
        audio_path, title = download_audio(vid, workdir)
        text = transcribe_audio(audio_path, cfg)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    media = {
        "audio": audio_path if cfg.get("keep_audio") else None,
        "video": None,  # vendor deletes video after audio extraction
    }
    return make_result("douyin", "video", url, title, text, media=media,
                       extra={"_tempdir": workdir})


REGISTRY["douyin"] = fetch
