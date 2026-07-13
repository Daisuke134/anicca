# Scenario Skeletons

Loaded by `goal-prompt-builder` after the user picks a scenario in Step 2. Each section provides a fillable skeleton plus the design rationale (so Claude knows *why* the skeleton looks the way it does, and can adapt intelligently when the user's actual case doesn't fit perfectly).

Use only the scenario the user picked. Don't blend.

---

## § Refactor (重构 — 单子系统改造)

### When this fits
- Changes confined to 1-3 files or a single subsystem
- The change has a crisp "after" state (specific behavior change, specific test passing)
- Risk is contained — public API surface is preserved

### Skeleton
```
/goal <重构动作>，<具体的 after 状态>。

Scope: <具体目录或文件 list>。

Constraints:
  - 不修改 <相邻但不相关的子系统>。
  - 公开 API（<具体导出文件>）签名保持不变。
  - <项目类型默认约束 — 从 references/project-types.md 取>
  - 不引入新依赖。

Done when:
  1. <文件 X> 实现了 <具体行为>。
  2. <测试文件 Y> 包含 N 个新用例并全部通过：(a) (b) (c)。
  3. <精确的测试命令> 退出码 0；粘贴 test summary。
  4. <build / type-check 命令> 退出码 0。
  5. CHANGELOG.md（如果存在）在 "Unreleased" 段落新增条目。
  6. 最终 summary 列出每个修改文件 + 改动行数。

Stop if:
  - 实现需要修改 <显式禁区>。
  - 现有测试开始失败（regression — 不要靠改测试解决）。
  - 需要新增依赖 / 升级语言版本。
  - <项目类型默认 stop-if>

Use a token budget of <60-100K> tokens for this goal.
```

### Rationale
- **Scope 必须先于 Constraints**: scope 圈"动什么"，constraints 圈"不动什么"——前者是邀请，后者是边界
- **Done when 5 项左右最稳**: 少于 3 项 audit 抓不住，多于 8 项模型容易遗漏
- **测试命令必须完整**: "测试通过" 是代理信号，"`npx tsc --noEmit && npm test -- src/auth` 退出码 0 + paste summary" 才是证据
- **Stop if 第 1 条永远是"修改禁区"**: 这是最常见的越界路径

### Token budget guidance
- 单文件 ≈ 30-60K
- 双文件 + 测试 ≈ 60-100K
- 跨 3+ 文件 ≈ 100-150K

---

## § Feature (新功能实现 — 已有 SDD spec)

### When this fits
- 用户已经有 OpenSpec / SpecKit / 自写的 spec 文档
- Spec 用 SHALL / Acceptance / Scenarios 这种结构化形式
- 任务是"按 spec 实现"，不是"想清楚要什么"

### Skeleton
```
/goal 严格按照 <spec 路径> 的全部规范实现。

First action: 先逐字读取以下文件，然后回报计数：
  - <spec 路径>/proposal.md
  - <spec 路径>/design.md
  - <spec 路径>/tasks.md
  - <spec 路径>/specs/<capability>/spec.md
  - AGENTS.md（如果存在）
报告：tasks.md 中 task 数量、spec.md 中 SHALL 数量、识别到的 AGENTS.md 关键约束条数。
等我确认后再开始实现。

Scope: design.md 中 "MUST NOT modify" 清单严格遵守；其他文件可改。

Constraints:
  - AGENTS.md 的所有 Iron Rules 是非协商约束。
  - <项目类型默认约束>
  - 不引入未在依赖清单中声明的新依赖。
  - 修改 @Model / data layer 需要 design.md 显式允许，否则禁止。

Done when:
  1. tasks.md 中每一项都打勾，每项注明对应的文件路径 + 关键修改点。
  2. spec.md 中每一条 SHALL 至少有一个通过的测试覆盖，注明测试文件 + 测试名称。
  3. spec.md 中每一个 GIVEN/WHEN/THEN scenario 都有对应的集成测试。
  4. <build 命令> 退出码 0，粘贴 build summary。
  5. <test 命令> 退出码 0，粘贴 test summary（新增测试数应 ≥ spec.md 中 SHALL 数）。
  6. design.md 的 "MUST NOT modify" 清单中每个文件 git diff 输出为空。
  7. README.md（如有要求）追加描述新增能力。

Stop if:
  - tasks.md 中某项要求修改 design.md "MUST NOT modify" 清单中的文件。
  - spec.md 中两条 SHALL 互相冲突（升级，不要自行决定优先级）。
  - 实现需要新增依赖。
  - 现有测试开始失败。
  - <项目类型默认 stop-if>

Use a token budget of <100-150K> tokens for this goal.
```

