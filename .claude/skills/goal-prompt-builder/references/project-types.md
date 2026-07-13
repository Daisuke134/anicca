# Project Type Defaults

This file is loaded by the `goal-prompt-builder` skill once the project type is known. Each section provides:

- **Test command**: full xcodebuild/npm/cargo invocation, no abbreviations
- **Build / type-check command**: same
- **Default Stop-if bullets**: what to add to every Stop-if for this project type
- **False-completion traps**: known ways the project type lets the model "pass" audit while still being broken
- **AGENTS.md / CLAUDE.md probe questions**: type-specific things to look for

Use the section matching the user's project type. Don't blend sections.

---

## Node / TypeScript

### Test command
```
npm test
```
or if more specific:
```
npm test -- <path-pattern>
```
For CI mode (no watch):
```
npm test -- --watchAll=false
```

### Build / type-check
```
npx tsc --noEmit
```
or if there's a build script:
```
npm run build
```

### Default Stop-if bullets
- `package.json` 中需要新增依赖（`npm install` would be required）
- `node_modules/` 损坏，需要 `rm -rf node_modules && npm ci` 才能继续
- 现有测试开始失败（regression — 不要靠改测试 / 加 `.skip` 解决）
- TypeScript strict 模式下出现 `any` 类型新增（如 tsconfig 启用了 strict）

### False-completion traps
- Jest 的 `it.skip` / `describe.skip` 被默认接受为"测试通过"——goal 应明确"skip 计数必须为 0"
- 如果项目用 jiti / esbuild-loader / ts-node 缓存：改 `.ts` 后跑测试前必须清缓存（`rm -rf node_modules/.cache`），否则跑的是旧版本
- monorepo 下 `npm test` 可能只跑当前 workspace，需要确认 `--workspaces` 是否生效

### Probe questions for AGENTS.md / CLAUDE.md
- 是否锁定 Node 版本（`engines` field、`.nvmrc`）？
- 是否禁止某些 npm 包（lock file 里有 deny list）？
- 是否要求 commit message 遵循特定格式（conventional commits）？

---

## Python

### Test command
```
pytest -q
```
or for specific path:
```
pytest -q tests/<path>
```
or with coverage:
```
pytest -q --cov=<package> --cov-fail-under=80
```

### Build / type-check
```
mypy <package>
```
or for ruff users:
```
ruff check . && ruff format --check .
```

### Default Stop-if bullets
- 需要新增 `requirements.txt` / `pyproject.toml` 依赖（`pip install` would be required）
- 需要修改 Python 版本要求（`python_requires`）
- 现有测试开始失败（regression — 不要靠 `@pytest.mark.skip` 跳过）
- 引入会泄漏的全局状态（修改 module-level 变量）

### False-completion traps
- `pytest.mark.skip` / `pytest.mark.xfail` 被默认计入"测试通过"——goal 应明确"skipped 计数必须为 0"
- 异步测试如果没装 `pytest-asyncio` 会被静默跳过——goal 应明确"async 测试实际执行计数 ≥ N"
- `conftest.py` 修改可能影响其他测试，但不会立刻报错——goal 应禁止改 `conftest.py` 除非显式需要

### Probe questions
- 用什么 Python 版本管理（pyenv / conda / uv）？
- 是否有 `pre-commit` hooks 强制 lint / format？
- 是否区分 dev / prod dependencies？

---

## Swift / iOS

### Test command
```
xcodebuild -project <project>.xcodeproj -scheme <scheme> \
  -destination 'platform=iOS Simulator,name=iPhone 17' \
  test -only-testing:<TestTarget>
```
For Swift Package Manager projects:
```
swift test
```

### Build
```
xcodebuild -project <project>.xcodeproj -scheme <scheme> \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
```

### Default Stop-if bullets
- 修改 `<project>.xcodeproj/project.pbxproj`（如果项目用 PBXFileSystemSynchronizedRootGroup，绝对禁止手动改）
- 引入新的 Swift Package（违反"零依赖"原则的项目）
- 需要 nonisolated 修饰符（如果项目设置了 SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor，先停下汇报为什么）
- iPhone 17 模拟器不可用（先 `xcrun simctl list devices available`，由用户决定换哪个 destination）
- 现有测试开始失败（regression — 不要改测试）

