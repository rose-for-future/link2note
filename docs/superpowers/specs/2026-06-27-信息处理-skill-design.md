# 信息处理 Skill 设计文档

> 日期：2026-06-27
> 形态：Claude Code Skill（逻辑全部在 `scripts/`，留 CLI/APP 抽取后路）

## 1. 目标

给一个链接（**抖音 / 小红书 / 播客 / B站 / 微博 / 知乎 / 公众号 / GitHub**，可扩展），自动：

1. 识别平台与内容类型（视频 / 音频 / 图文 / 文章 / 代码仓库）
2. 抓取内容（需登录的复用浏览器登录态）
3. 视频/音频转成文字（**字幕优先，没字幕才本地 SenseVoice 转写**）
4. 由 Claude 做要点总结；图片由 Claude 识别"需要注意的内容"
5. 产出两份 Markdown（**全文文字稿 + 总结稿**），素材按策略留底（见 §7.2）

## 2. 形态决策（已与用户确认）

- **做成 Claude Code Skill**，不是独立产品、不是 Agent。
- **设计铁律**：所有真实逻辑（路由、抓取、转写、写文件）放进 `scripts/`，`SKILL.md` 只负责"何时调哪个脚本"。
  - 好处：① 现在能在 Claude Code 里用；② 重活在脚本里跑，超长文字稿不进 Claude 上下文；③ 哪天想变 CLI / APP，给 `scripts/` 包个 `main()` 即可，引擎零改动。
- **分析由谁做**：当前由 Claude 做（总结 + 图片识别）。`analyze` 步骤设计成可插拔，以后可一行切到 DeepSeek / Qwen-VL 省成本。

## 3. 运行与依赖约束（已确认）

- **全本地、零付费**为底线：转写用本地开源 SenseVoice，不依赖付费云 ASR。
- 登录态：复用浏览器登录态——**抖音无需 cookie**（iesdouyin 方案）；**小红书用 `XHS_COOKIE`**（从浏览器复制）；播客无需登录。符合"浏览器登录了就能访问"。
- 平台抓取**优先复用现成开源工具**（见 §8），不自己造爬虫。

## 4. 整体架构与数据流

```
Claude 收到链接（支持一次多个）
        │
   ┌────▼─────┐
   │ router   │  纯 URL 规则匹配（免费可靠，不动用 LLM）
   └────┬─────┘  → {平台, 内容类型, 处理器}
        │
   ┌────┴───────────────┬──────────────┬─────────────┐
   ▼                    ▼              ▼             ▼
 抖音 fetcher       小红书 fetcher   播客 fetcher   github fetcher
 无水印视频+文案     图文+图片         音频          README+简介
   │                    │              │             │
 字幕/文案优先          │           字幕优先          │
   │ 没有→抽音频         │              │ 没有→        │
   ▼                    │              ▼              │
 SenseVoice 转写        │          SenseVoice 转写     │
   │                    │              │              │
   └──────────┬─────────┴──────────────┴──────────────┘
              ▼
   ┌────────────────────┐
   │ analyze（可插拔）    │  文字→Claude 总结；图片→Claude 识别注意点
   └─────────┬──────────┘
             ▼
   ┌────────────────────┐
   │ render → 写两份 MD   │
   └─────────┬──────────┘
             ▼
   成稿目录 + 原始素材目录（两个不同路径）
```

## 5. 模块边界（每个可独立测试）

| 模块 | 输入 | 输出 | 依赖 |
|------|------|------|------|
| `router` | URL | `{platform, type, handler}` | 无（正则） |
| `fetchers/douyin` | URL+cookie | 视频/音频文件 + 文案 + 元数据 | yt-dlp / douyin 工具 |
| `fetchers/xhs` | URL+cookie | 图片[] + 正文 + 元数据 | XHS-Downloader 等 |
| `fetchers/podcast` | URL | 音频文件 + 字幕(若有) + 元数据 | yt-dlp |
| `fetchers/github` | URL | README + 仓库简介（**不要 star 数等噪音**） | GitHub API / gh |
| `transcribe` | 音频文件 | 文字 | SenseVoice（本地） |
| `analyze` | 文字 / 图片 | 总结要点 / 图片注意点 | Claude（可换） |
| `render` | 以上全部 | 两份 MD + 落盘 | 无 |
| `config` | — | 路径、LLM 后端、模型大小、cookie 来源 | 无 |

加一个新平台 = `fetchers/` 下加一个文件 + `router` 注册一条规则，其它不动。

## 6. 转写策略（关键省时点）

