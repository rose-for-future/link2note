import os, sys, json, shutil, tempfile, argparse
from scripts.router import classify
from scripts.config import load_config
from scripts.render import render
from scripts.fetchers import REGISTRY, load_all

_INDEX = ".link2note_index.json"   # notes_dir 下：url -> {dir,platform,title}，用于幂等跳过


def _load_index(cfg):
    p = os.path.join(cfg["notes_dir"], _INDEX)
    if os.path.isfile(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_index(cfg, idx):
    try:
        os.makedirs(cfg["notes_dir"], exist_ok=True)
        # 原子写：写临时文件再 os.replace，避免崩溃留半截 JSON 导致全量索引丢失
        fd, tmp = tempfile.mkstemp(dir=cfg["notes_dir"], suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
        os.replace(tmp, os.path.join(cfg["notes_dir"], _INDEX))
    except Exception:
        pass


def run(url: str, cfg: dict) -> dict:
    # B站/微博/知乎(yt-dlp)登录态：cookies_file(优先) 或 cookies_browser，供 vendor 读取
    if cfg.get("cookies_file"):
        os.environ["YTDLP_COOKIES_FILE"] = cfg["cookies_file"]
    if cfg.get("cookies_browser"):
        os.environ["YTDLP_COOKIES_BROWSER"] = cfg["cookies_browser"]

    # 幂等：同链接处理过且文件还在 → 跳过重抓/重转写（--force 可绕过）
    idx = _load_index(cfg)
    if not cfg.get("force") and url in idx:
        rec = idx[url]
        nd = rec.get("dir", "")
        tp = os.path.join(nd, "文字稿.md")
        if nd and os.path.exists(tp):
            return {"note_dir": nd, "transcript_path": tp,
                    "summary_path": os.path.join(nd, "总结.md"), "assets_dir": None,
                    "platform": rec.get("platform", ""), "title": rec.get("title", ""),
                    "skipped": True}

    info = classify(url)                 # 可能抛 ValueError
    fetch = REGISTRY.get(info["platform"])
    if fetch is None:
        raise NotImplementedError(f"平台 {info['platform']} 的 fetcher 尚未实现")
    result = fetch(url, cfg)
    try:
        out = render(result, cfg)
    finally:
        # 清理 fetcher 登记的临时下载目录（render 已把要留的素材拷走）
        td = (result.get("extra") or {}).get("_tempdir")
        if td:
            shutil.rmtree(td, ignore_errors=True)
    out["platform"] = result["platform"]
    out["title"] = result["title"]
    out["skipped"] = False

    rec = {"dir": out["note_dir"], "platform": out["platform"], "title": out["title"]}
    idx[url] = rec
    # 短链/长链都能命中：也用 fetcher 解析后的规范原文链接存一份（如小红书 xhslink→长链）
    if result.get("url") and result["url"] != url:
        idx[result["url"]] = rec
    _save_index(cfg, idx)
    return out


def main():
    ap = argparse.ArgumentParser(description="信息处理：链接→文字稿+总结")
    ap.add_argument("url")
    ap.add_argument("--config", default=None)
    ap.add_argument("--keep-audio", action="store_true")
    ap.add_argument("--keep-video", action="store_true")
    ap.add_argument("--force", action="store_true", help="忽略幂等缓存，强制重新处理")
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.keep_audio: cfg["keep_audio"] = True
    if args.keep_video: cfg["keep_video"] = True
    if args.force: cfg["force"] = True
    try:
        out = run(args.url, cfg)
    except Exception as e:
        # 错误友好化：stderr 出可读原因 + stdout 出错误 JSON，调用方能解析
        msg = f"{type(e).__name__}: {e}"
        print(f"❌ 处理失败：{msg}", file=sys.stderr)
        print(json.dumps({"error": msg, "url": args.url}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False, indent=2))


# Register all fetchers at module import time (before any test monkeypatching).
load_all()

if __name__ == "__main__":
    main()
