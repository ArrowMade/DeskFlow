# DeskFlow

**AI-powered desktop agent that fully controls your Mac.**

DeskFlow is an open-source macOS automation agent powered by DeepSeek V4 Pro. It can see your screen, click buttons, type text, browse the web, manage files, control apps, and execute complex multi-step tasks — all from a simple chat interface.

Think of it as a mini [Open Interpreter](https://github.com/openclaw/openclaw) built for macOS, running locally with cheap API costs.

<p align="center">
  <img src="https://img.shields.io/badge/Platform-macOS-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Python-3.11+-green?style=flat-square" />
  <img src="https://img.shields.io/badge/Model-DeepSeek%20V4%20Pro-purple?style=flat-square" />
  <img src="https://img.shields.io/badge/Tools-32-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Skills-6-yellow?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" />
</p>

---

## Demo

```
>>> open Chrome, go to github.com/trending, and tell me the top 3 repos

[browser_open_url] Opening https://github.com/trending in Google Chrome...
[get_ui_elements] Reading page structure...
[browser_get_page_content] Extracting page text...

Here are today's top 3 trending repos on GitHub:

1. **project-alpha** - A next-gen framework for building AI agents
2. **lightning-css** - Blazing fast CSS parser written in Rust
3. **open-assistant** - Open-source conversational AI assistant
```

---

## Features

### 32 Tools for Full Desktop Control

| Category | Tools | What They Do |
|----------|-------|-------------|
| **Screen Understanding** | `get_ui_elements`, `ocr_screen`, `screenshot` | Read UI trees, extract text via OCR, capture screen |
| **Window Management** | `get_windows`, `move_resize_window`, `focus_window` | List, move, resize, focus windows |
| **Input Control** | `click_at`, `type_text`, `press_key`, `scroll`, `drag` | Click, type, keyboard shortcuts, scroll, drag-and-drop |
| **App Control** | `open_app`, `close_app`, `list_running_apps` | Launch, quit, list applications |
| **Browser** | `browser_open_url`, `browser_get_page_content`, `browser_list_tabs`, `browser_switch_tab` | Browse with Safari, Chrome, Firefox, Arc, Edge |
| **Files** | `read_file`, `write_file`, `list_directory`, `search_files`, `move_file`, `delete_file` | Full filesystem operations |
| **Shell & Code** | `shell`, `applescript`, `run_python` | Execute commands, AppleScript, Python |
| **System** | `get_system_info`, `set_system_setting`, `get_clipboard`, `set_clipboard`, `send_notification` | System info, settings, clipboard, notifications |

### Smart Skills System

Skills are markdown files that give the agent specialized knowledge per task. They auto-activate based on what you ask:

| Skill | Activates When You Say... |
|-------|--------------------------|
| `browser-automation` | chrome, safari, website, search, google, tab |
| `file-management` | file, folder, delete, move, finder, desktop |
| `app-control` | open, close, switch, window, resize |
| `typing-input` | type, write, press, keyboard, paste, form |
| `system-admin` | settings, wifi, volume, battery, process, brew |
| `coding` | code, python, debug, git, script, vscode |

Create your own skills in `~/.deskflow/skills/` — they override built-in ones.

### Structured Memory (OpenClaw-Inspired)

Three persistent files that make the agent smarter over time:

| File | Purpose |
|------|---------|
| `SOUL.md` | Agent personality — customize who DeskFlow is |
| `MEMORY.md` | Long-term facts about you, your preferences, learned context |
| `HEARTBEAT.md` | Daily activity log — every action timestamped and tracked |

### ReAct Agent Loop

Follows the **Observe → Think → Act → Verify** pattern:

```
1. Normalize      → Clean and parse user input
2. Context Assembly → Build prompt from skills + memory + history + environment
3. Infer          → Call DeepSeek V4 Pro with 1M token context
4. Act            → Execute tools (with safety checks)
5. Observe        → Verify results, retry if needed
6. Persist        → Log to heartbeat, save to memory
```

### Multi-Browser Support

Works with any browser — auto-detects which one is running:

- **Google Chrome** — full AppleScript control
- **Safari** — full AppleScript control
- **Firefox** — URL opening + OCR fallback
- **Arc** — full Chromium-based control
- **Microsoft Edge** — full Chromium-based control

Every browser operation **auto-focuses the window** before acting.

### Screen Understanding Without Vision Models

DeskFlow doesn't need GPT-4o or Claude for vision. Instead:

- **`get_ui_elements`** — reads the full UI tree via macOS Accessibility APIs (every button, label, text field with exact coordinates)
- **`ocr_screen`** — extracts all text from screen using macOS Vision framework
- **`get_windows`** — lists all windows with positions and sizes

This is often **more precise** than vision models for clicking UI elements.

### Safety System

Three-tier risk classification with configurable confirmation:

- **Safe** — auto-approved (reading files, screenshots, listing apps)
- **Risky** — confirmation optional (typing, clicking, writing files)
- **Dangerous** — always confirmed (deleting files, system settings)

Shell commands are checked against allowlists, blocklists, and dangerous patterns.

---

## Quick Start

### Prerequisites

- **macOS** 13+ (Ventura or later)
- **Python** 3.11+
- **uv** package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))

