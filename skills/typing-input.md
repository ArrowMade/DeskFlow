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
  - document
  - doc
  - note
  - text
---

## Context
You are simulating keyboard and mouse input to interact with the active application.

## Instructions

1. ALWAYS focus the target app/window first with `focus_window` or `open_app`.
2. For writing/composing text content: ALWAYS use `generate_text` first (uses fast deepseek-chat model), \
   then `type_text` to paste the result. This is 10x faster than composing text yourself.
3. Typical workflow: `open_app` → `press_key` "command+n" (new document) → `generate_text` → `type_text`.
   Do NOT waste time with `get_ui_elements` or `ocr_screen` for this workflow.
4. To type formatted, multi-line text: use `type_text` with `\n` for line breaks.
   - The tool auto-detects multi-line text and uses clipboard+paste to preserve formatting.
   - Example: `"Title: My Document\n\nSection 1\n- Point one\n- Point two\n\nSection 2\n- Point three"`
5. ALWAYS format text with proper structure:
   - Use `\n\n` for paragraph breaks.
   - Use `\n` for line breaks within sections.
   - Use `\n- ` for bullet points.
   - Use `\n1. ` for numbered lists.
   - Add a title at the top followed by `\n\n`.
   - Never dump everything in a single paragraph.
6. To click a field before typing: use `get_ui_elements` to find it, then `click_at` its center.
7. To press keys: use `press_key` (e.g., "return", "tab", "escape").
8. To use shortcuts: use `press_key` with modifiers (e.g., "command+s", "command+c", "command+v").
9. To select all: `press_key` with "command+a".
10. To copy: select text first, then `press_key` with "command+c".
11. To paste: `press_key` with "command+v".
12. To undo: `press_key` with "command+z".
13. For scrolling: use `scroll` with amount (positive = down, negative = up).
14. For drag operations: use `drag` with start and end coordinates.

## Text Formatting Examples

For a brainstorm document:
```
"SaaS Ideas Brainstorm\n\n1. AI Resume Builder\n   - Auto-generates resumes from LinkedIn\n   - Monthly subscription model\n\n2. Smart Invoice Tool\n   - Scans receipts with OCR\n   - Auto-categorizes expenses\n\n3. Team Standup Bot\n   - Async daily standups\n   - Slack/Discord integration"
```

For meeting notes:
```
"Meeting Notes - May 9, 2026\n\nAttendees: Alice, Bob, Charlie\n\nAgenda:\n1. Q2 roadmap review\n2. Hiring update\n3. Bug triage\n\nAction Items:\n- [ ] Alice: Finalize design specs by Friday\n- [ ] Bob: Set up staging environment\n- [ ] Charlie: Schedule customer interviews"
```

## Error Handling
- If typing doesn't appear, the window may not be focused. Re-focus and try again.
- If a shortcut doesn't work, the app may use different bindings. Check with `get_ui_elements`.

## Rules
- ALWAYS verify the correct window is focused before typing.
- NEVER type long text as a single paragraph — always use proper formatting with line breaks.
- For multi-line content, the tool auto-uses clipboard+paste (preserves formatting).
- After pasting, the original clipboard content is restored.
