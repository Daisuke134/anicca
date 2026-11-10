---
name: intervene
description: Use when the user states a commitment, asks what they owe themselves, or a scheduled Life Manager check-in is running. The board is already injected on turns that have open items.
---

# Life Manager intervention

The plugin stores the board. Do not invent a streak or a completion.

- When the injected board names an overdue item, ask once whether to do it, move the due date, or drop it.
- Call `life_manager_complete` only after the user says the item is done.
- Call `life_manager_commit` when the user agrees to something the statement hook did not already record.
- Call `life_manager_checkin` for a scheduled check-in. The tool returns immediately during cron.
- Never put passwords, tokens, or keys on the board.
