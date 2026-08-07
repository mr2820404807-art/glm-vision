---
name: glm-vision
description: 为不支持多模态的 AI 模型新增视觉能力：识别/描述图片内容、提取图中文字(OCR)、对图片提问。当用户发送图片、要求"看这张图/图里有什么/识别图片/读取图片文字/分析图片"时触发。底层由智谱 GLM 视觉模型（glm-4v-flash）驱动。
---

# GLM Vision — 图片识别 / OCR / 视觉问答

本技能让 AI 能"看图"：把图片交给智谱 GLM 视觉模型，转成文字描述后即可理解。专为**不支持多模态输入**的模型设计——模型本身不能看图，但通过本脚本把图片"翻译"成文字，就能像真的看图一样回答用户。

## 能力总览

| 能力 | 说明 | 输入 |
|------|------|------|
| 描述图片 | 详细描述图片内容（场景/物体/文字/颜色/布局） | 本地路径 / http(s) URL / base64 |
| OCR 提取文字 | 提取图中全部可见文字，保留顺序 | 同上 |
| 视觉问答 | 对图片任意提问，得到针对性回答 | 同上 + 问题 |

## 使用方法

### 快速开始（小白版）

1. **下载**：进入右侧 **Releases**，下载 `glm-vision-v1.0.0.zip` 压缩包（或直接下载本仓库的 `SKILL.md` + `scripts/` 文件夹，两个都需要）
2. 解压后把 **`SKILL.md` 和 `scripts/` 文件夹一起发给 AI**，告诉它"安装这个 skill"
3. 打开 [智谱开放平台](https://open.bigmodel.cn)，注册后**创建一个 API Key**
4. 把 API Key **发给 AI**，它会自动帮你配置好

之后直接发图片给它就能"看图"了。

> 注意：`SKILL.md` 是使用说明，`scripts/vision.py` 是实际调用智谱 API 的脚本，**两者缺一不可**。

### 手动安装（进阶）

```bash
git clone https://github.com/mr2820404807-art/glm-vision.git
pip install httpx
```

设置环境变量 `ZHIPU_API_KEY`（在 [智谱开放平台](https://open.bigmodel.cn) 免费申请）：

```bash
# Linux / macOS
export ZHIPU_API_KEY="你的密钥"

# Windows
setx ZHIPU_API_KEY "你的密钥"
```

### 命令行调用

```bash
python vision.py describe <图片路径或URL> [提示词]
python vision.py ocr <图片路径或URL> [语言]
python vision.py ask <图片路径或URL> <问题>
```

### 作为 AI 技能安装（以 opencode / Claude Code 等为例）

把 `SKILL.md` 和 `scripts/` 放入技能的技能目录（如 `~/.config/opencode/skills/glm-vision/` 或 `.claude/skills/glm-vision/`），AI 收到图片时会自动触发调用。

## 参数说明

`<图片>` 支持三种输入方式：

- **本地文件路径**：如 `C:\Users\xxx\Pictures\a.png` 或 `./photo.jpg`
- **http(s) 链接**：需可公开访问（模型服务端拉取）
- **base64 数据**：直接传编码后的字符串（自动识别）

可选环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ZHIPU_API_KEY` | （必填） | 智谱 API 密钥 |
| `ZHIPU_BASE_URL` | `https://open.bigmodel.cn/api/paas/v4` | API 地址（兼容 OpenAI 格式） |
| `GLM_VISION_MODEL` | `glm-4v-flash` | 视觉模型名称 |

## 项目结构

```
.
├── SKILL.md              # AI 技能定义（触发词 + 使用说明）
├── scripts/
│   └── vision.py         # 核心脚本：图片 → GLM 视觉模型 → 文字
├── glm-vision-v1.0.0.zip # 发布版打包（SKILL.md + scripts/），见右侧 Releases
└── README.md             # 本文档
```

## 技术栈

- Python 3.9+（标准库 + [httpx](https://www.python-httpx.org/)）
- [智谱 GLM-4V-Flash](https://open.bigmodel.cn) 免费视觉模型（OpenAI 兼容接口）

## 工作原理

1. 模型收到图片路径/URL/base64
2. 脚本读取图片并编码为 base64（或直传 URL）
3. 调用 GLM-4V-Flash 视觉模型，携带用户的问题
4. 模型返回文字描述/OCR 结果/回答
5. 交给原始 AI 模型继续处理，实现"无多模态模型也能看图"

## 注意事项

- 免费模型 `glm-4v-flash` 有访问限流（429 时稍等重试），`max_tokens` 上限 1024
- 大图（>15MB）建议先压缩或改用 URL
- OCR 对清晰印刷体/屏幕截图效果好；手写体可能不完美
- 图片 URL 需可公开访问（模型服务端拉取）
- Windows 下脚本自动以 UTF-8 输出，避免中文乱码

## License

本项目用于学习交流使用。
