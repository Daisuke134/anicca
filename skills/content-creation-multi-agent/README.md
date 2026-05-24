# 🦐 内容生成多 Agent 系统 v4.0.1

> 商用级内容生成全流程系统。配置飞书机器人名称、应用凭证、大模型名称，自动匹配 6 个内容创作 Agent（含第二大脑笔记虾），支持文章、朋友圈、视频脚本、图片、Seedance 提示词全流程内容生成。支持跨平台自动安装（macOS/Linux/Windows）

**版本**：v4.0.1（优化版）  
**作者**：OpenClaw 来合火  
**创建时间**：2026-03-17  
**GitHub**：https://github.com/jiebao360/content-creation-multi-agent  
**Clawhub**：content-creation-multi-agent

---

## 📦 技能介绍

商用级内容生成多 Agent 系统，整合第二大脑笔记虾能力，提供完整的内容创作工作流。支持自定义机器人名称、应用凭证、大模型名称，自动匹配 6 个内容创作 Agent。

### 核心能力

- ✅ 配置飞书机器人名称（可自定义，如：内容创作）
- ✅ 配置应用凭证（App ID、App Secret）
- ✅ 配置大模型名称（可指定或自动配置）
- ✅ 自动匹配内容创作 Agent（含第二大脑笔记虾）
- ✅ 6 个专业化内容创作 Agent
- ✅ 商用内容生成全流程
- ✅ 生成本地 md 文档
- ✅ 生成飞书文档
- ✅ 一键自动安装（跨平台）

### 6 个内容创作 Agent

| Agent | 职责 | 默认模型 | 推荐技能 |
|-------|------|----------|----------|
| **Note** | 第二大脑笔记虾（知识管理、素材提供） | doubao-pro | web-search, file-reading, knowledge-management |
| **Content** | 文章写作、报告、文案 | doubao | article-writer, ai-daily-news |
| **Moments** | 朋友圈、社交媒体 | doubao | copywriting, social-media |
| **Video Director** | 视频脚本、分镜 | doubao-pro | video-script, storyboard |
| **Image Generator** | 图片搜索、豆包生成 | doubao-pro | image-search, doubao-prompt, image-generation |
| **Seedance Director** | Seedance 提示词 | doubao-pro | seedance-prompt, video-direction, prompt-engineering |

---

## 🚀 安装方式

### 方式一：Clawhub 安装（最简单）

在 OpenClaw 对话中发送：
```
安装 content-creation-multi-agent
```

### 方式二：GitHub 安装

在 OpenClaw 对话中发送：
```
安装 https://github.com/jiebao360/content-creation-multi-agent
```

### 方式三：自动安装脚本（推荐）

**macOS / Linux**:
```bash
curl -fsSL https://raw.githubusercontent.com/jiebao360/content-creation-multi-agent/main/install.sh | bash
```

**Windows**:
```powershell
# 在 Git Bash 中
curl -fsSL https://raw.githubusercontent.com/jiebao360/content-creation-multi-agent/main/install.bat -o install.bat
./install.bat
```

### 方式四：命令行安装

```bash
# 1. 克隆仓库
git clone https://github.com/jiebao360/content-creation-multi-agent.git

# 2. 移动到 skills 目录
mv content-creation-multi-agent ~/.openclaw/workspace/skills/content-creation-multi-agent

# 3. 运行配置脚本
cd ~/.openclaw/workspace/skills/content-creation-multi-agent
bash scripts/configure-bot.sh

# 4. 重启 Gateway
openclaw gateway restart
```

---

## ⚙️ 配置说明

### 前置要求

- ✅ OpenClaw 已安装并运行
- ✅ 飞书授权已完成
- ✅ 飞书 Bot 有以下权限：
  - `im:message`
  - `im:message:send_as_bot`
  - `docs:doc`

### 配置步骤

#### 1. 运行配置脚本

```bash
cd ~/.openclaw/workspace/skills/content-creation-multi-agent
bash scripts/configure-bot.sh
```

配置脚本会自动：
1. 配置机器人名称
2. 配置飞书应用凭证
3. 配置大模型名称
4. 自动匹配内容创作 Agent（含第二大脑笔记虾）
5. 生成配置文件
6. 生成本地文档

