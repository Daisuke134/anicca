#!/bin/bash

# 🦐 内容生成多 Agent 系统 - 配置脚本（优化版）
# 版本：v4.0.1
# 作者：OpenClaw 来合火

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🦐 内容生成多 Agent 系统 - 配置"
echo "版本：v4.0.1（优化版）"
echo "=========================================="
echo ""

SKILL_DIR="$HOME/.openclaw/workspace/skills/content-creation-multi-agent"
CONFIG_DIR="$HOME/.openclaw/workspace-main/bot-configs"
mkdir -p "$CONFIG_DIR"

echo -e "${BLUE}📝 请输入配置信息：${NC}"
echo ""

# 步骤 1：配置机器人名称
echo -e "${YELLOW}1️⃣ 配置飞书机器人名称${NC}"
read -r -p "机器人名称（默认：内容创作）：" ROBOT_NAME
ROBOT_NAME=${ROBOT_NAME:-内容创作}
echo "✅ 机器人名称：$ROBOT_NAME"
echo ""

# 步骤 2：配置飞书应用凭证
echo -e "${YELLOW}2️⃣ 配置飞书应用凭证${NC}"
read -r -p "App ID（必填）：" APP_ID
if [ -z "$APP_ID" ]; then
    echo -e "${RED}❌ App ID 不能为空${NC}"
    exit 1
fi

read -r -p "App Secret（必填）：" APP_SECRET
if [ -z "$APP_SECRET" ]; then
    echo -e "${RED}❌ App Secret 不能为空${NC}"
    exit 1
fi
echo "✅ 飞书应用凭证已配置"
echo ""

# 步骤 3：配置大模型名称
echo -e "${YELLOW}3️⃣ 配置大模型名称${NC}"
echo "提示：可以指定已经配置好的模型，也可以为空自动配置默认大模型"
read -r -p "大模型名称（默认：doubao）：" MODEL_NAME
MODEL_NAME=${MODEL_NAME:-doubao}
echo "✅ 大模型名称：$MODEL_NAME"
echo ""

# 步骤 4：选择要创建的 Agent
echo -e "${YELLOW}4️⃣ 选择要创建的 Agent${NC}"
echo "提示：如果为空，自动匹配为机器人名称对应的技能"
echo ""
echo "请选择要创建的 Agent（输入序号，多个用逗号分隔）："
echo "  [1] Note - 第二大脑笔记虾（知识管理、素材提供）"
echo "  [2] Content - 内容创作（文章、报告、文案）"
echo "  [3] Moments - 朋友圈创作（社交媒体）"
echo "  [4] Video Director - 视频导演（脚本、分镜）"
echo "  [5] Image Generator - 图片生成（封面、配图）"
echo "  [6] Seedance Director - Seedance 导演（AI 视频提示词）"
echo "  [0] 全部创建（6 个 Agent）"
echo ""
read -r -p "选择（直接回车自动匹配）：" AGENT_CHOICES

# 自动匹配逻辑
if [ -z "$AGENT_CHOICES" ]; then
    echo -e "${BLUE}🤖 自动匹配 Agent...${NC}"
    
    # 根据机器人名称自动匹配（只匹配最相关的）
    case "$ROBOT_NAME" in
        *内容*|*创作*|*Content*)
            AGENTS=("note" "content")
            echo "✅ 自动匹配：第二大脑笔记虾 + Content Agent（内容创作）"
            ;;
        *笔记*|*Note*|*知识*)
            AGENTS=("note")
            echo "✅ 自动匹配：第二大脑笔记虾（知识管理）"
            ;;
        *朋友圈*|*Moments*|*社交*)
            AGENTS=("note" "moments")
            echo "✅ 自动匹配：第二大脑笔记虾 + Moments Agent（朋友圈创作）"
            ;;
        *视频*|*Video*|*导演*)
            AGENTS=("note" "video-director" "seedance-director")
            echo "✅ 自动匹配：第二大脑笔记虾 + Video Director + Seedance Director"
            ;;
        *图片*|*Image*|*设计*)
            AGENTS=("note" "image-generator")
            echo "✅ 自动匹配：第二大脑笔记虾 + Image Generator（图片生成）"
            ;;
        *自媒体*|*运营*)
            AGENTS=("note" "content" "moments" "image-generator")
            echo "✅ 自动匹配：笔记虾 + 内容创作 + 朋友圈 + 图片生成"
            ;;
        *)
            # 默认创建笔记虾 + 内容创作
            AGENTS=("note" "content")
            echo "✅ 默认匹配：第二大脑笔记虾 + Content Agent（内容创作）"
            ;;
    esac
