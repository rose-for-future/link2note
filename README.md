<div align="center">

# link2note

**丢一个链接，自动转写/识别，产出「文字稿 + 总结」进你的知识库。**

*Paste a link → local transcription + AI summary → Markdown notes in your knowledge base.*

**已支持**：抖音 · 小红书 · 播客 · B站 · 知乎 · 公众号 · GitHub
🚧 **规划中**：微博

![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-D97706?style=flat-square)
![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)
![Local & Free](https://img.shields.io/badge/转写-本地%20%26%20免费-10B981?style=flat-square)

</div>

---

## 它做什么

把一个链接丢进来，`link2note` 会自动：

1. **识别平台与类型**（视频 / 音频 / 图文 / 文章 / 代码仓库）——纯 URL 规则，无需你指定
2. **抓取内容**（需登录的复用浏览器登录态）
3. **视频/音频本地转写**成文字（Apple Silicon 走 GPU，免费）
4. **由 Claude 提炼要点**；图文笔记会**识别图片里的内容**
5. 产出两份 Markdown——**`文字稿.md`（全文，原文链接置顶）** + **`总结.md`（要点提炼）**，存进你指定的目录（如 Obsidian 知识库）

## 支持平台

| 平台 | 类型 | 说明 |
|------|------|------|
| 抖音 | 视频 | 无水印、**免 cookie** 抓取 + 文案 |
| 小红书 | 图文 | 抓正文 + 下图片，**图里的内容也识别** |
| 播客 | 音频 | 小宇宙 / 喜马拉雅 / RSS / 直接音频 |
| B站 | 视频 | 开放 API（WBI 签名）+ 字幕优先，**无需登录 / 不依赖 yt-dlp** |
| 知乎 | 视频 | zvideo 视频转写 |
| 公众号 | 文章 | 抓正文 + 作者（无需转写） |
| GitHub | 仓库 | README + 简介（去 star 等噪音） |
| 🚧 微博 | 视频 | **规划中**（代码已就绪，待真实链接验证后转正） |

## 转写后端

默认 `auto`：

- **Apple Silicon** → [`mlx-whisper`](https://pypi.org/project/mlx-whisper/) + `large-v3-turbo`，跑 Metal GPU，又快又准
- **其它平台** → [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper)（CPU 兜底）
- 可选 SenseVoice（中文最强，但依赖重）

各方案的 CPU/GPU/硬件吞吐对比见 [`docs/调研-语音转文字方案.md`](docs/调研-语音转文字方案.md)。

## 安装

```bash
git clone https://github.com/rose-for-future/link2note.git ~/.claude/skills/link2note
cd ~/.claude/skills/link2note

# 转写依赖需 arm64 原生 Python（如 python3.11/3.12）；务必加 --only-binary
python3.11 -m venv .venv && .venv/bin/pip install --only-binary=:all: -r requirements.txt

cp config.example.json config.json   # 填 notes_dir / assets_dir（你的知识库路径）
```
系统依赖：`ffmpeg`、`curl`、`gh`（GitHub）、`yt-dlp`（B站字幕，阶段2）。

## 使用

在 Claude Code 里直接贴链接即可触发；或命令行：

```bash
.venv/bin/python -m scripts.process "<链接>" [--keep-audio] [--keep-video]
```
脚本产出 `文字稿.md`，`总结.md` 由 Claude 读文字稿后写入。

## 发版前回归

```bash
.venv/bin/python -m pytest -q          # 单元测试
.venv/bin/python evals/regression.py   # 4 平台抓取层能力回归
```
详见 [`evals/README.md`](evals/README.md)。

## 致谢

各平台抓取/转写脚本改写自 [chubbyguan/chubbyskills](https://github.com/chubbyguan/chubbyskills)（MIT）。转写基于 [mlx-whisper](https://github.com/ml-explore/mlx-examples) / [faster-whisper](https://github.com/SYSTRAN/faster-whisper) / [SenseVoice](https://github.com/FunAudioLLM/SenseVoice)。

## License

MIT
