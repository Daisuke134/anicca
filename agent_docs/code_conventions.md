# Code Conventions

## Immutability (Critical)

Never mutate. Create new objects:
```javascript
// WRONG: user.name = name
// CORRECT: return { ...user, name }
```

## File Organization

| Rule | Value |
|------|-------|
| Typical | 200-400 lines |
| Max | 800 lines |
| Organize | By feature/domain |

## Error Handling

```typescript
try {
  const result = await riskyOperation()
  return result
} catch (error) {
  console.error('Operation failed:', error)
  throw new Error('User-friendly message')
}
```

## Input Validation

Use Zod at system boundaries:
```typescript
const schema = z.object({ email: z.string().email() })
const validated = schema.parse(input)
```

## Security

| Rule | Detail |
|------|--------|
| No hardcoded secrets | Use env vars only |
| Validate all user input | Zod at boundaries |
| Parameterized queries | SQL injection prevention |

## Unused Code

**Delete immediately.** Git history exists for recovery. No `// UNUSED` comments.

## FK Constraint Safety

```javascript
const exists = await prisma.table.findUnique({ where: { id }, select: { id: true } });
if (!exists) { logger.warn('Not found, skipping'); return; }
await prisma.dependent.upsert({ ... });
```
