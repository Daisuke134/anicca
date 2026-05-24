# 🚀 自动发布脚本使用说明

> 使用$GITHUB_TOKEN 环境变量安全发布

**版本**：v3.0.0  
**更新时间**：2026-03-16

---

## ⚠️ 安全警告

**永远不要在脚本或命令中硬编码 Token！**

✅ **正确做法**：使用 `$GITHUB_TOKEN` 环境变量  
❌ **错误做法**：直接在脚本中写 `ghp_xxxxx`

---

## 🔑 配置步骤

### 步骤 1：创建 Personal Access Token

1. **访问**：https://github.com/settings/tokens
2. **点击**："Generate new token (classic)"
3. **填写**：
   - Note：`OpenClaw Skills`
   - Expiration：90 天或更长
4. **选择权限**：
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
5. **点击**："Generate token"
6. **复制 Token**（格式：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）

⚠️ **重要**：Token 只会显示一次，立即复制保存！

---

### 步骤 2：配置环境变量

#### 方式一：永久配置（推荐）

```bash
# 1. 添加到 ~/.zshrc
echo 'export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' >> ~/.zshrc

# 2. 使配置生效
source ~/.zshrc

# 3. 验证
echo $GITHUB_TOKEN
# 应该输出你的 Token
```

#### 方式二：临时配置（当前终端会话）

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 步骤 3：使用自动发布脚本

```bash
# 1. 进入技能包目录
cd ~/.openclaw/workspace/skills/content-creation-multi-agent

# 2. 运行自动发布脚本
bash scripts/auto-publish.sh
```

**脚本会自动**：
1. ✅ 检查 `$GITHUB_TOKEN` 环境变量
2. ✅ Git 提交所有更改
3. ✅ 推送到 GitHub（使用 Token）
4. ✅ 准备 Clawhub 提交
5. ✅ 生成发布报告

---

## 🔒 安全机制

### 脚本中的安全实践

**✅ 使用环境变量**：
```bash
# 检查 Token 是否设置
if [ -z "$GITHUB_TOKEN" ]; then
    echo "错误：GITHUB_TOKEN 环境变量未设置"
    exit 1
fi

# 使用 Token 推送
GIT_PASSWORD=$GITHUB_TOKEN git push -u origin main
```

**❌ 不要硬编码 Token**：
```bash
# ❌ 错误示例
git remote set-url origin https://ghp_实际_TOKEN@github.com/...

# ✅ 正确示例
git remote set-url origin https://github.com/用户名/仓库.git
GIT_PASSWORD=$GITHUB_TOKEN git push
```

---

## 📋 完整发布流程

```bash
# 1. 配置环境变量（只需做一次）
echo 'export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx' >> ~/.zshrc
source ~/.zshrc

# 2. 以后发布只需运行
cd ~/.openclaw/workspace/skills/content-creation-multi-agent
bash scripts/auto-publish.sh
```

---

## 🐛 常见问题

### Q1: Token 不生效？

**解决方案**：
```bash
# 1. 检查 Token 是否设置
echo $GITHUB_TOKEN

# 2. 如果没有输出，重新配置
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# 3. 再次运行脚本
bash scripts/auto-publish.sh
```

### Q2: 推送失败？

**解决方案**：
```bash
# 1. 检查 remote 配置
git remote -v

# 2. 重新设置 remote
git remote set-url origin https://github.com/jiebao360/content-creation-multi-agent.git

# 3. 再次推送
GIT_PASSWORD=$GITHUB_TOKEN git push -u origin main
```

### Q3: 如何撤销 Token？

**解决方案**：
1. 访问：https://github.com/settings/tokens
2. 找到对应的 Token
3. 点击 "Delete"
4. 生成新 Token
5. 更新 `~/.zshrc` 中的配置

---

## 📞 参考资源

| 资源 | 链接 |
|------|------|
| GitHub Token 设置 | https://github.com/settings/tokens |
| Git Credential Helper | https://git-scm.com/docs/git-credential |
| 自动发布脚本 | `scripts/auto-publish.sh` |

---

**最后更新**：2026-03-16  
**版本**：v3.0.0
