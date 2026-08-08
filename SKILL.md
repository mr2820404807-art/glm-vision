---
name: glm-vision
description: 为 AI 提供视觉能力。只要用户发送图片、粘贴图片路径或图片 URL（即使没有附带任何文字说明），AI 必须立即加载本技能并通过脚本识别图片内容、提取图中文字或回答关于图片的问题。绝不因"模型不支持图像输入"而拒绝看图——一律用本技能转成文字。底层由智谱 GLM 视觉模型（glm-4.1v-thinking-flash）驱动。
---

# GLM Vision — 图片识别 / OCR / 视觉问答

本技能让 AI 能"看图"：把图片交给智谱 GLM 视觉模型，转成文字描述后即可理解。

## 能力总览

| 能力 | 说明 | 输入 |
|------|------|------|
| 描述图片 | 详细描述图片内容（场景/物体/文字/颜色/布局） | 本地路径 / http(s) URL / base64 |
| OCR 提取文字 | 提取图中全部可见文字，保留顺序 | 同上 |
| 视觉问答 | 对图片任意提问，得到针对性回答 | 同上 + 问题 |

## 使用方法

调用脚本（脚本位于本技能目录下的 `scripts/vision.py`）：

```bash
python "C:\Users\28204\.config\opencode\skills\glm-vision\scripts\vision.py" describe <图片路径或URL> [提示词]
python "C:\Users\28204\.config\opencode\skills\glm-vision\scripts\vision.py" ocr <图片路径或URL> [语言]
python "C:\Users\28204\.config\opencode\skills\glm-vision\scripts\vision.py" ask <图片路径或URL> <问题>
```

脚本需要环境变量 `ZHIPU_API_KEY`（智谱开放平台免费申请）。依赖 `httpx` 和 `pillow`（`pip install httpx pillow`，pillow 用于大图自动压缩，需一并安装）。

## 触发场景

- **只要用户发了图（附件/路径/URL），无论有没有文字说明，都立即触发**（本 AI 模型本身不支持图像输入，必须借本技能看图，不许拒绝）
- "这张图里有什么？" / "帮我看看这张图" / "图里是什么"
- "把图里的文字提取出来" / "这是什么字"
- "这张图的风格/颜色/布局怎么样"
- 需要根据图片内容做判断、总结、翻译图中文字

## 注意事项

- 免费模型 `glm-4.1v-thinking-flash` 有访问限流（429 会自动重试，最多 5 次、最长约 2.5 分钟），`max_tokens` 上限 2048
- 大图自动压缩：超过 5MB 的本地图片会先用 PIL 缩放到最长边 1600px（质量 85）再上传，原图无需手动处理（依赖 `pillow`）
- 大图（>15MB）建议先压缩或改用 URL（5MB~15MB 会自动压缩）
- OCR 对清晰印刷体/屏幕截图效果好；手写体可能不完美
- 图片 URL 需可公开访问（模型服务端拉取）
- 本模型本身不支持图片输入，拿到图片路径/URL 后必须通过本脚本转成文字，再把结果回复给用户