### Install & Run

```bash
# Clone
git clone https://github.com/yourusername/deskflow.git
cd deskflow

# Install dependencies
uv sync

# Run
uv run deskflow
```

On first run, DeskFlow will ask for your DeepSeek API key:

```
╭──────────────────────────────────────────────╮
│ Welcome to DeskFlow!                         │
│                                              │
│ To get started, you need a DeepSeek API key. │
│ Get one at: platform.deepseek.com/api_keys   │
╰──────────────────────────────────────────────╯

Enter your DeepSeek API key: sk-xxxxx
API key saved to ~/.deskflow/config.yaml
```

The key is saved locally — you only enter it once.

### macOS Permissions

DeskFlow needs these permissions (System Settings → Privacy & Security):

| Permission | Why |
|-----------|-----|
| **Accessibility** | To read UI elements and simulate clicks/keystrokes |
| **Screen Recording** | To take screenshots and run OCR |
| **Automation** | To control apps via AppleScript |

Your terminal app (Terminal, iTerm2, etc.) needs to be added to each.

---

## Usage

### Chat Interface

```
>>> open Safari and go to google.com
>>> what apps are running right now?
>>> take a screenshot and tell me what's on my screen
>>> create a file called todo.txt on my Desktop with a task list
>>> open Notes and type "Meeting notes for today"
>>> check my battery, wifi, and disk space
```

### Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/tools` | List all 32 tools with risk levels |
| `/skills` | List loaded skills and their triggers |
| `/soul` | View agent personality (SOUL.md) |
| `/memory` | View stored memories |
| `/heartbeat` | View today's activity log |
| `/clear` | Clear conversation history |
| `/reload` | Hot-reload skills from disk |
| `/quit` | Exit DeskFlow |

---

## Configuration

Config lives at `~/.deskflow/config.yaml`:

```yaml
# Model
model: deepseek-v4-pro
max_context_tokens: 1000000
max_output_tokens: 8192

# Workspace (SOUL.md, MEMORY.md, HEARTBEAT.md)
workspace_dir: ~/.deskflow/workspace

# Custom skills directory (overrides built-in skills)
skills_dir: ~/.deskflow/skills

# Safety
safety:
  auto_approve_safe: true
  require_confirmation: dangerous  # "risky", "dangerous", or "all"
  shell_allowlist:
    - ls
    - cat
    - pwd
    - grep
  shell_blocklist:
    - "rm -rf /"
    - "sudo rm"

# Memory
memory:
  enabled: true
  db_path: ~/.deskflow/memory.db
  max_context_facts: 20
```

---

## Creating Custom Skills

Create a `.md` file in `~/.deskflow/skills/`:

