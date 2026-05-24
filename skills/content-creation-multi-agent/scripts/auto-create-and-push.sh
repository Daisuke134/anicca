#!/bin/bash

# 🚀 自动创建 GitHub 仓库并推送脚本
# 版本：v1.0.0
# 作者：OpenClaw 来合火

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🚀 自动创建 GitHub 仓库并推送"
echo "版本：v1.0.0"
echo "=========================================="
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ 错误：GITHUB_TOKEN 环境变量未设置${NC}"
    echo "请设置：export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx"
    exit 1
fi

GITHUB_USER="jiebao360"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_NAME="$(basename "$SKILL_DIR")"
REPO_DESC="内容生成多 Agent 系统 - 商用级内容生成全流程"

echo -e "${BLUE}📁 技能包目录：$SKILL_DIR${NC}"
echo -e "${BLUE}📦 仓库名称：$REPO_NAME${NC}"
echo ""

# 步骤 1：检查 Git 仓库
echo -e "${BLUE}📝 步骤 1: 检查 Git 仓库...${NC}"

if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  初始化 Git 仓库...${NC}"
    git init
    git add -A
    git commit -m "Initial release: $REPO_NAME v1.0.0
    
作者：OpenClaw 来合火"
else
    echo "✅ Git 仓库已存在"
    if ! git diff --quiet || ! git diff --{{profile.lateness.stakeholders.senderType}}d --quiet; then
        echo -e "${YELLOW}⚠️  有未提交的更改，正在提交...${NC}"
        git add -A
        git commit -m "Update: $REPO_NAME
        
作者：OpenClaw 来合火"
    else
        echo "✅ 没有未提交的更改"
    fi
fi
echo ""

# 步骤 2：配置 Git 用户信息
echo -e "${BLUE}🔧 步骤 2: 配置 Git 用户信息...${NC}"
git config user.name "OpenClaw 来合火"
git config user.{{profile.lateness.stakeholders.channel}} "jiebao360@users.noreply.github.com"
echo "✅ Git 用户信息已配置"
echo ""

# 步骤 3：检查 remote
echo -e "${BLUE}🔗 步骤 3: 检查 remote...${NC}"

if ! git remote -v | grep -q origin; then
    echo -e "${YELLOW}⚠️  添加 remote...${NC}"
    git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git
else
    echo "✅ remote 已存在"
    git remote set-url origin https://github.com/$GITHUB_USER/$REPO_NAME.git
fi
echo ""

# 步骤 4：检查 GitHub 仓库是否存在
echo -e "${BLUE}🔍 步骤 4: 检查 GitHub 仓库...${NC}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$GITHUB_USER/$REPO_NAME")

if [ "$HTTP_CODE" = "404" ]; then
    echo -e "${YELLOW}⚠️  仓库不存在，正在创建...${NC}"
    
    CREATE_RESPONSE=$(curl -s -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        https://api.github.com/user/repos \
        -d "{\"name\":\"$REPO_NAME\",\"description\":\"$REPO_DESC\",\"private\":false,\"auto_init\":false}")
    
    if echo "$CREATE_RESPONSE" | grep -q "\"name\""; then
        echo -e "${GREEN}✅ GitHub 仓库创建成功${NC}"
        echo "仓库地址：https://github.com/$GITHUB_USER/$REPO_NAME"
    else
        echo -e "${RED}❌ 创建仓库失败${NC}"
        echo "错误信息：$CREATE_RESPONSE"
        exit 1
    fi
elif [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ GitHub 仓库已存在${NC}"
    echo "仓库地址：https://github.com/$GITHUB_USER/$REPO_NAME"
else
    echo -e "${YELLOW}⚠️  仓库状态码：$HTTP_CODE${NC}"
fi
echo ""

# 步骤 5：推送代码
echo -e "${BLUE}🚀 步骤 5: 推送代码...${NC}"

git config --global credential.helper store

echo "推送到 GitHub..."
if GIT_USERNAME=$GITHUB_USER GIT_PASSWORD=$GITHUB_TOKEN git push -f -u origin main 2>&1; then
    echo -e "${GREEN}✅ 推送到 GitHub 成功${NC}"
    echo "GitHub 仓库：https://github.com/$GITHUB_USER/$REPO_NAME"
else
    echo -e "${RED}❌ 推送到 GitHub 失败${NC}"
    echo "请检查 GITHUB_TOKEN 是否正确"
    exit 1
fi
echo ""

# 步骤 6：生成发布报告
echo -e "${BLUE}📊 步骤 6: 生成发布报告...${NC}"

cat > GITHUB_RELEASE_REPORT.md << EOF
# 📢 $REPO_NAME - GitHub 发布报告

**发布时间**：$(date +"%Y-%m-%d %H:%M:%S")
**版本**：v1.0.0
**作者**：OpenClaw 来合火

## ✅ 发布状态

### GitHub
- ✅ 仓库已创建
- ✅ 代码已推送
- ✅ 仓库：https://github.com/$GITHUB_USER/$REPO_NAME

### Clawhub
- ⏳ 待提交
- 📋 技能 ID：$REPO_NAME

## 📦 技能包信息

**技能名称**：$REPO_NAME
**版本**：v1.0.0
**作者**：OpenClaw 来合火
**描述**：$REPO_DESC

---
_发布时间：$(date +"%Y-%m-%d %H:%M:%S")_
EOF

echo -e "${GREEN}✅ 发布报告已生成：GITHUB_RELEASE_REPORT.md${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}✅ 自动创建并推送完成！${NC}"
echo "=========================================="
echo ""
echo "📁 GitHub 仓库："
echo "  https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo "📢 Clawhub 状态："
echo "  待提交（请在 OpenClaw 对话中发送：发布技能到 Clawhub：$REPO_NAME）"
echo ""
echo "📊 发布报告："
echo "  $SKILL_DIR/GITHUB_RELEASE_REPORT.md"
echo ""
