#!/bin/bash

# 🦐 内容生成多 Agent 技能包 - 自动安装脚本
# 版本：v3.0.0
# 作者：OpenClaw 社区

set -e

SKILL_NAME="content-creation-multi-agent"
SKILL_DIR="$HOME/.openclaw/workspace/skills/$SKILL_NAME"
CONFIG_DIR="$HOME/.openclaw/workspace-main/content-creation-configs"
AGENTS_DIR="$SKILL_DIR/agents"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🦐 内容生成多 Agent 技能包 - 自动安装"
echo "版本：v3.0.0"
echo "=========================================="
echo ""

# 步骤 1：创建技能目录
echo -e "${BLUE}📁 创建技能目录...${NC}"
mkdir -p "$SKILL_DIR/scripts"
mkdir -p "$AGENTS_DIR"
mkdir -p "$CONFIG_DIR"
echo -e "${GREEN}✅ 目录创建完成${NC}"
echo "  - 技能目录：$SKILL_DIR"
echo "  - Agent 配置目录：$AGENTS_DIR"
echo "  - 配置输出目录：$CONFIG_DIR"
echo ""

# 步骤 2：创建 Agent 配置文件
echo -e "${BLUE}📝 创建 Agent 配置文件...${NC}"

# 第二大脑笔记虾
cat > "$AGENTS_DIR/note-shrimp.json" << 'EOF'
{
  "name": "第二大脑笔记虾",
  "role": "知识管理与内容素材提供",
  "model": "doubao-pro",
  "thinking": "on",
  "skills": ["{{profile.lateness.stakeholders.channel}}-search", "file-reading", "knowledge-management", "content-curation", "material-supply"],
  "keywords": "笔记、整理、知识库、素材库、浏览器搜索、文件读取、内容提供",
  "output_format": "markdown",
  "{{profile.lateness.stakeholders.channel}}_search": {
    "enabled": true,
    "method": "open_{{profile.lateness.stakeholders.channel}}",
    "description": "通过打开电脑浏览器搜索网页获取资料"
  },
  "integrations": {
    "supply_to": ["moments-shrimp", "content-creator-shrimp"]
  },
  "file_access": {
    "enabled": true,
    "paths": ["~/.openclaw/workspace-main/", "~/Documents/", "~/Downloads/"]
  }
}
EOF
echo "  ✅ 第二大脑笔记虾配置已创建"

# 朋友圈创作虾
cat > "$AGENTS_DIR/moments-shrimp.json" << 'EOF'
{
  "name": "朋友圈创作虾",
  "role": "朋友圈文案创作",
  "model": "doubao",
  "thinking": "on",
  "skills": ["copywriting", "social-media"],
  "keywords": "朋友圈、文案、推广、分享、社交",
  "output_format": "text",
  "features": ["文案创作", "配图建议", "发布时间", "互动话术"]
}
EOF
echo "  ✅ 朋友圈创作虾配置已创建"

# 电商视频导演虾
cat > "$AGENTS_DIR/video-director-shrimp.json" << 'EOF'
{
  "name": "电商视频导演虾",
  "role": "电商视频脚本创作",
  "model": "doubao-pro",
  "thinking": "on",
  "skills": ["video-script", "storyboard"],
  "keywords": "视频、脚本、分镜、拍摄、电商",
  "output_format": "markdown",
  "features": ["脚本编写", "分镜设计", "拍摄建议", "剪辑指导"]
}
EOF
echo "  ✅ 电商视频导演虾配置已创建"

# 通用内容创作虾
cat > "$AGENTS_DIR/content-creator-shrimp.json" << 'EOF'
{
  "name": "通用内容创作虾",
  "role": "通用内容创作",
  "model": "doubao",
  "thinking": "on",
  "skills": ["writing", "editing"],
  "keywords": "文章、报告、文案、邮件、创作",
  "output_format": "markdown",
  "features": ["多文体写作", "内容优化", "风格调整", "校对润色"]
}
EOF
echo "  ✅ 通用内容创作虾配置已创建"

# 图片素材生成虾
cat > "$AGENTS_DIR/image-generator-shrimp.json" << 'EOF'
{
  "name": "图片素材生成虾",
  "role": "图片搜索 + 豆包图片生成",
  "model": "doubao-pro",
  "thinking": "on",
  "skills": ["image-search", "doubao-prompt", "image-generation"],
  "keywords": "图片、素材、搜索、豆包、AI 绘图、提示词",
  "output_format": "image+markdown",
  "doubao_rules": {
    "prompt_count": 5,
    "image_count": 5,
    "search_count": 5
  }
}
EOF
echo "  ✅ 图片素材生成虾配置已创建"

# 电商 seedacne 导演虾
cat > "$AGENTS_DIR/seedacne-director-shrimp.json" << 'EOF'
{
  "name": "电商 seedacne 导演虾",
  "role": "Seedance 视频生成提示词专家",
  "model": "doubao-pro",
  "thinking": "on",
  "skills": ["seedance-prompt", "video-direction", "prompt-engineering"],
  "keywords": "seedance、视频生成提示词、导演级提示词、AI 视频、提示词工程",
  "output_format": "seedance-prompt",
  "seedance_rules": {
    "format": "导演级提示词格式",
    "structure": ["场景描述", "镜头语言", "角色动作", "光影效果", "氛围情绪", "技术参数"]
  }
}
EOF
echo "  ✅ 电商 seedacne 导演虾配置已创建"