1. **字幕/文案优先**：fetcher 能直接拿到字幕或创作者文案时，直接用 → 免转写、秒出、免 GPU。
2. **没有才转写**：抽音频（ffmpeg）→ 本地 **SenseVoice-Small（~900MB）** 转写。中文质量对标云端，完全本地免费。
3. Apple Silicon 上可选 mlx 后端提速（同权重，跑得快），通过 config 切换。

## 7. 输出规格（已确认，按用户给定路径）

**成稿目录**（每条内容一个独立文件夹，内含两份稿）：
```
<你的Obsidian库>/📚知识库/信息处理/
└── <标题>/
    ├── 文字稿.md      # 顶部：原文链接 + 信息源元数据；下面：全文文字稿（含值得放的图片引用）
    └── 总结.md        # 要点总结 / 需要注意的内容
```

**原始素材目录**（下载的视频/音频/图片）：
```
<你的Obsidian库>/⚙系统/素材/信息收集原文件/
└── <标题>/
    ├── video.mp4 / audio.mp3
    └── img_01.jpg, img_02.jpg ...
```

**`文字稿.md` 结构：**
```markdown
# <标题>

- 原文链接：<URL>
- 平台：抖音 / 小红书 / 播客 / GitHub
- 采集时间：<YYYY-MM-DD HH:mm>
- 原始素材：[[../../../⚙系统/素材/信息收集原文件/<标题>/]]

---

<全文文字稿 / 图文正文。值得注意的图片用 markdown 图片链接指向素材目录>
```

**`总结.md` 结构：**
```markdown
# <标题> · 总结

- 原文链接：<URL>

## 要点
- ...

## 需要注意的内容
- （图片里/正文里值得我留意的点）
```

> 路径全部走 `config`，使用者用之前自行设定，不写死在脚本里（当前默认值即上面两个路径）。

### 7.1 文件夹命名

- 用平台原标题（视频名 / 小红书笔记名 / 文章名），复用 chubbyskills 的 `clean_title` 清洗非法字符（`/ : * ? " < > |`）、截断超长。
- 用户后续可自行重命名文件夹，不影响内容。

### 7.2 素材保存策略（已确认）

| 素材 | 默认 | 开关 | 说明 |
|------|------|------|------|
| **原文链接** | ✅ 永远留（文字稿顶部） | — | "回头去看"靠它 |
| **小红书/图文图片** | ✅ 默认存到素材目录 | `--no-images` 关 | 小、常是内容本体，删帖也不丢 |
| **音频** | ❌ 默认不存 | `--keep-audio` 开 | 防 iCloud 膨胀；想给某条留底再开 |
| **视频原片** | ❌ 默认不存 | `--keep-video` 开 | 同上，视频更大 |

> 风险提醒：素材目录在 iCloud 同步的 Obsidian 库内。若常开 `--keep-video`，建议把素材目录挪出 iCloud 同步范围，避免撑爆同步。
> chubbyskills 原行为即"转写后丢弃音视频、只留链接 + 图片"，本策略在此基础上加了可选的音视频留底开关。

## 8. 复用方案（已精读 chubbyskills 源码后确定）

