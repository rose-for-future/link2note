---
name: 信息处理
description: 给一个链接（抖音/小红书/播客/B站/微博/知乎/公众号/GitHub）就自动抓取内容、视频音频本地转写、识别图片、由我做要点总结，产出「文字稿.md + 总结.md」到你的 Obsidian 知识库。当用户粘贴上述平台链接并希望提取/转写/总结/存档内容时使用。
---

# 信息处理

## 何时用

用户给出抖音/小红书/播客/B站/微博/知乎/公众号/GitHub 链接，想要：转文字、提炼要点、存进知识库。

## 流程

1. **确认 `config.json` 存在**。若不存在，从 `config.example.json` 复制并提示用户填写 `notes_dir`（Obsidian 知识库路径）和 `assets_dir`（素材存放路径）。

2. **运行脚本**：
   ```bash
   python -m scripts.process "<链接>"
   ```
   可选参数：`--keep-audio`（保留音频文件）、`--keep-video`（保留视频文件）。
   - 脚本输出 JSON，含 `transcript_path`（文字稿.md 路径）、`summary_path`（总结.md 路径）、`platform`、`title`。
   - 下载/转写等重活都在脚本里完成，超长文字稿不进 Claude 上下文。

3. **图文笔记补全文字稿**：若脚本返回了 `assets_dir`（小红书等图文笔记），查看目录里的图片——这类笔记正文常只有话题标签，**真正内容在图里**。把图中文字（OCR）还原后写进 `文字稿.md` 的正文，让原文完整可搜。

4. **写总结**：读取 `transcript_path`（文字稿.md）正文，写一份「一句话 + 要点提炼 + 需要注意的内容」，存到 `summary_path`（总结.md）。
   - **总结里不写元信息**（原文链接/平台/作者/说明）——这些只放在 `文字稿.md` 顶部，总结只留正文。
   - 图中值得注意的信息也提炼进总结。

5. **回报用户**：给出两份文件路径 + 3–5 条要点速览。

## 总结.md 模板

> 注意：总结不重复写元信息（链接/平台/作者），它们在文字稿顶部。

```markdown
# <标题> · 总结

## 一句话
...

## 要点
- ...

## 需要注意的内容
- ...
```

## 已知限制

- **小红书**：未登录约 60% 成功率；失败时提示用户在 `config.json` 填 `xhs_cookie`（浏览器 F12 → Network → 任意请求 → 复制 Cookie 头的值）。
- **抖音 keep_video**：暂未支持（vendor 抽完音频后即删视频）；需要保留视频时须单独增强。
- **转写后端**：默认 `auto`——Apple Silicon 用 **mlx-whisper + large-v3-turbo**（跑 GPU，快且中文准），其它平台回退 **faster-whisper**。详见 `docs/superpowers/decisions/2026-06-28-转写后端选型.md` 与 `docs/调研-语音转文字方案.md`。
- **首次转写**：会下载模型（mlx turbo ~1.6GB），请在网络良好时操作；之后缓存复用。
- **Python 版本**：转写依赖需 **arm64 原生** Python（如 `python3.11`/`python3.12`）；系统 Python 3.14 与 x86_64/Rosetta 环境装不上。安装务必带 `pip install --only-binary=:all:`，避免源码编译失败。GitHub/小红书图文等纯抓取无此限制。
- **小红书图文**：正文常仅含标签，真实内容在图片里——按流程第 3 步把图片 OCR 进文字稿。
