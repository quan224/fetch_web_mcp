---
name: fetch_webpage
description: Browser automation - navigate, interact with, and extract content from web pages. Use when user asks to browse websites, click elements, fill forms, take screenshots, extract data, scroll pages, or manage popups/ads.
---

# Fetch Webpage Skill

This skill controls a real browser (Edge/Chrome) via CDP to automate web interactions.

## Available Tools

### Navigation & Content
- **navigate** - Open a URL in the browser
- **content** - Get visible text content and interactive elements from a page
- **list_pages** - List all open browser tabs
- **close_page** - Close a browser tab by URL domain

### Interaction
- **click** - Click an element by CSS selector, text, or XPath
- **fill** - Fill text into an input field
- **scroll** - Scroll the page up or down

### Data Extraction
- **extract** - Extract data from elements matching a CSS selector
- **screenshot** - Take a screenshot of the page or a specific element

### Popup & Ad Management
- **detect_popups** - Detect all popups (dialogs, modals, overlays)
- **close_popup** - Close a specific popup (click button, press Escape, or hide)
- **detect_ads** - Detect ad elements on the page
- **close_ads** - Hide ad elements on the page

### Utility
- **shutdown** - Close the browser and release the debug port

## Usage Guidelines

1. Always **navigate** to a URL before using other tools on that page
2. Use **content** to understand what's on the page before interacting
3. Use **extract** with CSS selectors to pull structured data
4. Use **screenshot** to verify page state when needed
5. Use **detect_popups** / **detect_ads** to handle overlays that block interaction
6. Call **shutdown** when done to free the browser process

## Common Patterns

### Browse and extract data
```
navigate(url) → content(url) → extract(url, selector)
```

### Fill and submit a form
```
navigate(url) → fill(url, selector, value) → click(url, submit_button)
```

### Handle blocking popups
```
detect_popups(url) → close_popup(url, selector, method) → content(url)
```

## Notes

- The browser persists between calls (same tab is reused for the same domain)
- Screenshots are saved to a `screenshot/` directory next to the executable
- `browser_path` argument is optional on all tools (auto-detects Edge)