**决策：以 [chubbyguan/chubbyskills](https://github.com/chubbyguan/chubbyskills)（MIT）为基础搬+改写，新建单个"信息处理"skill。搬用其抖音/小红书/播客/B站/微博/知乎/公众号各平台脚本，统一到一个 router 入口，再补缺失的 4 块。**（用户确认 B站/微博/知乎/公众号都要用）

### 8.1 直接搬用（核心脏活已验证）

| 来源 | 搬什么 | 关键点 |
|------|--------|--------|
| `douyin-transcribe/scripts/download_douyin_audio.py` | 抖音下载 | **走 `iesdouyin.com/share/video/<id>` + 手机 UA 解析 `_ROUTER_DATA`，无需 cookie/yt-dlp，直接拿无水印视频地址 + 创作者文案**。彻底绕开抖音 fresh-cookies 坑 |
| `douyin-transcribe/scripts/transcribe.py` | SenseVoice 转写 | `iic/SenseVoiceSmall`，CPU 推理，`language="zh"` |
| `xiaohongshu-ingest/scripts/fetch_note.py` | 小红书图文 | 解析 `__INITIAL_STATE__`，**零第三方库**，三层降级兜底（JSON→og 标签→提示手动）；图片下载；登录态走 `XHS_COOKIE` 环境变量（从浏览器复制） |
| `podcast-transcribe/scripts/{transcribe,batch_transcribe}.py` | 播客 | 小宇宙/喜马拉雅/RSS/直接音频 URL，抓 `og:audio` → faster-whisper |
| `bilibili-transcribe/scripts/*` | B站 | **字幕优先**（yt-dlp 抓 vtt），无字幕才转写 |
| `weibo-transcribe/scripts/*` | 微博 | 微博视频转录 |
| `zhihu-transcribe/scripts/*` | 知乎 | 知乎视频/文章 |
| `wechat-article-ingest/scripts/*` | 公众号 | 文章正文+图片（依赖 beautifulsoup4/markitdown） |

### 8.2 GitHub / 转写补充

| 平台 | 用什么 |
|------|--------|
| GitHub | `gh` CLI / GitHub API，只取 README + 仓库简介（**不要 star 等噪音**） |
| 备选转写 | faster-whisper / mlx-whisper（Apple Silicon 提速），通过 config 切 |

### 8.3 需自建/改造的 4 块（chubbyskills 没有）

1. **统一 router**：URL 正则 → 平台 + 类型 → 调对应脚本（它是 13 个独立 skill，无统一入口）。
2. **双稿输出**：它是单文件、链接埋在 frontmatter；要改成 `文字稿.md`（原文链接置顶）+ `总结.md` 两份。
3. **原始素材另存**：它只存图片（`.assets/`）、音视频转完即丢；要加 media 归档到独立素材目录。
4. **Claude 总结**：它用 DeepSeek API；改成**脚本只产文字稿，由 Claude（调用方）读稿写 `总结.md`**——更简单，无需任何 API key，契合"目前由你做分析"。

> 风险提示（来自源码）：小红书未登录约 60% 成功率，需提示设 `XHS_COOKIE`；视频转写依赖 `funasr/modelscope/torch/torchaudio` 约 2–3GB，首次安装较慢；均为一次性成本。

## 9. 配置（`config`）

使用前可设定：
- `output.notes_dir`：成稿目录（默认上面 §7 的知识库路径）
- `output.assets_dir`：原始素材目录（默认上面 §7 的素材路径）
- `transcribe.backend`：`sensevoice`（默认）/ `mlx-whisper` / `faster-whisper`
- `transcribe.model_size`：默认 SenseVoice-Small
- `analyze.backend`：`claude`（默认）/ 预留 `deepseek` / `qwen-vl`
- `XHS_COOKIE`：小红书登录态（从浏览器复制；抖音/播客无需 cookie）

## 10. 错误处理

- **小红书未登录/风控**（约 60% 成功率）：三层降级仍失败时，提示设 `XHS_COOKIE` 或手动复制正文，不静默失败。
- **抖音**：无 cookie 方案；若 `_ROUTER_DATA` 解析失败（页面结构变动），报告并保留链接。
- **无字幕且转写失败**：保留已下载素材，报告失败原因，不丢数据。
- **图片无值得注意内容**：总结里如实写"无特别注意点"，不硬凑。
- **GitHub 私有仓库**：用 `gh` 鉴权；无权限则提示。

## 11. 测试

- `router`：各平台 URL → 正确分类（单元测试，免网络）。
- `render`：给定假数据 → 生成的 MD 结构正确、路径正确（免网络）。
- 各 `fetcher`：用真实链接做冒烟测试（需 cookie，手动/标记 slow）。
- 端到端：每平台一个真链接，跑通到落盘，人工核对两份稿。

## 12. YAGNI / 暂不做

- 不做 LLM 路由（URL 正则足够）。
- 不抓 star 数、点赞、评论等噪音。
- v1 不做 GUI / APP（铁律已留好后路，以后再说）。
- v1 不接 DeepSeek（analyze 先用 Claude，接口预留）。
- 不做多平台主页批量抓取（只处理"单条链接→单份成稿"）。

## 13. 已确认决策（原待确认项）

1. ✅ 素材策略：链接必留 + 图片必留，音视频默认不存（`--keep-audio`/`--keep-video` 可单开）。见 §7.2。
2. ✅ 文件夹命名：用平台原标题 + `clean_title` 清洗/截断；用户后续可自行改名。见 §7.1。
3. ✅ 复用：已精读源码，搬脚本 + 补 4 块，覆盖 8 平台。见 §8。
4. ✅ 范围：抖音/小红书/播客/B站/微博/知乎/公众号/GitHub。
5. 🔲 仍待定：文字稿里图片用**引用**素材目录（倾向，省空间）还是**复制**几张进成稿夹；小红书 `XHS_COOKIE` 是否接受手动复制一次（vs 自动读浏览器 cookie）。可在实施时定。
