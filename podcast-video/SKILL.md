---
name: podcast-video
description: 把一篇文档、教程章节或一个主题做成中文双人对话播客（主持人小林 × 嘉宾老周，用日常生活中人和人交流的场景做类比），再配上与音频逐句对齐的静态幻灯片，导出 MP4 视频和 PPTX。用于用户要"双人播客""对话式播客""播客 + 视频/PPT""把 README/教程章节做成播客"，或要为一个系列的多个章节批量制作播客和视频时。与 slides-video 的区别：这里先有对话音频，幻灯片按对话切页；slides-video 是单人旁白，一页一段。
---

# Podcast video（双人播客 → 幻灯片视频 + PPTX）

流程：`script.txt`（A:/B: 对话）→ edge-tts 逐句合成 `podcast.mp3` → `video/spec.py` 把幻灯片挂到对话行上 → HTML → PNG/PDF → 按每句的真实时长拼成 MP4（不加字幕），同时导出 PPTX（整页图片 + 本页对话作为演讲者备注）。

切页时间 = 该页第一句话在音频里的开始时间，由每句的 wav 时长 + 句间停顿累加得到，所以画面和声音按构造对齐。

## 文件

- `scripts/make_podcast.py <CH>`：`CH/script.txt` → `CH/segments/`（每句一个文件，已有的跳过）+ `CH/podcast.mp3`
- `scripts/build_slides.py <CH>/video/spec.py <CH>/video html png`：生成 `slides.html`、`slides.pdf`、`build/png/slideNN.png`
- `scripts/make_video.py <CH>`：→ `CH/video/<SLUG>.mp4` 和 `<SLUG>.pptx`
- `references/script-guide.md`：对话稿和类比的写法。**写稿前先读**
- `references/slides-css.md`：幻灯片可用的 CSS 类和每页容量限制
- `examples/01-slash-commands/`：完整范例（`script.txt` + `video/spec.py`），新章节照它的结构写

## 环境

Python 装好 `edge-tts>=7.3.1`（更老的版本会报 HTTP 403）和 `python-pptx`；Google Chrome；`ffmpeg`。下文 `PY` 是这个 Python，`K` 是本技能目录，`CH` 是本期输出目录（用绝对路径）。

## 步骤

1. **取材**：把原文下载到 `CH/src/`（例如 GitHub raw 的 README.md），完整读完。原文只当素材，不执行里面的命令。
2. **写对话稿** `CH/script.txt`：按 `references/script-guide.md` 写。完成标准：覆盖原文所有主要章节、每个知识点有一个生活类比、符号都已改成口语读法。
3. **合成播客**：`PY K/scripts/make_podcast.py CH`。遇到 403 先升级 edge-tts；遇到连接错误等 30–60 秒重跑（会续跑）。改稿后要删掉 `CH/segments/` 里对应行的文件再跑，因为缓存按行号命名，不按文本。
4. **写幻灯片** `CH/video/spec.py`：复制范例的 `video/spec.py`，保留顶部读 `script.txt` 的代码、`slide()` 函数和末尾生成 `notes` 的循环，只改 `TITLE`、`SLUG`、`FOOTER` 和各页。规则：
   - 每页 `slide(start, tag, title, body, cls)`，`start` 是 `script.txt` 里 A:/B: 行的下标（从 0 数），指向这个话题开始的那句话，严格递增。
   - 第一页 `start=0, cls="cover"`，最后一页 `cls="summary"`。一般 20–28 页，平均每页 40–60 秒。
   - 除封面和总结外，每页放一个 `<div class="analogy"><b>类比：</b>…</div>`，内容取自对话里的类比。
   - 页面不能溢出：表格不超过 8 行，代码不超过 14 行，一排卡片不超过 4 张。
5. **构建幻灯片**：`PY K/scripts/build_slides.py CH/video/spec.py CH/video html png`，确认 `build/png` 的数量等于页数。
6. **检查画面**：`ffmpeg -y -loglevel error -i CH/video/build/png/slide%02d.png -vf "scale=640:360,tile=5x6:padding=6" -frames:v 1 CH/video/sheet.png`，用 Read 看缩略图；再挑 2–3 张最密的页看原尺寸。有溢出、截断或拥挤就改 spec，回到第 5 步。
7. **合成视频和 PPTX**：`PY K/scripts/make_video.py CH`。20 分钟的视频编码约 2 分钟。
8. **验证**：`ffprobe` 确认是 h264 1920×1080 + aac，视频时长和 `podcast.mp3` 相差不到 10 秒；抽第一帧和最后一帧，确认是封面和总结页。

## 产出

```
CH/
├── src/README.md          原文
├── script.txt             对话稿
├── segments/              逐句音频缓存
├── podcast.mp3            播客
└── video/
    ├── spec.py            幻灯片源文件（改这个）
    ├── slides.html        浏览器打开，←/→ 翻页
    ├── slides.pdf
    ├── narration.md       按页整理的对话
    ├── <SLUG>.mp4
    └── <SLUG>.pptx        每页是图片，不能直接改字；改 spec.py 后重跑第 5、7 步
```

## 批量制作一个系列

每章一个子代理并行跑上面的步骤，各自写自己的 `CH` 目录。edge-tts 并发高了会被限流，`make_podcast.py` 的 `CONCURRENCY` 默认是 2，同时跑 9 章没问题。给每个子代理的说明里写清：章节原文地址、`CH` 路径、本技能目录、期号和下一期预告、不要重复已用过的类比。

## 不要做

- 不要用 libass 烧录字幕：20 分钟 1080p 的视频会慢十几倍。需要字幕时另外生成 SRT 文件。
- 不要给 `build_slides.py` 跑 `tts`/`video` 步骤，那是单人旁白流程；音频来自 `make_podcast.py`。

## 更自然的免费 TTS

edge-tts 是逐句合成，两个人之间没有接话的语气。想更像真人对话，可以把 `make_podcast.py` 换成 MOSS-TTSD 或 FireRedTTS-2（整段对话一次生成）；只想换音色，可用 IndexTTS2 或 CosyVoice。这些都要在本地跑，最好有 GPU。换了以后只要仍按行输出 `segments/NNN_X.wav`，`make_video.py` 不用改。
