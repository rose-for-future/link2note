import json, os, copy

DEFAULTS = {
    # 成稿与素材的默认输出目录；请在 config.json 改成你自己的知识库路径（如 Obsidian 库）
    "notes_dir": os.path.expanduser("~/Documents/link2note/成稿"),
    "assets_dir": os.path.expanduser("~/Documents/link2note/素材"),
    "keep_audio": False,
    "keep_video": False,
    "save_images": True,
    "transcribe_backend": "auto",   # auto=按硬件自动选后端+模型(见 transcribe.recommend) | mlx-whisper | faster-whisper | sensevoice
    "whisper_model": "small",        # 仅显式 faster-whisper 时用：small/medium/large-v3
    "mlx_model": "mlx-community/whisper-large-v3-turbo",  # 仅显式 mlx-whisper 时用
    "xhs_cookie": "",                      # 小红书登录态，从浏览器复制；也可用环境变量 XHS_COOKIE
}

_SEARCH = [
    "./config.json",
    os.path.expanduser("~/.claude/skills/link2note/config.json"),
]

def load_config(path=None):
    cfg = copy.deepcopy(DEFAULTS)
    candidates = [path] if path else _SEARCH
    for c in candidates:
        if c and os.path.isfile(c):
            with open(c, encoding="utf-8") as f:
                user = json.load(f)
            cfg.update({k: v for k, v in user.items() if v is not None})
            break
    if not cfg["xhs_cookie"]:
        cfg["xhs_cookie"] = os.environ.get("XHS_COOKIE", "")
    return cfg
