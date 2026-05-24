#!/bin/bash

# 🦐 内容生成多 Agent 系统 - 跨平台自动安装脚本
# 版本：v4.0.0
# 作者：OpenClaw 来合火
# 支持：macOS, Linux, Windows (Git Bash)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🦐 内容生成多 Agent 系统 - 自动安装"
echo "版本：v4.0.0"
echo "=========================================="
echo ""

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# 检测 OpenClaw 安装路径
detect_openclaw_path() {
    local os_type=$(detect_os)
    local openclaw_path=""
    
    case "$os_type" in
        "macos")
            if [ -d "$HOME/.openclaw" ]; then
                openclaw_path="$HOME/.openclaw"
            elif [ -d "$HOME/.config/openclaw" ]; then
                openclaw_path="$HOME/.config/openclaw"
            fi
            ;;
        "linux")
            if [ -d "$HOME/.openclaw" ]; then
                openclaw_path="$HOME/.openclaw"
            elif [ -d "$HOME/.config/openclaw" ]; then
                openclaw_path="$HOME/.config/openclaw"
            fi
            ;;
        "windows")
            if [ -d "$USERPROFILE/.openclaw" ]; then
                openclaw_path="$USERPROFILE/.openclaw"
            elif [ -d "$APPDATA/openclaw" ]; then
                openclaw_path="$APPDATA/openclaw"
            fi
            ;;
    esac
    
    echo "$openclaw_path"
}

# 检测 Git
check_git() {
    if ! command -v git &> /dev/null; then
        echo -e "${RED}❌ 错误：Git 未安装${NC}"
        echo ""
        echo "请先安装 Git："
        echo "  macOS: brew install git"
        echo "  Linux: sudo apt-get install git"
        echo "  Windows: https://git-scm.com/download/win"
        exit 1
    fi
    echo -e "${GREEN}✅ Git 已安装${NC}"
}

# 主安装流程
main() {
    local os_type=$(detect_os)
    echo -e "${BLUE}🖥️  检测到操作系统：$os_type${NC}"
    
    check_git
    
    echo -e "${BLUE}🔍 检测 OpenClaw 安装路径...${NC}"
    local openclaw_path=$(detect_openclaw_path)
    
    if [ -z "$openclaw_path" ]; then
        echo -e "${RED}❌ 错误：未找到 OpenClaw 安装路径${NC}"
        echo ""
        echo "请确认 OpenClaw 已安装，或手动指定路径："
        echo "  export OPENCLAW_PATH=/path/to/openclaw"
        exit 1
    fi
    
    echo -e "${GREEN}✅ OpenClaw 路径：$openclaw_path${NC}"
    
    local skills_dir="$openclaw_path/workspace/skills"
    
    if [ ! -d "$skills_dir" ]; then
        echo -e "${YELLOW}⚠️  skills 目录不存在，正在创建...${NC}"
        mkdir -p "$skills_dir"
        echo -e "${GREEN}✅ skills 目录已创建${NC}"
    fi
    
    local repo_url="https://github.com/jiebao360/content-creation-multi-agent.git"
    local target_dir="$skills_dir/content-creation-multi-agent"
    
    if [ -d "$target_dir" ]; then
        echo -e "${YELLOW}⚠️  技能已存在，正在更新...${NC}"
        cd "$target_dir"
        git pull origin main
    else
        echo -e "${BLUE}📥 正在克隆仓库...${NC}"
        git clone "$repo_url" "$target_dir"
    fi
    
    echo -e "${GREEN}✅ 技能已安装到：$target_dir${NC}"
    
    if [[ "$os_type" == "macos" ]] || [[ "$os_type" == "linux" ]]; then
        echo -e "${BLUE}🔧 添加执行权限...${NC}"
        chmod +x "$target_dir/scripts/"*.sh
        echo -e "${GREEN}✅ 执行权限已添加${NC}"
    fi
    
    echo ""
    read -r -p "是否立即运行配置脚本？(y/n) " -n 1 -e
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$target_dir"
        bash scripts/configure-bot.sh
    else
        echo -e "${BLUE}💡 提示：稍后可以手动运行配置脚本${NC}"
        echo "  cd $target_dir"
        echo "  bash scripts/configure-bot.sh"
    fi
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✅ 安装完成！${NC}"
    echo "=========================================="
    echo ""
    echo "📁 技能位置：$target_dir"
    echo ""
    echo "🚀 下一步："
    echo "  1. 运行配置脚本（如果刚才没运行）"
    echo "     cd $target_dir"
    echo "     bash scripts/configure-bot.sh"
    echo ""
    echo "  2. 重启 Gateway"
    echo "     openclaw gateway restart"
    echo ""
    echo "  3. 开始内容生成工作流"
    echo ""
}

main
