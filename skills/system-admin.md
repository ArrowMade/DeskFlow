---
name: system-admin
description: System settings, info, network, disk, processes, and administration
triggers:
  - system
  - settings
  - preferences
  - wifi
  - network
  - bluetooth
  - volume
  - brightness
  - battery
  - storage
  - disk
  - memory
  - cpu
  - process
  - kill
  - install
  - update
  - brew
  - terminal
---

## Context
You are managing macOS system settings and performing administration tasks.

## Instructions

1. To get system info: use `get_system_info` for hardware, OS, disk, battery details.
2. To change settings: use `set_system_setting` for defaults-based settings.
3. For System Settings app: use `open_app "System Settings"`, then navigate with UI elements.
4. To manage processes: use `shell` with `ps aux`, `top -l 1`, or `kill`.
5. To check network: use `shell` with `ifconfig`, `networksetup`, or `ping`.
6. To manage Wi-Fi: use `shell` with `networksetup -setairportpower en0 on/off`.
7. To install software: use `shell` with `brew install package`.
8. To check disk space: use `shell` with `df -h`.
9. To manage volumes: use AppleScript `set volume output volume 50`.
10. For login items, notifications, security: navigate System Settings UI.

## Error Handling
- If `sudo` is needed, inform the user and let them decide.
- If a command fails, check permissions and suggest alternatives.

## Rules
- NEVER run destructive system commands (rm -rf /, mkfs, etc.) without explicit confirmation.
- ALWAYS warn before changing system settings.
- For `sudo` commands, explain what they do and why elevated access is needed.
