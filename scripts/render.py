import os, shutil, datetime
from scripts.models import clean_title

def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def _existing_link(note_dir: str) -> str | None:
    """读已存在 文字稿.md 的原文链接，用于判断是否同一内容。"""
    p = os.path.join(note_dir, "文字稿.md")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.startswith("- 原文链接："):
                    return line.split("：", 1)[1].strip()
                if line.startswith("---"):
                    break
    return None


def render(result: dict, cfg: dict) -> dict:
    folder = clean_title(result["title"])
    note_dir = os.path.join(cfg["notes_dir"], folder)
    # 防数据丢：同名文件夹但来自不同链接 → 追加 (2)(3)… 不互相覆盖；同链接=重跑，正常覆盖
    i = 2
    while True:
        ex = _existing_link(note_dir)
        if ex is None or ex == result["url"]:
            break
        note_dir = os.path.join(cfg["notes_dir"], f"{folder} ({i})")
        i += 1
    os.makedirs(note_dir, exist_ok=True)

    # 决定是否需要素材目录（lazy：只在真正写入时才创建）
    keep_imgs = cfg.get("save_images", True) and result["images"]
    keep_audio = cfg.get("keep_audio") and result["media"].get("audio")
    keep_video = cfg.get("keep_video") and result["media"].get("video")
    assets_dir_path = os.path.join(cfg["assets_dir"], folder)
    archived = False  # 只要成功写入一个文件就置 True

    def _ensure_assets_dir():
        nonlocal archived
        if not archived:
            os.makedirs(assets_dir_path, exist_ok=True)

    # 复制素材
    img_md = []
    if keep_imgs:
        for i, im in enumerate(result["images"]):
            if im.get("path") and os.path.exists(im["path"]):
                orig_basename = os.path.basename(im["path"])
                dest_basename = f"{i:02d}_{orig_basename}"
                _ensure_assets_dir()
                dst = os.path.join(assets_dir_path, dest_basename)
                shutil.copy2(im["path"], dst)
                archived = True
                rel = os.path.relpath(dst, note_dir)
                img_md.append(f"![]({rel})")
            elif im.get("url"):
                img_md.append(f"![]({im['url']})")
    for kind in ("audio", "video"):
        on = cfg.get(f"keep_{kind}")
        src = result["media"].get(kind)
        if on and src and os.path.exists(src):
            _ensure_assets_dir()
            shutil.copy2(src, os.path.join(assets_dir_path, os.path.basename(src)))
            archived = True

    assets_dir = assets_dir_path if archived else None

    # 文字稿
    head = [
        f"# {result['title']}", "",
        f"- 原文链接：{result['url']}",
        f"- 平台：{result['platform']}",
        f"- 作者：{result['author']}",
        f"- 采集时间：{_now()}",
        "", "---", "",
    ]
    body = [result["text"]]
    if img_md:
        body += ["", "## 图片", ""] + img_md
    transcript_path = os.path.join(note_dir, "文字稿.md")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write("\n".join(head + body) + "\n")

    return {
        "note_dir": note_dir,
        "transcript_path": transcript_path,
        "summary_path": os.path.join(note_dir, "总结.md"),
        "assets_dir": assets_dir,
    }
