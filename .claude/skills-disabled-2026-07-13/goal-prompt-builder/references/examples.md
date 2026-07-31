# Worked Examples

End-to-end transformations: vague user input → final `/goal` command. Use these as reference when the user's case is ambiguous about how to fill a section.

Each example shows:
1. User's initial vague request
2. Skill's interview questions
3. User's answers
4. Final rendered `/goal`
5. Audit verdict

---

## Example 1: Refactor (Node/TS project)

### User's initial request
> "Help me write a goal to refactor the auth middleware to support API key rotation"

### Interview
- **Skill**: 这是 Node/TS 还是其他？项目里有 AGENTS.md 或 CLAUDE.md 吗？
- **User**: Node/TS, has AGENTS.md, follows conventional commits
- **Skill**: scope 涉及哪些文件？现有的 auth 测试在哪里？
- **User**: 只动 src/auth/middleware.ts 和 tests/auth/middleware.test.ts
- **Skill**: 具体的"after"状态是什么？需要支持哪些场景？
- **User**: 接受 current key 和 previous key（grace window 7 天），都过期才拒绝
- **Skill**: 公开 API 是否要保持不变？
- **User**: 是

### Final `/goal`
```
/goal 重构 src/auth/middleware.ts，使其同时支持当前密钥与前一密钥（grace window 7 天）的鉴权。

Scope: 仅 src/auth/middleware.ts 与 tests/auth/middleware.test.ts。

Constraints:
  - 不修改 src/auth/index.ts 的公开导出签名。
  - 不修改 db schema、不修改 migrations/。
  - 不引入新的 npm 依赖。
  - commit message 遵循 conventional commits 格式（AGENTS.md 要求）。

Done when:
  1. src/auth/middleware.ts 同时接受 `Authorization: Bearer <current>` 
     和 `X-Auth-Previous: <rotated>` 两种 header。
  2. tests/auth/middleware.test.ts 包含 4 个新测试并全部通过：
     (a) 仅当前密钥；(b) 仅前一密钥（grace window 内）；
     (c) 仅前一密钥（grace window 已过）；(d) 双密钥都过期。
  3. `npm test -- tests/auth` 退出码 0；粘贴 test summary（应显示 ≥ 4 个新测试通过）。
  4. `npx tsc --noEmit` 退出码 0。
  5. CHANGELOG.md 在 "Unreleased" 段落新增条目描述行为变化。
  6. 最终 summary 列出所有修改文件 + 改动行数（应仅 3 个文件）。

Stop if:
  - 实现需要修改 db schema 或 migrations/。
  - 现有的 src/auth/* 测试任何一个开始失败（regression — 不要靠改测试解决）。
  - 需要新增 npm 依赖。
  - TypeScript strict 模式下出现新增的 `any` 类型（项目启用了 strict）。

Use a token budget of 80000 tokens for this goal.
```

**审计友好度：优秀 · 6 项验收 · 0 风险标记**

**关键设计选择**：
- Done when 第 2 项把"测试覆盖"翻译成 4 个具体可枚举的场景（current/grace 内/grace 外/双过期）
- Done when 第 3 项要求"粘贴 test summary"防止只看 exit code
- Stop if 第 2 条是 regression 兜底，明确禁止"改测试让自己通过"
- 80K 预算适合双文件改造 + 4 个测试

---

## Example 2: Feature (SDD-driven, Swift project)

### User's initial request
> "我用 OpenSpec 提了个收藏夹智能排序的 change，现在想用 /goal 实现"

### Interview
- **Skill**: 这是什么项目？SDD spec 路径在哪里？
- **User**: SwiftUI iOS 应用，spec 在 openspec/changes/add-favorites-smart-sort/
- **Skill**: Xcode 版本 + 测试框架？
- **User**: Xcode 26 beta, lingolearnTests 用 Swift Testing
- **Skill**: 项目有 CLAUDE.md / AGENTS.md 吗？有什么铁律？
- **User**: 有 CLAUDE.md。铁律：(1) 不改 pbxproj (2) MainActor isolation (3) 零第三方依赖 (4) 不联网

