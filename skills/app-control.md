---
name: app-control
description: Open, close, switch between, and control macOS applications
triggers:
  - open
  - close
  - launch
  - quit
  - switch
  - app
  - application
  - window
  - minimize
  - maximize
  - fullscreen
  - resize
  - arrange
---

## Context
You are controlling macOS applications — launching, switching, arranging windows.

## Instructions

1. To open an app: use `open_app` with the app name (e.g., "Safari", "Visual Studio Code").
2. To close an app: use `close_app`. Warn the user about unsaved work.
3. To switch to an app: use `focus_window` to bring it to front.
4. To see what's running: use `list_running_apps`.
5. To see window layout: use `get_windows` for positions and sizes.
6. To arrange windows: use `move_resize_window` to set position and size.
7. To split screen: get screen resolution first (`get_system_info`), then position windows side by side.
8. For app-specific actions: use `get_ui_elements` to find menus/buttons, then click them.
9. To use menu items: click the menu bar item, wait, then click the submenu item.

## Error Handling
- If app not found, search for it with `shell` using `mdfind "kMDItemKind == Application" -name "appname"`.
- If app is frozen, use `shell` with `kill` command (warn user first).

## Rules
- ALWAYS bring the target app to front before doing anything in it.
- Before closing apps, mention that unsaved work may be lost.
