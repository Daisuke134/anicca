# Coding Style

## Immutability (CRITICAL)

ALWAYS create new objects, NEVER mutate:

```javascript
// WRONG: Mutation
function updateUser(user, name) {
  user.name = name  // MUTATION!
  return user
}

// CORRECT: Immutability
function updateUser(user, name) {
  return {
    ...user,
    name
  }
}
```

## File Organization

MANY SMALL FILES > FEW LARGE FILES:
- High cohesion, low coupling
- 200-400 lines typical, 800 max
- Extract utilities from large components
- Organize by feature/domain, not by type

## Error Handling

ALWAYS handle errors comprehensively:

```typescript
try {
  const result = await riskyOperation()
  return result
} catch (error) {
  console.error('Operation failed:', error)
  throw new Error('Detailed user-friendly message')
}
```

## Input Validation

ALWAYS validate user input:

```typescript
import { z } from 'zod'

const schema = z.object({
  email: z.string().email(),
  age: z.number().int().min(0).max(150)
})

const validated = schema.parse(input)
```

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No console.log statements
- [ ] No hardcoded values
- [ ] No mutation (immutable patterns used)

## Refactoring Policy (未使用コード)

**原則: 容赦なく削除する（例外なし）**

根拠: [Avanderlee - Refactoring Swift Best Practices](https://www.avanderlee.com/optimization/refactoring-swift-best-practices/)
> 「シンプルだが非常に価値のあるアクションは、未使用コードを容赦なく削除すること」

**ルール:**
1. **今使っていないコード** → 完全削除
2. **将来使うかもしれないコード** → 削除（git historyから復元可能）
3. **`// UNUSED`コメント付きで残す** → 禁止（レガシーコードの混乱を招く）
4. **UIパターンとして参考になる** → MDファイルに記録してから削除

**記録先:**
- `.cursor/plans/future/` - 将来実装予定の機能パターン
- `.cursor/plans/ui-patterns/` - 再利用可能なUIパターン

## FK Constraint Safety Pattern (P2003)

**Prisma upsert で FK 先のレコードが存在しない場合、P2003 エラーでクラッシュする。**

| ルール | 詳細 |
|--------|------|
| FK依存 upsert の前に存在チェック | `findUnique({ where: { id }, select: { id: true } })` |
| 存在しない場合 | warn ログを出して早期 return（throw しない） |
| 該当箇所 | `userTypeService.js:classifyAndSave()`, `profileService` 等 |

```javascript
// 必須パターン: FK依存 upsert の前
const exists = await prisma.targetTable.findUnique({ where: { id }, select: { id: true } });
if (!exists) {
  logger.warn(`Record not found, skipping FK-dependent operation`);
  return;
}
await prisma.dependentTable.upsert({ ... });
```