#### 2. 验证安装

```bash
# 检查技能文件
ls -la ~/.openclaw/workspace/skills/content-creation-multi-agent/

# 检查配置文件
ls -la ~/.openclaw/workspace-main/bot-configs/

# 检查 Gateway 状态
openclaw status
```

---

## 📋 使用方式

### 方式一：对话配置（推荐）

在已经配置好的飞书机器人对话中对龙虾说：

```
配置飞书机器人

机器人名称：内容创作
飞书应用凭证：
- App ID: cli_xxx
- App Secret: xxx
大模型名称：doubao（可以指定已经配置好的模型，也可以为空自动配置默认大模型）

创建对应 agent：Content Agent（内容创作）
如果为空，自动匹配为机器人名称的技能
```

龙虾会自动：
1. ✅ 配置机器人名称
2. ✅ 配置飞书应用凭证
3. ✅ 配置大模型名称
4. ✅ 自动匹配 Agent（含第二大脑笔记虾）
5. ✅ 生成配置文件
6. ✅ 生成本地文档

### 方式二：使用配置脚本

```bash
cd ~/.openclaw/workspace/skills/content-creation-multi-agent
bash scripts/configure-bot.sh
```

按提示输入：
1. 机器人名称（默认：内容创作）
2. App ID 和 App Secret
3. 大模型名称（默认：doubao）
4. 选择要创建的 Agent（直接回车自动匹配）

---

## 🎯 配置流程

### 步骤 1：配置机器人名称

```
请输入飞书机器人名称（默认：内容创作）：内容创作
✅ 机器人名称：内容创作
```

### 步骤 2：配置飞书应用凭证

```
App ID（必填）：cli_xxx
App Secret（必填）：xxx
✅ 飞书应用凭证已配置
```

### 步骤 3：配置大模型名称

```
配置大模型名称
提示：可以指定已经配置好的模型，也可以为空自动配置默认大模型
大模型名称（默认：doubao）：doubao
✅ 大模型名称：doubao
```

### 步骤 4：选择要创建的 Agent

```
请选择要创建的 Agent（输入序号，多个用逗号分隔）：
  [1] Note - 第二大脑笔记虾（知识管理、素材提供）
  [2] Content - 内容创作（文章、报告、文案）
  [3] Moments - 朋友圈创作（社交媒体）
  [4] Video Director - 视频导演（脚本、分镜）
  [5] Image Generator - 图片生成（封面、配图）
  [6] Seedance Director - Seedance 导演（AI 视频提示词）
  [0] 全部创建（6 个 Agent）

选择（直接回车自动匹配）：
🤖 自动匹配 Agent...
✅ 自动匹配：第二大脑笔记虾 + Content Agent（内容创作）
```

### 步骤 5：自动生成

系统自动：
1. 生成 `bot-config_TIMESTAMP.json` - Agent 配置
2. 生成 `bot-setup_TIMESTAMP.md` - 本地文档
3. 准备飞书文档创建指令

---

## 🔄 自动匹配规则

### 根据机器人名称自动匹配

| 机器人名称包含 | 自动匹配 Agent |
|---------------|---------------|
| 内容、创作、Content | Note + Content（笔记虾 + 内容创作） |
| 笔记、Note、知识 | Note（笔记虾） |
| 朋友圈、Moments、社交 | Note + Moments（笔记虾 + 朋友圈） |
| 视频、Video、导演 | Note + Video + Seedance（笔记虾 + 视频导演 + Seedance） |
| 图片、Image、设计 | Note + Image（笔记虾 + 图片生成） |
| 自媒体、运营 | Note + Content + Moments + Image（笔记虾 + 内容 + 朋友圈 + 图片） |
| 其他 | Note + Content（默认：笔记虾 + 内容创作） |

**重要**：自动匹配时都会包含第二大脑笔记虾，确保素材提供能力。

---

## 🔄 商用内容生成工作流

### 完整流程

```
1. 笔记虾搜索素材
   ↓
2. Content 虾写文章
   ↓
3. Image 虾生成封面
   ↓
4. Video 虾写脚本
   ↓
5. Seedance 虾生成提示词
```

