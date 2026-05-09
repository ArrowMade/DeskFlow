---
name: browser-automation
description: Browse the web, search, read pages, fill forms, manage tabs
triggers:
  - browser
  - chrome
  - safari
  - firefox
  - website
  - web
  - url
  - search
  - google
  - tab
  - page
  - link
  - download
  - navigate
---

## Context
You are controlling the user's web browser to accomplish tasks on the internet.

## Instructions

1. Detect which browser the user wants. If they say "Chrome", pass `browser: "Google Chrome"`. If they don't specify, auto-detect.
2. Use `focus_window` or `browser_open_url` to bring the browser to front FIRST.
3. To navigate: use `browser_open_url` with the target URL.
4. To read page content: use `browser_get_page_content` to get the text.
5. To interact with page elements (buttons, forms, links):
   - Use `get_ui_elements` to find clickable elements and their positions.
   - Calculate center of the element: `x + width/2, y + height/2`.
   - Use `click_at` to click the element.
6. To type in a form field: click the field first, then use `type_text`.
7. To search Google: navigate to `https://www.google.com`, click search box, type query, press Enter.
8. To manage tabs: use `browser_list_tabs` to see open tabs, `browser_switch_tab` to switch.
9. After each action, verify with `ocr_screen` or `get_ui_elements` that it worked.
10. If a page is loading, wait 2-3 seconds then re-check.

## Error Handling
- If `browser_get_page_content` fails, fall back to `ocr_screen`.
- If a click misses, re-observe with `get_ui_elements` and try again.
- If the browser is unresponsive, try `close_app` then `open_app` to restart it.

## Rules
- NEVER guess URLs — ask the user or search Google first.
- ALWAYS bring the browser to front before any operation.
- When filling sensitive forms (passwords, payments), warn the user first.