### Final `/goal`
```
/goal 严格按照 openspec/changes/add-favorites-smart-sort/ 的全部规范实现。

First action: 先逐字读取以下文件，然后回报计数：
  - openspec/changes/add-favorites-smart-sort/proposal.md
  - openspec/changes/add-favorites-smart-sort/design.md
  - openspec/changes/add-favorites-smart-sort/tasks.md
  - openspec/changes/add-favorites-smart-sort/specs/favorites-sort/spec.md
  - CLAUDE.md
报告：tasks.md 中 task 数量、spec.md 中 SHALL 数量、CLAUDE.md 中 Iron Rules 数量。
等我确认后再开始实现。

Scope: design.md 中 "MUST NOT modify" 清单严格遵守；其他 .swift 文件可改。

Constraints:
  - CLAUDE.md 的 4 条铁律是非协商：
    (a) 不修改 lingolearn.xcodeproj/project.pbxproj；
    (b) 新类型默认 MainActor-isolated；
    (c) 不引入 Swift Package；
    (d) 不引入网络请求（隐私铁律：不联网）。
  - 单元测试用 Swift Testing（@Test / #expect），不用 XCTest。
  - 修改 @Model 需要 design.md 显式允许。

Done when:
  1. tasks.md 中每一项都打勾，每项注明对应的文件路径 + 关键修改点。
  2. spec.md 中每一条 SHALL 至少有一个通过的 Swift Testing 用例覆盖，
     注明测试文件名 + 测试函数名。
  3. spec.md 中每个 GIVEN/WHEN/THEN scenario 都有对应集成测试。
  4. 既有 11 个测试（SM2Tests 7 + SeedTests 3 + AppearanceTests 1）全部通过。
  5. `xcodebuild -project lingolearn.xcodeproj -scheme lingolearn 
     -destination 'platform=iOS Simulator,name=iPhone 17' build` 退出码 0。
  6. `xcodebuild ... test -only-testing:lingolearnTests` 退出码 0；
     粘贴 test summary（新增测试数应 ≥ spec.md 中 SHALL 数）。
  7. design.md 的 "MUST NOT modify" 清单中每个文件 git diff 输出为空。

Stop if:
  - tasks.md 中某项要求修改 design.md "MUST NOT modify" 清单中的文件。
  - spec.md 中两条 SHALL 互相冲突（升级，不要自行决定）。
  - 实现需要在 project.pbxproj 中手动注册新文件（违反 CLAUDE.md）。
  - 实现需要新增 Swift Package（违反零依赖）。
  - 实现需要任何网络请求（违反隐私铁律）。
  - 既有 11 个测试中任意一个失败（regression — 不要改测试）。
  - 需要 nonisolated 修饰符（先停下汇报为什么需要）。
  - iPhone 17 模拟器不可用（先 `xcrun simctl list devices available`，由我决定）。

Use a token budget of 130000 tokens for this goal.
```

**审计友好度：优秀 · 7 项验收 · 8 项 stop-if · 0 风险标记**

**关键设计选择**：
- First action 强制先读 5 个文件 + 报数——绕开 `@filename` 引用语法的不确定性
- CLAUDE.md 的 4 条铁律每一条同时进 Constraints（告诉模型别这么做）+ Stop if（如果发现必须这么做就停）
- Done when 第 6 项要求 paste test summary，防止 xcodebuild 输出过长模型只看末尾
- Stop if 第 8 条 iPhone 17 模拟器兜底是 Xcode beta 项目特有的——并非每台机器都装

---

## Example 3: Vague request → push back instead of rendering

### User's initial request
> "我想让 Codex 把整个项目优化一下，跑得快一点"

### Interview
- **Skill**: ⚠ 我看到几处需要先澄清的地方：
  - "整个项目" 太宽——audit 期模型无法构建可枚举边界。具体哪个子系统？
  - "优化" 是主观判断——audit 期模型无法验证。具体的可观测指标是什么？比如某个端点 p99 延迟、某个测试运行时长、内存占用？
  - "跑得快一点" 没有数字——具体目标值是多少？比 baseline 提升多少 %？

  请告诉我：
  1. 哪个具体子系统 / 哪个具体场景？
  2. 你怎么测量"快"——什么命令、什么数字？
  3. 目标是从 X 提升到 Y 还是要 ≤ Z？

