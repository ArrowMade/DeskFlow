---
name: typing-input
description: Type text, press keys, use keyboard shortcuts, fill forms
triggers:
  - type
  - write
  - enter
  - press
  - key
  - shortcut
  - keyboard
  - paste
  - copy
  - undo
  - select
  - form
  - input
  - fill
---

## Context
You are simulating keyboard and mouse input to interact with the active application.

## Instructions

1. ALWAYS focus the target app/window first with `focus_window` or `open_app`.
2. To type text: use `type_text`. Make sure the cursor is in the right field first.
3. To click a field before typing: use `get_ui_elements` to find it, then `click_at` its center.
4. To press keys: use `press_key` (e.g., "return", "tab", "escape").
5. To use shortcuts: use `press_key` with modifiers (e.g., "command+s", "command+c", "command+v").
6. To select all: `press_key` with "command+a".
7. To copy: select text first, then `press_key` with "command+c".
8. To paste: `press_key` with "command+v".
9. To undo: `press_key` with "command+z".
10. For scrolling: use `scroll` with amount (positive = down, negative = up).
11. For drag operations: use `drag` with start and end coordinates.

## Error Handling
- If typing doesn't appear, the window may not be focused. Re-focus and try again.
- If a shortcut doesn't work, the app may use different bindings. Check with `get_ui_elements`.

## Rules
- ALWAYS verify the correct window is focused before typing.
- For multi-line text, type line by line with `press_key return` between lines.
- Be careful with keyboard shortcuts — they vary between apps.