elif [ "$AGENT_CHOICES" = "0" ]; then
    echo -e "${BLUE}🤖 创建全部 Agent...${NC}"
    AGENTS=("note" "content" "moments" "video-director" "image-generator" "seedance-director")
    echo "✅ 全部创建：6 个 Agent"
else
    # 手动选择
    AGENTS=()
    if [[ "$AGENT_CHOICES" =~ 1 ]]; then AGENTS+=("note"); fi
    if [[ "$AGENT_CHOICES" =~ 2 ]]; then AGENTS+=("content"); fi
    if [[ "$AGENT_CHOICES" =~ 3 ]]; then AGENTS+=("moments"); fi
    if [[ "$AGENT_CHOICES" =~ 4 ]]; then AGENTS+=("video-director"); fi
    if [[ "$AGENT_CHOICES" =~ 5 ]]; then AGENTS+=("image-generator"); fi
    if [[ "$AGENT_CHOICES" =~ 6 ]]; then AGENTS+=("seedance-director"); fi
fi

echo ""

# 步骤 5：生成配置文件
echo -e "${BLUE}📄 生成配置文件...${NC}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONFIG_FILE="$CONFIG_DIR/bot-config_${TIMESTAMP}.json"

cat > "$CONFIG_FILE" << EOF
{
  "robot_name": "$ROBOT_NAME",
  "app_id": "$APP_ID",
  "app_secret": "$APP_SECRET",
  "model": "$MODEL_NAME",
  "created_at": "$(date -Iseconds)",
  "agents": [
EOF

FIRST=true
for agent in "${AGENTS[@]}"; do
    if [ "$FIRST" = true ]; then
        FIRST=false
    else
        echo "," >> "$CONFIG_FILE"
    fi
    
    case $agent in
        note)
            ROLE="知识管理、素材提供、全网搜索、文件读取"
            AGENT_MODEL="${MODEL_NAME}-pro"
            THINKING="on"
            SKILLS='["web-search", "file-reading", "knowledge-management", "content-curation", "material-supply"]'
            KEYWORDS="笔记、整理、知识库、素材库、搜索、文件读取、内容提供"
            ;;
        content)
            ROLE="文章写作、报告生成、营销文案"
            AGENT_MODEL="$MODEL_NAME"
            THINKING="on"
            SKILLS='["article-writer", "ai-daily-news"]'
            KEYWORDS="写文章、报告、文案、内容、创作"
            ;;
        moments)
            ROLE="朋友圈文案、社交媒体内容"
            AGENT_MODEL="$MODEL_NAME"
            THINKING="on"
            SKILLS='["copywriting", "social-media"]'
            KEYWORDS="朋友圈、文案、推广、分享、社交"
            ;;
        video-director)
            ROLE="视频脚本、分镜设计、拍摄指导"
            AGENT_MODEL="${MODEL_NAME}-pro"
            THINKING="on"
            SKILLS='["video-script", "storyboard"]'
            KEYWORDS="视频、脚本、分镜、拍摄、电商"
            ;;
        image-generator)
            ROLE="图片搜索、豆包图片生成"
            AGENT_MODEL="${MODEL_NAME}-pro"
            THINKING="on"
            SKILLS='["image-search", "doubao-prompt", "image-generation"]'
            KEYWORDS="图片、素材、搜索、豆包、AI 绘图、提示词"
            ;;
        seedance-director)
            ROLE="Seedance 视频提示词专家"
            AGENT_MODEL="${MODEL_NAME}-pro"
            THINKING="on"
            SKILLS='["seedance-prompt", "video-direction", "prompt-engineering"]'
            KEYWORDS="seedance、视频生成提示词、导演级提示词、AI 视频"
            ;;
    esac
    
    # 使用机器人名称作为 Agent 名称前缀
    AGENT_NAME="${ROBOT_NAME} - ${agent^}"
    
    cat >> "$CONFIG_FILE" << EOF
    {
      "name": "$AGENT_NAME",
      "role": "$ROLE",
      "model": "$AGENT_MODEL",
      "thinking": $THINKING,
      "feishu": {
        "appId": "$APP_ID",
        "appSecret": "$APP_SECRET"
      },
      "skills": $SKILLS,
      "keywords": "$KEYWORDS"
    }
EOF
done

cat >> "$CONFIG_FILE" << EOF

  ],
  "routing": {
    "enabled": true,
    "default": "${AGENTS[0]:-note}"
  }
}
EOF