echo -e "${GREEN}✅ Agent 配置文件创建完成${NC}"
echo ""

# 步骤 3：创建脚本文件
echo -e "${BLUE}📝 创建脚本文件...${NC}"

# 创建 Agent 选择脚本
cat > "$SKILL_DIR/scripts/select-agent.sh" << 'SCRIPT'
#!/bin/bash
echo "=========================================="
echo "🦐 选择内容创作 Agent"
echo "=========================================="
echo ""
echo "请选择要使用的 Agent："
echo "  [1] 第二大脑笔记虾 - 知识管理、笔记整理"
echo "  [2] 朋友圈创作虾 - 朋友圈文案创作"
echo "  [3] 电商视频导演虾 - 电商视频脚本"
echo "  [4] 通用内容创作虾 - 通用内容创作"
echo "  [5] 图片素材生成虾 - 图片素材生成"
echo "  [6] 电商 seedacne 导演虾 - Seedance 提示词"
echo ""
read -r -p "选择 (1-6): " choice

case $choice in
    1) echo "已选择：第二大脑笔记虾" ;;
    2) echo "已选择：朋友圈创作虾" ;;
    3) echo "已选择：电商视频导演虾" ;;
    4) echo "已选择：通用内容创作虾" ;;
    5) echo "已选择：图片素材生成虾" ;;
    6) echo "已选择：电商 seedacne 导演虾" ;;
    *) echo "无效选择" ; exit 1 ;;
esac
SCRIPT
chmod +x "$SKILL_DIR/scripts/select-agent.sh"
echo "  ✅ Agent 选择脚本已创建"

# 创建测试脚本
cat > "$SKILL_DIR/scripts/test.sh" << 'SCRIPT'
#!/bin/bash
SKILL_DIR="$HOME/.openclaw/workspace/skills/content-creation-multi-agent"
echo "检查技能文件..."
[ -f "$SKILL_DIR/SKILL.md" ] && echo "✅ SKILL.md 存在" || echo "❌ SKILL.md 缺失"
[ -f "$SKILL_DIR/_meta.json" ] && echo "✅ _meta.json 存在" || echo "❌ _meta.json 缺失"
[ -f "$SKILL_DIR/README.md" ] && echo "✅ README.md 存在" || echo "❌ README.md 缺失"
echo "检查 Agent 配置..."
for agent in note-shrimp moments-shrimp video-director-shrimp content-creator-shrimp image-generator-shrimp seedacne-director-shrimp; do
    [ -f "$SKILL_DIR/agents/$agent.json" ] && echo "✅ $agent.json 存在" || echo "❌ $agent.json 缺失"
done
echo "✅ 检查完成"
SCRIPT
chmod +x "$SKILL_DIR/scripts/test.sh"
echo "  ✅ 测试脚本已创建"

echo -e "${GREEN}✅ 脚本文件创建完成${NC}"
echo ""

# 步骤 4：添加执行权限
echo -e "${BLUE}🔧 添加执行权限...${NC}"
chmod +x "$SKILL_DIR/scripts/"*.sh 2>/dev/null || true
echo -e "${GREEN}✅ 权限设置完成${NC}"
echo ""

# 步骤 5：验证文件
echo -e "${BLUE}🧪 验证文件完整性...${NC}"
bash "$SKILL_DIR/scripts/test.sh"
echo ""

# 步骤 6：重启 Gateway
echo -e "${BLUE}🔄 重启 Gateway...${NC}"
openclaw gateway restart || {
    echo -e "${YELLOW}⚠️  Gateway 重启失败，请手动重启${NC}"
    echo "命令：openclaw gateway restart"
}
echo -e "${GREEN}✅ Gateway 已重启${NC}"
echo ""

# 步骤 7：显示使用说明
echo "=========================================="
echo -e "${GREEN}✅ 安装完成！${NC}"
echo "=========================================="
echo ""
echo "📁 技能位置：$SKILL_DIR"
echo "📁 Agent 配置：$AGENTS_DIR"
echo ""
echo "🚀 使用方法："
echo ""
echo "方式一：对话调用"
echo "  笔记虾，帮我搜索全网关于 AI 视频生成的最新资料"
echo "  朋友圈虾，帮我写一条产品推广文案"
echo "  视频导演虾，帮我写一个产品展示视频脚本"
echo "  创作虾，帮我写一篇产品介绍文章"
echo "  素材虾，帮我生成产品封面图，5 张"
echo "  seedacne 导演虾，帮我生成 Seedance 视频提示词"
echo ""
echo "方式二：选择 Agent"
echo "  cd $SKILL_DIR"
echo "  bash scripts/select-agent.sh"
echo ""
echo "🎉 开始创作吧！"
echo ""
