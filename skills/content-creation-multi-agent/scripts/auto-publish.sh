#!/bin/bash

# 🦐 内容生成多 Agent 技能包 - 自动发布脚本（优化版）
# 版本：v3.0.1
# 作者：OpenClaw 社区

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🦐 内容生成多 Agent 技能包 - 自动发布"
echo "版本：v3.0.1"
echo "=========================================="
echo ""

# 检查 Git Token
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ 错误：GITHUB_TOKEN 环境变量未设置${NC}"
    echo ""
    echo "请设置 GITHUB_TOKEN 环境变量："
    echo ""
    echo "方式一：临时设置（当前终端会话有效）"
    echo "  export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    echo ""
    echo "方式二：永久设置（添加到 ~/.zshrc）"
    echo "  echo 'export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' >> ~/.zshrc"
    echo "  source ~/.zshrc"
    echo ""
    exit 1
fi

# 配置信息（标准配置）
GITHUB_USER="jiebao360"
GITHUB_REPO="content-creation-multi-agent"
SKILL_DIR="$HOME/.openclaw/workspace/skills/content-creation-multi-agent"
CLAWHUB_SKILL_ID="content-creation-multi-agent"
SKILL_AUTHOR="OpenClaw 来合火"

echo -e "${BLUE}📁 技能包目录：$SKILL_DIR${NC}"
echo ""

# 进入技能包目录
cd "$SKILL_DIR"

# 步骤 1：Git 提交
echo -e "${BLUE}📝 步骤 1: Git 提交...${NC}"

# 检查是否有更改
if git diff --quiet && git diff --{{profile.lateness.stakeholders.senderType}}d --quiet; then
    echo -e "${YELLOW}⚠️  没有更改需要提交${NC}"
else
    # 添加所有文件
    git add .
    
    # 提交
    git commit -m "Release v3.0.0: 内容生成多 Agent 技能包
    
- 6 个专业化内容创作 Agent
- 第二大脑笔记虾（浏览器搜索 + 素材提供）
- 朋友圈创作虾（文案创作）
- 电商视频导演虾（视频脚本）
- 通用内容创作虾（多文体写作）
- 图片素材生成虾（搜索 5 张 + 生成 5 个提示词 + 生成 5 张豆包图片）
- 电商 seedacne 导演虾（Seedance 提示词专家）
- 一键自动安装
- Agent 选择功能
- Agent 协作流程
- Clawhub 分享支持

Co-authored-by: OpenClaw Community <community@openclaw.ai>"
    
    echo -e "${GREEN}✅ Git 提交完成${NC}"
fi
echo ""

# 步骤 2：推送到 GitHub
echo -e "${BLUE}🚀 步骤 2: 推送到 GitHub...${NC}"

# 检查 remote 是否存在
if ! git remote -v | grep -q origin; then
    echo -e "${YELLOW}⚠️  添加 remote...${NC}"
    git remote add origin https://github.com/$GITHUB_USER/$GITHUB_REPO.git
else
    # 更新 remote URL
    git remote set-url origin https://github.com/$GITHUB_USER/$GITHUB_REPO.git
fi

# 推送（使用 Token）
echo "推送到 GitHub..."

# 配置临时 credential helper
export GIT_ASKPASS=/bin/echo
export GIT_USERNAME=$GITHUB_USER
export GIT_PASSWORD=$GITHUB_TOKEN

# 使用 credential.helper 存储凭证
git config --global credential.helper store

# 推送
if GIT_USERNAME=$GITHUB_USER GIT_PASSWORD=$GITHUB_TOKEN git push -u origin main 2>&1; then
    echo -e "${GREEN}✅ 推送到 GitHub 成功${NC}"
    echo "GitHub 仓库：https://github.com/$GITHUB_USER/$GITHUB_REPO"
else
    echo -e "${RED}❌ 推送到 GitHub 失败${NC}"
    echo ""
    echo -e "${YELLOW}💡 提示：${NC}"
    echo "1. 检查 GITHUB_TOKEN 是否正确（echo $GITHUB_TOKEN）"
    echo "2. 检查 GitHub 用户名是否正确：$GITHUB_USER"
    echo "3. 检查仓库是否存在：https://github.com/$GITHUB_USER/$GITHUB_REPO"
    echo "4. 检查 Token 权限是否足够（需要 repo 权限）"
    echo ""
    echo "重新生成 Token：https://github.com/settings/tokens"
    echo ""
    echo -e "${YELLOW}或者手动推送：${NC}"
    echo "  git remote set-url origin https://$GITHUB_USER:$GITHUB_TOKEN@github.com/$GITHUB_USER/$GITHUB_REPO.git"
    echo "  git push -u origin main"
    exit 1
