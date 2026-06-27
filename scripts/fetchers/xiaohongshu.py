"""小红书图文笔记 → ContentResult。"""
import os
import tempfile

from scripts.vendor import xhs_fetch as V
from scripts.models import make_result
from scripts.fetchers import REGISTRY


def fetch(url, cfg):
    cookie = cfg.get("xhs_cookie", "")
    html, final_url = V.http_get(url, cookie=cookie)
    state = V.extract_initial_state(html)
    note = V.find_note(state) if state else None
    if note:
        data = V.parse_from_state(note)
    else:
        data = V.parse_from_meta(html)
        if not data:
            raise RuntimeError("小红书解析失败：请在 config 设置 xhs_cookie 或手动复制正文")
    title = V.compute_title(data)
    images = []
    if cfg.get("save_images", True) and data.get("images"):
        workdir = tempfile.mkdtemp(prefix="xhs-")
        refs = V.download_images(data["images"], workdir, "xhs", cookie)
        for kind, val in refs:
            if kind == "local":
                images.append({"path": os.path.join(workdir, val), "url": ""})
            else:
                images.append({"path": None, "url": val})
    extra = {"tags": data.get("tags", []), "note_type": data.get("note_type")}
    text = data.get("desc", "")
    if data.get("note_type") == "video" and data.get("video_url"):
        extra["video_url"] = data["video_url"]
        try:
            transcript = V.transcribe_video(data["video_url"], cookie)
            if transcript:
                text = transcript
        except Exception:
            pass
    return make_result("xiaohongshu", "image_text", final_url, title,
                       text, author=data.get("author", ""),
                       images=images, extra=extra)


REGISTRY["xiaohongshu"] = fetch