### 使用示例

**步骤 1：搜索素材**
```
笔记虾，帮我搜索全网关于 AI 视频生成的最新资料
```

**步骤 2：写文章**
```
创作虾，使用笔记虾的资料写一篇 AI 视频生成教程文章
```

**步骤 3：生成封面**
```
图片虾，帮我生成 AI 视频教程的封面图
- 主题：AI 视频生成
- 风格：科技感
- 尺寸：1080x1080
- 数量：5 张
```

**步骤 4：写视频脚本**
```
视频虾，帮我写一个 AI 视频生成教程的视频脚本
- 时长：60 秒
- 风格：教学
```

**步骤 5：生成 Seedance 提示词**
```
Seedance 虾，帮我生成 AI 视频生成的 Seedance 视频提示词
- 主题：AI 视频生成教程
- 风格：科技感、教学
- 时长：60 秒
```

---

## 📁 生成的文档

### 配置文件（JSON）

位置：`~/.openclaw/workspace-main/bot-configs/bot-config_TIMESTAMP.json`

```json
{
  "robot_name": "内容创作",
  "app_id": "cli_xxx",
  "app_secret": "xxx",
  "model": "doubao",
  "created_at": "2026-03-17T02:30:00+08:00",
  "agents": [
    {
      "name": "内容创作 - Note",
      "role": "知识管理、素材提供、全网搜索、文件读取",
      "model": "doubao-pro",
      "thinking": "on",
      "skills": ["web-search", "file-reading", "knowledge-management", "content-curation", "material-supply"],
      "keywords": "笔记、整理、知识库、素材库、搜索、文件读取、内容提供"
    },
    {
      "name": "内容创作 - Content",
      "role": "文章写作、报告生成、营销文案",
      "model": "doubao",
      "thinking": "on",
      "skills": ["article-writer", "ai-daily-news"],
      "keywords": "写文章、报告、文案、内容、创作"
    }
  ],
  "routing": {
    "enabled": true,
    "default": "note"
  }
}
```

---

## 📁 文件结构

```
content-creation-multi-agent/
├── SKILL.md                    # 技能描述
├── _meta.json                  # 技能元数据
├── README.md                   # 使用说明
├── install.sh                  # macOS/Linux 安装脚本
├── install.bat                 # Windows 安装脚本
├── scripts/
│   ├── auto-create-and-push.sh # 自动创建 GitHub 仓库脚本
│   ├── configure-bot.sh        # 配置脚本
│   └── ...
└── output/                     # 生成的文件（运行时创建）
    ├── bot-config_TIMESTAMP.json
    └── bot-setup_TIMESTAMP.md
```

---

## 📞 参考资源

| 资源 | 链接 |
|------|------|
| GitHub 仓库 | https://github.com/jiebao360/content-creation-multi-agent |
| OpenClaw 文档 | https://docs.openclaw.ai |
| 飞书开放平台 | https://open.feishu.cn |
| Clawhub 技能站 | https://clawhub.ai/ |

---

## 📝 更新日志

### v4.0.1 (2026-03-17 优化版)

- ✅ 加入第二大脑笔记虾技能
- ✅ 优化自动匹配逻辑（根据机器人名称智能匹配）
- ✅ 支持自定义机器人名称配置
- ✅ 支持大模型名称配置（可指定或自动配置）
- ✅ 自动匹配 6 个内容创作 Agent
- ✅ 商用内容生成全流程
- ✅ 跨平台自动安装
- ✅ 自动检测 OpenClaw 路径

### v4.0.0 (2026-03-17 商用版)

- ✅ 整合飞书机器人配置助手所有能力
- ✅ 支持自定义机器人名称
- ✅ 支持大模型名称配置
- ✅ 自动匹配 5 个内容创作 Agent
- ✅ 商用内容生成全流程

---

## 👥 贡献者

- **作者**：OpenClaw 来合火

---

## 📄 许可证

MIT License - 开源免费使用

---

_商用级内容生成全流程系统，让内容创作更高效！_ 🦐✨

**最后更新**：2026-03-17  
**版本**：v4.0.1（优化版）