echo -e "${GREEN}✅ 配置文件已生成：$CONFIG_FILE${NC}"
echo ""

# 步骤 6：生成本地文档
echo -e "${BLUE}📝 生成本地文档...${NC}"

MD_FILE="$CONFIG_DIR/bot-setup_${TIMESTAMP}.md"

cat > "$MD_FILE" << EOF
# 🦐 飞书机器人配置文档

_配置时间：$(date -Iseconds)_

---

## 📋 基本信息

| 配置项 | 值 |
|--------|-----|
| **机器人名称** | $ROBOT_NAME |
| **飞书 App ID** | $APP_ID |
| **大模型** | $MODEL_NAME |
| **Agent 数量** | ${#AGENTS[@]} |

---

## 🤖 已创建的 Agent

EOF

AGENT_NUM=1
for agent in "${AGENTS[@]}"; do
    case $agent in
        note) ROLE="知识管理、素材提供"; MODEL="${MODEL_NAME}-pro"; SKILLS="web-search, file-reading, knowledge-management" ;;
        content) ROLE="文章写作、报告生成"; MODEL="$MODEL_NAME"; SKILLS="article-writer, ai-daily-news" ;;
        moments) ROLE="朋友圈文案、社交媒体"; MODEL="$MODEL_NAME"; SKILLS="copywriting, social-media" ;;
        video-director) ROLE="视频脚本、分镜设计"; MODEL="${MODEL_NAME}-pro"; SKILLS="video-script, storyboard" ;;
        image-generator) ROLE="图片搜索、豆包生成"; MODEL="${MODEL_NAME}-pro"; SKILLS="image-search, doubao-prompt, image-generation" ;;
        seedance-director) ROLE="Seedance 提示词"; MODEL="${MODEL_NAME}-pro"; SKILLS="seedance-prompt, video-direction, prompt-engineering" ;;
    esac
    
    cat >> "$MD_FILE" << EOF
### $AGENT_NUM. ${ROBOT_NAME} - ${agent^}

- **职责**：$ROLE
- **模型**：$MODEL
- **技能**：$SKILLS

EOF
    ((AGENT_NUM++))
done

cat >> "$MD_FILE" << EOF
## 🔧 下一步操作

### 1. 在飞书开放平台配置应用权限

访问：https://open.feishu.cn

需要的权限：
- \`im:message\` - 发送消息
- \`im:message:send_as_bot\` - 以机器人身份发送消息
- \`docs:doc\` - 创建和编辑文档

### 2. 应用配置到 openclaw.json

\`\`\`bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak
\`\`\`

### 3. 重启 Gateway

\`\`\`bash
openclaw gateway restart
\`\`\`

### 4. 开始内容生成工作流

**内容生成全流程**：
1. 笔记虾搜索素材 → 2. 创作虾写文章 → 3. 图片虾生成封面 → 4. 视频虾写脚本 → 5. Seedance 虾生成提示词

---

## 📞 参考资源

| 资源 | 链接 |
|------|------|
| OpenClaw 文档 | https://docs.openclaw.ai |
| 飞书开放平台 | https://open.feishu.cn |
| Clawhub 技能站 | https://clawhub.ai/ |

---

_配置完成！开始内容生成吧！_ 🦐✨
EOF

echo -e "${GREEN}✅ 本地文档已生成：$MD_FILE${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}✅ 配置完成！${NC}"
echo "=========================================="
echo ""
echo "📁 配置文件：$CONFIG_FILE"
echo "📁 本地文档：$MD_FILE"
echo ""
echo "📋 配置摘要："
echo "  - 机器人名称：$ROBOT_NAME"
echo "  - 飞书 App ID：$APP_ID"
echo "  - 大模型：$MODEL_NAME"
echo "  - Agent 数量：${#AGENTS[@]}"
echo "  - Agent 列表：${AGENTS[*]}"
echo ""
echo "🚀 内容生成工作流："
echo "  1. 笔记虾搜索素材"
echo "  2. 创作虾写文章"
echo "  3. 图片虾生成封面"
echo "  4. 视频虾写脚本"
echo "  5. Seedance 虾生成提示词"
echo ""
echo "🚀 下一步："
echo "  1. 在飞书开放平台配置应用权限"
echo "  2. 应用配置到 openclaw.json"
echo "  3. 重启 Gateway"
echo "  4. 开始内容生成工作流"
echo ""
echo "💡 提示：也可以直接对话配置"
echo "  在飞书机器人对话中对龙虾说："
echo "  配置飞书机器人"
echo ""