### Rationale
- **First action 是"先读 + 报数"**: 这一段是 SDD 模式的 killer 设计。绕开 `@filename` 引用语法是否被 Codex 解析的不确定性，强制模型在动手前**显式回报**它读到了多少内容。如果回报的数字对不上，立刻 `/goal pause` 排查，比让它跑半天才发现没读到 spec 安全得多
- **Done when 第 1-3 项是"映射 1:1"**: SHALL → 测试 / Scenario → 集成测试 / task → 文件——这种 1:1 映射是 SDD + /goal 配合的核心价值
- **Stop if 第 2 条"SHALL 冲突 → 升级"**: 这种冲突应该回到 spec 阶段解决，不应该让模型独断
- **预算偏高（100-150K）**: SDD 实现通常涉及多文件 + 多测试，预算给足

### Variant: 没有 SDD spec 的"新功能"
如果用户只有自然语言需求，没有 spec 文档，应该建议：
- 先用 OpenSpec 提案（`/opsx:propose`）生成 spec
- 再用本 skeleton

或者降级用 § Refactor 的 skeleton + 加大 scope。

---

## § Batch (批量任务 — 修 bug、补测试、批量重命名)

### When this fits
- 任务是"做 N 件相似的事"
- N 是已知的或可枚举的
- 每件事的"完成"标准一致

### Skeleton
```
/goal <批量动作> N 个 <对象>，<来自哪里 / 怎么枚举>。

Scope: <每件事的修改范围>。每件事一个 commit。

Constraints:
  - N 个对象必须来自 <可枚举来源>（如 GitHub issue tracker labels=bug+priority=high）。
  - 每件事的修改不能跨界（一个 commit 只动相关文件）。
  - 不合并、不关闭范围之外的其他对象。
  - <项目类型默认约束>
  - commit message 格式：<具体格式>。

Done when:
  1. N 个对象各自关联一个独立的 commit。
  2. 每件事在 <测试目录> 下有对应的 <测试 / 验证>，全部通过。
  3. <test 命令> 退出码 0，新增测试数 ≥ N。
  4. CHANGELOG.md 列出 N 条，每条附引用。
  5. 最终 summary 是一张表格，列出：对象号 / 一句话描述 / 修改文件 / 测试 / commit hash。

Stop if:
  - 某个对象在过程中状态变化（被关闭 / 被他人改动）。
  - 某件事需要破坏性变更（API 签名 / schema 变更）。
  - 现有的相关测试开始失败。
  - 某个对象实际不可复现 / 不存在。
  - 完成 N 件后 review 发现 < M 件实际正确（M 由用户定，通常 = N）。

Use a token budget of <100-150K> tokens for this goal.
```

### Rationale
- **N 必须是数字**: "修一些 bug" 是愿望，"修 5 个 bug" 是循环。模型在续跑期会拿这个 N 当 audit checklist 的长度
- **可枚举来源**: 强制让 N 的边界来自外部事实（issue tracker / 文件列表 / 测试覆盖报告），而不是模型主观判断
- **commit 隔离**: "一件事一个 commit" 让回滚边界明确，也是 audit 时的天然 checkpoint
- **Stop if 第 5 条 "review 后 < M 件正确"**: 这是 batch 任务特有的兜底——避免"完成 5 件但有 3 件错了"的情况被宣告 done

