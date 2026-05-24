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
