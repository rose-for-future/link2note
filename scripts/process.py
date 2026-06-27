import sys, json, argparse
from scripts.router import classify
from scripts.config import load_config
from scripts.render import render
from scripts.fetchers import REGISTRY, load_all

def run(url: str, cfg: dict) -> dict:
    info = classify(url)                 # 可能抛 ValueError
    fetch = REGISTRY.get(info["platform"])
    if fetch is None:
        raise NotImplementedError(f"平台 {info['platform']} 的 fetcher 尚未实现")
    result = fetch(url, cfg)
    out = render(result, cfg)
    out["platform"] = result["platform"]
    out["title"] = result["title"]
    return out

def main():
    ap = argparse.ArgumentParser(description="信息处理：链接→文字稿+总结")
    ap.add_argument("url")
    ap.add_argument("--config", default=None)
    ap.add_argument("--keep-audio", action="store_true")
    ap.add_argument("--keep-video", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.keep_audio: cfg["keep_audio"] = True
    if args.keep_video: cfg["keep_video"] = True
    out = run(args.url, cfg)
    print(json.dumps(out, ensure_ascii=False, indent=2))

# Register all fetchers at module import time (before any test monkeypatching).
load_all()

if __name__ == "__main__":
    main()