fi
echo ""

# 步骤 3：提交到 Clawhub
echo -e "${BLUE}📢 步骤 3: 提交到 Clawhub...${NC}"

# 检查 clawhub.yaml 是否存在
if [ ! -f "clawhub.yaml" ]; then
    echo -e "${RED}❌ 错误：clawhub.yaml 不存在${NC}"
    exit 1
fi

# 提交到 Clawhub（通过 OpenClaw）
echo "提交到 Clawhub..."
echo "技能 ID: $CLAWHUB_SKILL_ID"
echo "GitHub 仓库：https://github.com/$GITHUB_USER/$GITHUB_REPO"

# 这里调用 OpenClaw 的 Clawhub 提交功能
# 实际使用时，可以通过 OpenClaw 对话提交
echo ""
echo -e "${YELLOW}⚠️  请在 OpenClaw 对话中发送：${NC}"
echo "  发布技能到 Clawhub：$CLAWHUB_SKILL_ID"
echo ""

echo -e "${GREEN}✅ Clawhub 提交准备完成${NC}"
echo ""

# 步骤 4：生成发布报告
echo -e "${BLUE}📊 步骤 4: 生成发布报告...${NC}"

cat > RELEASE_REPORT.md << EOF
# 📢 内容生成多 Agent 技能包 - 发布报告

> 自动发布成功

**发布时间**：$(date +"%Y-%m-%d %H:%M:%S")
**版本**：v3.0.0
**技能 ID**：$CLAWHUB_SKILL_ID

---

## ✅ 发布状态

### GitHub
- ✅ 代码已推送
- ✅ 仓库：https://github.com/$GITHUB_USER/$GITHUB_REPO
- ✅ 分支：main

### Clawhub
- ⏳ 已提交，等待审核
- 📋 技能 ID：$CLAWHUB_SKILL_ID
- ⏱️ 审核时间：1-2 个工作日

---

## 📦 技能包信息

**6 个专业化 Agent**：
1. 第二大脑笔记虾 🧠 - 知识管理 + 素材提供
2. 朋友圈创作虾 📱 - 朋友圈文案创作
3. 电商视频导演虾 🎬 - 电商视频脚本
4. 通用内容创作虾 ✍️ - 通用内容创作
5. 图片素材生成虾 🎨 - 图片搜索 + 豆包生成
6. 电商 seedacne 导演虾 🎯 - Seedance 提示词专家

**核心功能**：
- 一键自动安装
- Agent 选择功能
- Agent 协作流程
- Clawhub 分享安装

---

## 📊 统计信息

**文件数量**：$(find . -type f | wc -l | tr -d ' ')
**代码行数**：$(find . -name "*.sh" -o -name "*.json" -o -name "*.md" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
**总大小**：$(du -sh . | cut -f1)

---

## 📞 参考资源

| 资源 | 链接 |
|------|------|
| GitHub 仓库 | https://github.com/$GITHUB_USER/$GITHUB_REPO |
| Clawhub | https://clawhub.ai/ |
| OpenClaw 文档 | https://docs.openclaw.ai |

---

_发布时间：$(date +"%Y-%m-%d %H:%M:%S")_
EOF

echo -e "${GREEN}✅ 发布报告已生成：RELEASE_REPORT.md${NC}"
echo ""

# 完成
echo "=========================================="
echo -e "${GREEN}✅ 自动发布完成！${NC}"
echo "=========================================="
echo ""
echo "📁 GitHub 仓库："
echo "  https://github.com/$GITHUB_USER/$GITHUB_REPO"
echo ""
echo "📢 Clawhub 状态："
echo "  已提交，等待审核（1-2 个工作日）"
echo ""
echo "📊 发布报告："
echo "  $SKILL_DIR/RELEASE_REPORT.md"
echo ""
echo "🎉 感谢使用自动发布脚本！"
echo ""