---

## § Archaeology (代码考古 — 只研究不动手)

### When this fits
- 接手陌生项目想摸清架构
- 想识别"代码做了但文档没写"的部分
- 想生成 onboarding 文档

### Skeleton
```
/goal 摸清 <项目名> 的所有运作方式，输出 <N> 份文档；不修改任何源代码。

Scope: 只读 <源代码目录>；可写文件仅限本 goal 创建的 N 份新 .md 文档。

Constraints:
  - 严格禁止修改任何 <源代码目录> 下的现有文件。
  - 不修改 <资产文件，如 words.json / 配置文件>（这些是产品资产）。
  - 不运行任何会修改环境的命令（npm install / cargo build 等）。
  - 引用代码必须用真实文件路径 + 行号，不要编造。
  - 重点指出"代码做了但 README / docs 没写"的部分。

Done when:
  1. 新建 docs/ARCHITECTURE.md，包含：entry points、primary modules、外部依赖、数据流图（mermaid）。
  2. 新建 docs/CALL_GRAPHS.md，包含 top N 用户路径的调用链，每条 cite 文件:行号。
  3. 新建 docs/UNDOCUMENTED.md，列出 ≥ 5 处"代码已实现但 README 未提及"的行为。
  4. 最终 summary 确认：本 goal 期间 git diff 仅显示 docs/ 下 N 个新文件，无源码改动。

Stop if:
  - 某个文件需要外部工具才能解析（加密 / 二进制 / 专有格式）。
  - git status 显示任何源码文件被修改（越界，立即停止）。
  - 发现两份既有文档在同一事实上互相冲突（升级，让用户决定）。

Use a token budget of <50-80K> tokens for this goal.
```

### Rationale
- **Constraints 比 Scope 更长更严**: 这种 goal 的核心价值是"不动代码"，禁区清单必须详尽
- **"引用必须用真实路径 + 行号"**: 防止模型编造好看的报告。Done when 应该至少抽查 1 项 cite 是否真实（人工 review 时）
- **Done when 最后一项验证 git diff**: 把"没改代码"显式作为可机械检验的验收项
- **预算偏低（50-80K）**: 不动代码的 goal 不需要长跑，主要消耗在 read 上

---

## § UI Audit (对照文档审实现)

### When this fits
- 项目有 README / spec / 设计稿描述了"应该是什么样"
- 想 audit "实际实现"和"宣称行为"的差距
- 不修改代码，只生成报告

### Skeleton
```
/goal 对照 <宣称来源> 描述的所有功能，audit <项目> 的实际实现，
       生成一份差距报告；不修改任何代码。

Scope: 只读 <UI 代码目录>、<宣称来源文件>；可写文件仅限本 goal 创建的 1 份 docs/<NAME>_AUDIT.md。

Constraints:
  - 不修改任何源代码。
  - 不启动 / 不运行（这次是静态 audit，运行验证留给后续）。
  - 不"宣称"功能存在或不存在——必须 cite 文件路径 + 行号。
  - 评估口径基于 <宣称来源> 的具体内容，不引入额外预期。

Done when:
  1. 新建 docs/<NAME>_AUDIT.md，包含 N 个段落（每个对应一个被 audit 的单元）。
  2. 每个段落有 4 个子段：(a) 宣称功能逐字摘录 (b) 实际实现位置 cite 行号 
     (c) 实现状态 ✅/⚠/❌ + 1 句理由 (d) 风险点（最多 5 条）。
  3. 文档末尾一张总览表：被审单元 × 状态计数。
  4. 文档末尾给出"如果只能改 1 处，建议先改哪里"+ 1 句理由。
  5. 最终 summary 确认：仅创建 docs/<NAME>_AUDIT.md，无其他 git diff。

Stop if:
  - 宣称的某项功能在源码中找不到任何相关文件（先列出搜索过的关键字，由用户决定是否真的缺失）。
  - 出现需要"运行才能判断"的 case（如动画行为、异步交互）—— 标 ⚠ 并说明"需要运行验证"，不要凭空给 ✅ 或 ❌。
  - git status 显示除报告之外的任何变化。

Use a token budget of <60-90K> tokens for this goal.
```

