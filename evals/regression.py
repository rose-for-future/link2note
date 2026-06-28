#!/usr/bin/env python3
"""发版前能力回归：重跑 4 平台抓取层，与 baseline.json 对比，检测能力缺失。

只测抓取层（快、且最易随平台改版而崩），不跑耗时的完整转写。
- 硬检查（能力）：抓取成功 + 关键字段非空（标题/音频可解析/图片数/README）。任一失败 → 回归失败，退出码 1。
- 软检查（漂移）：标题/作者/图片数与基线的差异，只告警，不判失败（内容可能被作者改）。

用法：  .venv311/bin/python -m evals.regression
"""
import json, os, re, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _result(ok, fields, drift=None, err=None):
    return {"ok": ok, "fields": fields, "drift": drift or [], "err": err}


def check_douyin(url, expect):
    from scripts.vendor.douyin_dl import extract_video_id, download_audio
    vid = extract_video_id(url)
    wd = tempfile.mkdtemp(prefix="reg-dy-")
    audio, title = download_audio(vid, wd)
    audio_ok = bool(audio) and os.path.exists(audio) and os.path.getsize(audio) > 100_000
    hard = bool(title) and audio_ok
    drift = [] if expect.get("title_contains", "") in title else [f"标题不含基线关键字「{expect.get('title_contains')}」: {title!r}"]
    return _result(hard, {"标题": title[:40], "音频": "✅" if audio_ok else "❌"}, drift)


def check_podcast(url, expect):
    # 轻量：只解析页面拿 og:title + og:audio，不下载 60MB 音频
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    page = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    title_m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', page, re.I)
    audio_m = re.search(r'<meta[^>]+property=["\']og:audio["\'][^>]+content=["\'](.*?)["\']', page, re.I) \
        or re.search(r'["\'](https?://[^"\']+\.(?:m4a|mp3|wav)[^"\']*)["\']', page, re.I)
    title = (title_m.group(1).strip() if title_m else "")
    audio_ok = bool(audio_m)
    hard = bool(title) and audio_ok
    drift = [] if expect.get("title_contains", "") in title else [f"标题不含基线关键字: {title!r}"]
    return _result(hard, {"标题": title[:40], "音频URL": "✅" if audio_ok else "❌"}, drift)


def check_xiaohongshu(url, expect):
    from scripts.fetchers.xiaohongshu import fetch
    r = fetch(url, {"save_images": True, "xhs_cookie": os.environ.get("XHS_COOKIE", "")})
    n_img = len(r["images"])
    hard = bool(r["title"]) and n_img >= expect.get("min_images", 1)
    drift = []
    if expect.get("author") and r["author"] != expect["author"]:
        drift.append(f"作者变化: {r['author']!r}≠基线{expect['author']!r}")
    if expect.get("note_type") and r["extra"].get("note_type") != expect["note_type"]:
        drift.append(f"类型变化: {r['extra'].get('note_type')}")
    if expect.get("title_contains", "") not in r["title"]:
        drift.append(f"标题不含基线关键字: {r['title']!r}")
    return _result(hard, {"标题": r["title"][:30], "作者": r["author"], "图片数": n_img}, drift)


def check_github(url, expect):
    from scripts.fetchers.github import fetch
    r = fetch(url, {})
    readme_ok = len(r["text"]) >= expect.get("readme_min_len", 1)
    no_star = "stargazers" not in r["text"].lower() and "star" not in r["title"].lower()
    hard = bool(r["title"]) and readme_ok and (no_star if expect.get("no_star_noise") else True)
    drift = [] if r["title"] == expect.get("title", r["title"]) else [f"标题变化: {r['title']!r}"]
    return _result(hard, {"仓库": r["title"], "正文长度": len(r["text"]), "无star噪音": "✅" if no_star else "❌"}, drift)


def check_wechat(url, expect):
    from scripts.fetchers.wechat import fetch
    r = fetch(url, {})
    hard = bool(r["title"]) and len(r["text"]) >= expect.get("min_text_len", 200)
    drift = []
    if expect.get("author") and r["author"] != expect["author"]:
        drift.append(f"作者变化: {r['author']!r}≠基线{expect['author']!r}")
    if expect.get("title_contains", "") not in r["title"]:
        drift.append(f"标题不含基线关键字: {r['title']!r}")
    return _result(hard, {"标题": r["title"][:30], "作者": r["author"], "正文字数": len(r["text"])}, drift)


def check_bilibili(url, expect):
    # 轻量：只验开放 API 拿信息(标题/cid)，不下载转写
    from scripts.bili_api import extract_bvid, get_info
    info = get_info(extract_bvid(url))
    hard = bool(info["title"]) and bool(info["cid"])
    drift = [] if expect.get("title_contains", "") in info["title"] else [f"标题不含基线关键字: {info['title']!r}"]
    return _result(hard, {"标题": info["title"][:24], "UP": info["author"], "cid": info["cid"]}, drift)


CHECKS = {
    "douyin": check_douyin, "podcast": check_podcast,
    "xiaohongshu": check_xiaohongshu, "github": check_github,
    "wechat": check_wechat, "bilibili": check_bilibili,
}


def main():
    with open(os.path.join(ROOT, "evals", "baseline.json"), encoding="utf-8") as f:
        baseline = json.load(f)
    print("=" * 64)
    print("能力回归测试（抓取层）")
    print("=" * 64)
    failed, drifted = [], []
    for case in baseline["cases"]:
        plat = case["platform"]
        res = None
        for attempt in (1, 2):   # 失败重试一次，避免网络抖动误报为能力退化
            try:
                res = CHECKS[plat](case["url"], case.get("expect", {}))
                if res["ok"]:
                    break
            except Exception as e:
                res = _result(False, {}, err=f"{type(e).__name__}: {e}")
        verdict = "PASS ✅" if res["ok"] else "FAIL ❌"
        if not res["ok"]:
            failed.append(plat)
        if res["drift"]:
            drifted.append(plat)
        fields = "  ".join(f"{k}={v}" for k, v in res["fields"].items())
        print(f"\n[{plat:12}] {verdict}")
        if fields:
            print(f"  {fields}")
        if res["err"]:
            print(f"  ⚠ 错误: {res['err']}")
        for d in res["drift"]:
            print(f"  ⚠ 漂移: {d}")
    print("\n" + "=" * 64)
    print(f"结果: {len(baseline['cases']) - len(failed)}/{len(baseline['cases'])} 通过"
          + (f" | 能力回归: {', '.join(failed)}" if failed else " | 无能力缺失")
          + (f" | 内容漂移: {', '.join(drifted)}" if drifted else ""))
    print("=" * 64)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
