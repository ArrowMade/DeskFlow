---
name: file-management
description: Create, move, rename, delete, search, and organize files and folders
triggers:
  - file
  - folder
  - directory
  - create
  - delete
  - move
  - rename
  - copy
  - find
  - search
  - organize
  - desktop
  - downloads
  - documents
  - finder
---

## Context
You are managing files and folders on the user's Mac.

## Instructions

1. To explore files: use `list_directory` to see contents, `search_files` to find by pattern.
2. To read a file: use `read_file` with the full path.
3. To create a file: use `write_file` with path and content.
4. To move/rename: use `move_file` with source and destination paths.
5. To delete: use `delete_file` — ALWAYS warn the user before deleting.
6. To copy a file: use `shell` with `cp source dest`.
7. To create a folder: use `shell` with `mkdir -p path`.
8. To find large files: use `shell` with `find path -size +100M -type f`.
9. To open in Finder: use `shell` with `open path` or `open_app Finder`.
10. For bulk operations, use `shell` with appropriate commands.

## Error Handling
- If a path doesn't exist, inform the user and suggest alternatives.
- If permission denied, explain and suggest `sudo` if appropriate (with warning).

## Rules
- ALWAYS use absolute paths (starting with `/` or `~`).
- NEVER delete files without confirming with the user first.
- When moving files, verify the destination directory exists first.
- Expand `~` to the full home directory path in shell commands.