### False-completion traps
- Swift Testing 的 `@Test(.disabled())` 不计入失败但不再执行——goal 应明确"无 disabled 测试新增"
- XCTest 的 `XCTSkip` 同上
- iOS 测试有时因为模拟器启动失败"挂起"而不是失败——goal 应要求 paste 完整 test summary 而不是只看 exit code
- xcodebuild 的 stdout 极长，模型容易只看末尾——goal 应要求 cite 测试名而不是"all passed"

### Probe questions
- Xcode beta 版本号是多少？
- 测试框架：Swift Testing（`@Test`）还是 XCTest（`XCTestCase`）？两个目录可能用不同的
- 是否启用 SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor？
- 是否禁止第三方依赖（README 常见铁律）？

---

## Go

### Test command
```
go test ./...
```
For specific package:
```
go test ./<pkg>/...
```
With race detector:
```
go test -race ./...
```

### Build
```
go build ./...
```
Or for vet/lint:
```
go vet ./... && staticcheck ./...
```

### Default Stop-if bullets
- 需要修改 `go.mod` 添加新依赖（`go get` would be required）
- `go.sum` 出现意外变动（除了添加同意的依赖）
- 现有测试开始失败（regression — 不要 `t.Skip` 解决）
- 数据竞争被引入（`go test -race` 检测到新的 race）

### False-completion traps
- `t.Skip` 默认计入"通过"——goal 应明确"skipped 计数必须为 0"
- table-driven test 中某个 case 被注释掉看起来像通过——goal 应禁止"注释 test case 来让自己通过"
- `_test.go` 里的 helper 函数被改可能影响多个测试但不立刻报错

### Probe questions
- Go 版本是多少（`go.mod` 第一行）？
- 是否要求 `gofmt` 干净？
- 是否使用 generics（Go 1.18+）？
- 是否有内部 packages（`internal/`）需要避免暴露？

---

## Rust

### Test command
```
cargo test --all-features
```
For specific crate in workspace:
```
cargo test -p <crate-name>
```

### Build
```
cargo check --all-targets
```
Stricter:
```
cargo clippy --all-targets -- -D warnings
```

### Default Stop-if bullets
- 需要修改 `Cargo.toml` 添加新依赖（`cargo add` would be required）
- `Cargo.lock` 出现意外变动
- 现有测试开始失败（regression — 不要 `#[ignore]` 解决）
- 引入 `unsafe` 块（如果项目政策禁止）
- clippy warnings 增加（如果项目用 `-D warnings`）

### False-completion traps
- `#[ignore]` 标注会让测试跳过但仍计入 "test result: ok"——goal 应明确"ignored 计数必须为 0"
- `cfg(test)` 下的 mock 实现可能让测试通过但生产代码 broken——goal 应要求至少一个集成测试
- Cargo workspace 下 `cargo test` 不带 `-p` 会跑所有 crate，时间长

### Probe questions
- Rust 版本（`rust-toolchain.toml`）？
- 是否 `#![forbid(unsafe_code)]`？
- 是否启用 nightly features？
- 是否有 `no_std` crate？

---

## Static / 文档项目

### Test / Build 命令
- 通常只有 markdown lint 或 link-check
```
markdownlint **/*.md
```
或：
```
npx markdown-link-check README.md
```

### Default Stop-if bullets
- 修改任何 `.svg` / `.png` / `.gif` 资产（除非 goal 明确要求）
- 现有 markdown 渲染失败（如有 build pipeline）
- 引入 broken link
- frontmatter / metadata 字段被无意修改

### False-completion traps
- 模型可能"修复"它认为是 typo 的术语，实际是项目刻意保留的拼法（如品牌名、缩写）
- markdown 表格的对齐改动会让 git diff 看起来很大但实际无内容变化——goal 应区分"内容变化"vs"格式化变化"
- 双语文档（README.md + README_CN.md）容易只改一个

### Probe questions
- 是否有 style guide（措辞、术语表）？
- 是否双语？哪个是主？
- 是否用 mkdocs / docusaurus / vitepress 等 static site generator？

---

## 其他 / 未知

如果项目类型不在以上列表，至少问：

1. 怎么跑测试？（请给完整命令）
2. 怎么 build / type-check？（请给完整命令）
3. 项目最忌讳改什么文件？
4. 是否有 AGENTS.md / CLAUDE.md / CONTRIBUTING.md 已经写了规则？

把这些答案直接塞进 Constraints 和 Stop-if，不要尝试推断。
