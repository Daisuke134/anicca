# Multi-Agent Patterns

Patterns for coordinating multiple AI agents.

## Pattern 1: Pipeline (Sequential)

Agents execute in order, each passing output to the next.

```
[Agent A] → [Agent B] → [Agent C]
   ↓            ↓            ↓
 Research → Writing → Publishing
```

Use when:
- Clear sequential dependency
- Each step transforms data
- No parallelization needed

Implementation: `agent-orchestrator` with sequential mode

## Pattern 2: Parallel (Concurrent)

Multiple agents work independently on the same input.

```
         → [Agent A] →
[Input] → [Agent B] → [Aggregator] → Output
         → [Agent C] →
```

Use when:
- Multiple perspectives needed
- Tasks don't depend on each other
- Speed is priority

Implementation: `agent-orchestrator` with parallel mode

## Pattern 3: Coordinator-Worker

One coordinator delegates tasks to specialized workers.

```
           → [Worker A: Research]
[Coordinator] → [Worker B: Writing] → [Coordinator] → Output
           → [Worker C: Review]
```

Use when:
- Dynamic task allocation
- Need centralized control
- Tasks vary by input

Implementation: `autonomous-tasks` + `agent-orchestrator`

## Pattern 4: Producer-Consumer

One agent produces work items, others consume them.

```
[Producer] → Queue → [Consumer A]
                   → [Consumer B]
                   → [Consumer C]
```

Use when:
- Continuous work stream
- Load balancing needed
- Variable processing time

Implementation: Use file-based queue or database

## Communication Patterns

### File-Based
```yaml
# Producer writes to file
output: "shared/tasks/inbox.json"

# Consumer reads from file
input: "shared/tasks/inbox.json"
```

### Memory-Based
```yaml
# Use OpenClaw memory system
memory_set: "shared/tasks/current"
memory_get: "shared/tasks/current"
```

### Message-Based
```yaml
# Use sessions_send for inter-agent messaging
target_session: "worker-agent"
message: "{\"task\": \"process\", \"data\": ...}"
```

## Error Handling

1. **Retry with backoff** - Transient failures
2. **Dead letter queue** - Failed messages
3. **Circuit breaker** - Prevent cascade failures
4. **Timeout + fallback** - Don't hang forever

## State Management

- Use `memory/` directory for persistent state
- Use `MEMORY.md` for long-term knowledge
- Use `memory/YYYY-MM-DD.md` for daily logs
- Consider `shared-memory` skill for multi-agent shared state