- **User**: 哦那这样：让搜索接口的 p95 latency 从 800ms 降到 400ms 以下，benchmark 用 scripts/bench.sh

- **Skill**: 这就好办多了。继续...

### Lesson
对模糊请求**不要直接 render** —— 那样产出的 goal 必然 audit-hostile。Skill 的价值之一就是在写之前帮用户把愿望翻译成可验证的目标。

---

## Example 4: Archaeology (Static / docs project)

### User's initial request
> "帮我让 Codex 摸清这个新接手的开源项目"

### Interview
- **Skill**: 项目类型？什么语言？
- **User**: 一个 Astro 文档站点 + 一些 React component
- **Skill**: 你想要什么形式的产出？想识别哪类东西？
- **User**: 三份文档：架构图、调用链、文档没写但代码做了的事

### Final `/goal`
```
/goal 摸清这个 Astro 文档站点的所有运作方式，输出三份文档；不修改任何源代码。

Scope: 只读 src/、components/、astro.config.* 与 README.md / CHANGELOG.md；
       可写文件仅限本 goal 创建的 3 份新 docs/*.md 文档。

Constraints:
  - 严格禁止修改任何 .astro / .tsx / .ts / .mdx 文件。
  - 不修改 astro.config.* 配置。
  - 不修改 public/ 资产。
  - 不运行 npm install / npm run build（这次只读，不验证）。
  - 引用代码必须用真实文件路径 + 行号，不要编造行号。
  - 重点指出"代码做了但 README 没写"的部分。

Done when:
  1. 新建 docs/ARCHITECTURE.md，包含：entry points、layout 文件、content 来源、
     主要 island components 列表、build pipeline 概述（mermaid 图，不超过 200 行）。
  2. 新建 docs/CALL_GRAPHS.md，包含 top 3 用户路径的渲染链：
     (a) 访问首页 → layout → content collection → render；
     (b) 访问博客列表 → 数据来源 → 分页 → 渲染；
     (c) 访问搜索页 → 客户端 island → 数据获取。
     每条链路 cite 文件:行号。
  3. 新建 docs/UNDOCUMENTED.md，列出至少 5 处"代码已实现但 README 未提及"的行为。
  4. 最终 summary 确认：本 goal 期间 git diff 仅显示 docs/ 下 3 个新文件，无其他改动。

Stop if:
  - 某个 .astro 文件无法解析（语法错误 / 编码问题）。
  - git status 显示任何 .astro / .tsx / .ts / .mdx / config 文件被修改（越界）。
  - 发现 README 与既有文档在同一事实上互相冲突（升级，让我决定）。

Use a token budget of 60000 tokens for this goal.
```

**审计友好度：优秀 · 4 项验收 · 0 风险标记**

**关键设计选择**：
- Constraints 列了具体扩展名（.astro / .tsx / .ts / .mdx）——比 "不改源码" 更精确
- Done when 第 1 项给出 mermaid 长度上限（200 行），防止图过大失去可读性
- Done when 第 4 项验证 git diff——把"没改代码"作为可机械检验的验收项
- 60K 预算偏低，因为不动代码的 goal 不需要长跑

---

## Example 5: When user wants raw template (skip the interview)

### User's initial request
> "Just give me the 5-section template, I'll fill it in myself"

### Skill response
```
/goal <objective>。

Scope: <files / subsystem>。

Constraints:
  - <hard rules>
  - <project-type defaults>

Done when:
  1. <verifiable artifact 1>
  2. <verifiable artifact 2>
  3. <verifiable artifact 3>

Stop if:
  - <mechanical condition 1>
  - <mechanical condition 2>
  - <mechanical condition 3>

Use a token budget of <N> tokens for this goal.
```

**几个填空提示**：
- Done when 至少 3 项，每项要 cite 一个文件 / 命令 / 测试
- Stop if 至少 3 项，每项要可机械检测
- 避免 "改进 / 优化 / 全部 / 彻底" 这类虚词
- Token budget：单文件 30-60K，子系统 80-120K，跨多文件 120-200K

如果你写完想让我 review，把它贴给我，我会指出 audit 友好度问题。