### Rationale
- **Done when 第 2 项把"输出格式"写死**: 4 个子段是 audit 的具体证据靶子。如果让模型自由发挥结构，结果会五花八门
- **Stop if "需要运行才能判断" → ⚠**: 这是反 false-completion 的关键。强制模型主动承认"我没运行过"，而不是凭代码静态分析硬给结论
- **总览表 + "建议先改哪里"**: 这两个是 audit 报告的可消费性指标——没有它们，报告变成纯陈列

---

## § Gatekeeper (守门员 — 评估能否合并)

### When this fits
- 有 N 个 PR / 分支需要 review
- 评估输出是判断而非代码
- 守门员模式：只 review 不修改

### Skeleton
```
/goal 评估 <分支 / PR list> 是否可以合入 <目标分支>；不 push、不 merge、不修改代码。

Scope: 只读这 N 个 <分支 / PR>；可写文件仅限新建的 REVIEW_*.md。

Constraints:
  - 不执行 git push / merge / rebase。
  - 不修改任何 <被 review 项目的源码文件>。
  - 每个 <分支 / PR> 必须独立 review，不跨引用。
  - 评估必须基于实际 diff + 测试运行结果，不能仅凭 commit message 判断。

Done when:
  1. 为每个 <分支 / PR> 生成独立报告 REVIEW_<name>.md，包含：
     (a) diff 摘要：文件数 / 增删行数；
     (b) 每个修改文件的风险等级（low / medium / high）+ 1 句话理由；
     (c) 测试运行结果：cite 测试文件 + 退出码；
     (d) 缺失项清单（缺文档 / 缺迁移 / 缺 changelog 等），最多 5 条；
     (e) 最终判定：ready / needs-work / blocked，blocker 不超过 3 条。
  2. 每份报告末尾附"如果决定合并，建议的下一步操作"3 条以内。
  3. 最终 summary 是一张表格，对比 N 个 <分支 / PR> 的最终判定。

Stop if:
  - 某 <分支 / PR> diff 超过 2000 行（自动 review 范围之外，转人工）。
  - 某 <分支 / PR> 需要新依赖才能跑测试（可能引入未明示的依赖，需人工确认）。
  - 测试运行需要环境变量 / 凭据未在 .env.example 中声明。
  - <分支 / PR> 在 review 过程中被 force-push（diff 已变化）。

Use a token budget of <70-100K> tokens for this goal.
```

### Rationale
- **每份报告独立**: 跨 PR 引用会让 audit 失焦——一份报告对应一个判断
- **"基于实际 diff + 测试结果，不能仅凭 commit message"**: 防止模型偷懒只读 commit message
- **判定限定为 3 个值**: ready / needs-work / blocked。开放式判定（"看起来还行"）会让总览表失去意义
- **Stop if 第 4 条"force-push"**: 长跑 review 期间 PR 可能变化，这是 batch / gatekeeper 类型特有的兜底

---

## § Custom (自定义)

如果用户的场景不在以上 6 种：

1. 不要硬塞进某个 skeleton
2. 用 SKILL.md 主体的"5 段式"裸模板
3. 多花一点时间问 Done when 和 Stop if——这两个是定制 goal 最容易出问题的地方
4. 至少 3 项 acceptance + 至少 3 项 stop-if，否则不要 render

通用裸模板（无场景特化）：

```
/goal <objective>。

Scope: <files / subsystem / area>。

Constraints:
  - <hard rules>
  - <项目类型默认约束>

Done when:
  1. <verifiable artifact>
  2. <verifiable artifact>
  3. <verifiable artifact>

Stop if:
  - <mechanical condition>
  - <mechanical condition>
  - <mechanical condition>

Use a token budget of <N> tokens for this goal.
```
