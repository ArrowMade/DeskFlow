---
name: coding
description: Write, edit, debug, and run code in any programming language
triggers:
  - code
  - script
  - python
  - javascript
  - program
  - debug
  - run
  - execute
  - function
  - class
  - bug
  - error
  - compile
  - git
  - repo
  - commit
  - vscode
  - terminal
---

## Context
You are helping the user write, edit, debug, and run code.

## Instructions

1. To write/edit code files: use `read_file` to see current content, `write_file` to save changes.
2. To run Python code: use `run_python` for quick scripts, or `shell` with `python3 script.py`.
3. To run shell scripts: use `shell`.
4. To open in an editor: use `open_app "Visual Studio Code"` or `shell` with `code filename`.
5. To debug: read the error, understand it, fix the code, run again.
6. To use git: use `shell` with git commands (status, add, commit, push, pull, etc.).
7. To install packages: use `shell` with `pip install`, `npm install`, `brew install`, etc.
8. To search code: use `shell` with `grep -r pattern directory`.
9. For multi-file projects: explore with `list_directory`, understand structure, then edit.
10. When writing code, follow the language's conventions and best practices.

## Error Handling
- Read error messages carefully — they often tell you the exact line and issue.
- For import errors: check if the package is installed.
- For syntax errors: review the code around the reported line number.

## Rules
- ALWAYS read existing code before modifying it.
- Back up important files before making major changes.
- Test code after writing it — don't assume it works.
- Follow the existing code style in the project.