```markdown
---
name: my-skill
description: What this skill does
triggers:
  - keyword1
  - keyword2
  - keyword3
---

## Context
Describe the role the agent takes when this skill activates.

## Instructions
1. Step one
2. Step two
3. Step three

## Rules
- What the agent should never do
- Constraints and guardrails
```

Skills auto-activate when the user's message matches trigger keywords. Top 3 most relevant skills are injected per request.

---

## Architecture

```
src/deskflow/
├── cli.py                  # Rich REPL interface
├── config.py               # YAML + env config loader
├── agent/
│   ├── loop.py             # ReAct agent loop (6 stages)
│   ├── client.py           # DeepSeek API client
│   └── conversation.py     # Conversation history + compaction
├── tools/
│   ├── base.py             # Tool interface + risk levels
│   ├── registry.py         # Tool registry + factory
│   ├── accessibility.py    # UI element tree reader
│   ├── ocr.py              # Screen OCR (Vision framework)
│   ├── screenshot.py       # Screen capture
│   ├── window.py           # Window management
│   ├── keyboard_mouse.py   # Click, type, scroll, drag
│   ├── browser.py          # Multi-browser automation
│   ├── apps.py             # App control
│   ├── filesystem.py       # File operations
│   ├── shell.py            # Shell commands
│   ├── applescript.py      # AppleScript execution
│   ├── python_exec.py      # Python execution
│   ├── clipboard.py        # Clipboard access
│   ├── system.py           # System info + settings
│   └── notifications.py    # macOS notifications
├── skills/
│   └── loader.py           # Skill parser + selector
├── memory/
│   ├── store.py            # SQLite interaction store
│   ├── structured.py       # SOUL.md + MEMORY.md + HEARTBEAT.md
│   └── context.py          # Context builder for prompts
├── safety/
│   ├── classifier.py       # Risk classification
│   ├── rules.py            # Allow/block lists + patterns
│   └── confirm.py          # User confirmation prompts
└── scheduler/
    └── scheduler.py        # Task scheduler (SQLite-backed)

skills/                     # Built-in skill definitions
├── browser-automation.md
├── file-management.md
├── app-control.md
├── typing-input.md
├── system-admin.md
└── coding.md
```

---

## How It Sees Without Vision

Most AI desktop agents need expensive vision models (GPT-4o, Claude) to understand what's on screen. DeskFlow uses a different approach:

| Method | What It Does | When To Use |
|--------|-------------|-------------|
| **Accessibility API** | Returns full UI tree — every button, label, text field with exact `(x, y, width, height)` | Finding clickable elements |
| **OCR (Vision framework)** | Extracts text from screen with positions | Reading content, verifying actions |
| **Window List** | All windows with app name, title, position, size | Understanding what's open |

This is **cheaper** (no vision model tokens) and **more precise** (exact pixel coordinates vs. model guessing).

---

## Cost

DeepSeek V4 Pro is extremely cheap:

| | Price |
|---|---|
| Input tokens | $0.44 / million |
| Output tokens | $0.87 / million |
| Cache hits | $0.03 / million (90% discount) |
| Context window | 1 million tokens |

A typical task (open browser, navigate, read page) costs **< $0.01**.

---

## Roadmap

- [ ] Streaming responses (real-time output)
- [ ] Voice input (Whisper)
- [ ] Multi-monitor support
- [ ] Plugin system with hooks
- [ ] Web UI dashboard
- [ ] Task scheduler (cron-based automation)
- [ ] Session save/restore
- [ ] DeepSeek V4 Vision support (when available)

---

## Contributing

Contributions are welcome! Areas where help is needed:

- **New tools** — more macOS integrations
- **New skills** — domain-specific knowledge
- **Testing** — more test coverage
- **Documentation** — guides and tutorials

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Built with DeepSeek V4 Pro + macOS Accessibility APIs</b><br>
  <sub>A cheap, powerful desktop agent that actually works.</sub>
</p>
