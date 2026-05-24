# 🦐 内容生成多 Agent 技能包

> 6 个专业化内容创作 Agent：第二大脑笔记虾（浏览器搜索 + 素材提供）、朋友圈创作虾、电商视频导演虾、通用内容创作虾、图片素材生成虾（搜索 5 张 + 生成 5 个提示词 + 生成 5 张豆包图片）、电商 seedacne 导演虾（Seedance 提示词专家）

**版本**：v3.0.0  
**作者**：OpenClaw来合火  
**创建时间**：2026-03-16  
**技能 ID**：content-creation-multi-agent  
**Clawhub 分类**：效率工具

---

## 📦 技能元数据

```yaml
name: content-creation-multi-agent
version: 3.0.0
description: 内容生成多 Agent 技能包 - 6 个专业化内容创作 Agent
author: OpenClaw 社区
license: MIT
tags:
  - content-creation
  - multi-agent
  - note-taking
  - copywriting
  - video-script
  - image-generation
  - seedance-prompt
  - 效率工具
```

---

## 🎯 核心功能

### 6 个专业化 Agent

| Agent | 职责 | 核心能力 |
|-------|------|----------|
| **第二大脑笔记虾** 🧠 | 知识管理 + 素材提供 | 浏览器搜索、文件读取、素材提供 |
| **朋友圈创作虾** 📱 | 朋友圈文案创作 | 文案创作、配图建议、发布时间 |
| **电商视频导演虾** 🎬 | 电商视频脚本 | 脚本编写、分镜设计、拍摄建议 |
| **通用内容创作虾** ✍️ | 通用内容创作 | 多文体写作、内容优化、风格调整 |
| **图片素材生成虾** 🎨 | 图片搜索 + 豆包生成 | 搜索 5 张 +5 个提示词 +5 张图片 |
| **电商 seedacne 导演虾** 🎯 | Seedance 提示词 | Seedance 提示词、镜头语言、光影效果 |

### 核心特性

- ✅ 一键自动安装
- ✅ Agent 选择功能
- ✅ 自动下载技能文件
- ✅ 自动创建目录结构
- ✅ 自动配置权限
- ✅ 自动生成说明文档
- ✅ 自动重启 Gateway
- ✅ Clawhub 分享

---

## 🚀 安装方式

### Clawhub 安装（推荐）

在 OpenClaw 对话中发送：
```
安装 content-creation-multi-agent
```

### GitHub 安装

```bash
git clone https://github.com/jiebao360/content-creation-multi-agent.git
mv content-creation-multi-agent ~/.openclaw/workspace/skills/content-creation-multi-agent
cd ~/.openclaw/workspace/skills/content-creation-multi-agent
bash scripts/auto-install.sh
openclaw gateway restart
```

---

## ⚙️ 配置说明

### 前置要求

- ✅ OpenClaw 已安装并运行
- ✅ 飞书授权已完成
- ✅ 豆包 API（可选，用于图片生成）

### 配置步骤

1. **运行自动安装脚本**
   ```bash
   bash scripts/auto-install.sh
   ```

2. **验证安装**
   ```bash
   ls -la ~/.openclaw/workspace/skills/content-creation-multi-agent/
   ```

3. **重启 Gateway**
   ```bash
   openclaw gateway restart
   ```

---

## 📋 使用示例

### 第二大脑笔记虾
```
笔记虾，帮我搜索全网关于 AI 视频生成的最新资料
笔记虾，读取本地文件，整理成素材
```

### 朋友圈创作虾
```
朋友圈虾，帮我写一条产品推广文案
朋友圈虾，使用笔记虾的素材创作文案
```

### 电商视频导演虾
```
视频导演虾，帮我写一个产品展示视频脚本
```

### 通用内容创作虾
```
创作虾，帮我写一篇产品介绍文章
```

### 图片素材生成虾
```
素材虾，帮我生成产品封面图
- 产品：智能手表
- 风格：科技感
- 尺寸：1080x1080
- 数量：5 张

输出：
1. ✅ 搜索 5 张参考图片
2. ✅ 生成 5 个豆包提示词
3. ✅ 生成 5 张豆包图片
```

### 电商 seedacne 导演虾
```
seedacne 导演虾，帮我生成一个智能手表展示的 Seedance 视频提示词
```

---

## 🔄 Agent 协作

### 笔记虾 → 朋友圈虾/创作虾

```
1. 笔记虾搜索全网资料
2. 笔记虾读取本地文件
3. 笔记虾整理知识库内容
4. 笔记虾提供素材包
5. 朋友圈虾/创作虾使用素材创作
```

### 素材虾 → 朋友圈虾/创作虾/视频导演虾

```
1. 素材虾搜索 5 张参考图片
2. 素材虾生成 5 个豆包提示词
3. 素材虾生成 5 张豆包图片
4. 素材虾提供图片包
5. 朋友圈虾/创作虾/视频导演虾使用图片创作
```

---

## 🐛 常见问题

### Q: Agent 选择失败？
**A**: 检查技能是否已安装，重新运行选择脚本

### Q: 图片生成失败？
**A**: 检查豆包 API 配置，检查网络连接

### Q: 笔记虾无法读取文件？
**A**: 检查文件路径是否正确，确认文件权限

### Q: 如何分享技能？
**A**: 配置 clawhub.yaml 后提交到 Clawhub

---

## 📞 参考资源

| 资源 | 链接 |
|------|------|
| OpenClaw 文档 | https://docs.openclaw.ai |
| 飞书开放平台 | https://open.feishu.cn |
| Clawhub | https://clawhub.ai/ |
| 豆包 API | https://www.doubao.com |
| GitHub | https://github.com/jiebao360/content-creation-multi-agent |

---

## 📝 更新日志

### v3.0.0 (2026-03-16 重大更新)

- ✅ 优化图片素材生成虾：搜索 5 张 + 生成 5 个提示词 + 生成 5 张豆包图片
- ✅ 去掉 Gemini API 配置，使用豆包图片生成
- ✅ 优化第二大脑笔记虾：浏览器搜索功能
- ✅ 整合 v2.0.0 所有优化
- ✅ 完善 Agent 协作流程
- ✅ 支持 Clawhub 分享安装

---

**最后更新**：2026-03-16  
**版本**：v3.0.0
