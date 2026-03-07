---
name: agent-browser
description: 'Automate web browsers with agent-browser CLI: navigate pages, take screenshots, click elements, fill forms, and extract content. Use when tasks require reading/interacting with web pages that cannot be accessed via APIs. Requires agent-browser installed (Docker: build with OPENCLAW_INSTALL_AGENT_BROWSER=1).'
metadata:
  {
    "openclaw":
      {
        "emoji": "🌐",
        "requires": { "bins": ["agent-browser"] },
      },
  }
---

# agent-browser

[agent-browser](https://github.com/vercel-labs/agent-browser) is a headless browser CLI for AI agents. It navigates pages, captures accessibility tree snapshots, clicks elements, fills forms, and takes screenshots — all via simple commands.

## Prerequisites

The `agent-browser` binary must be installed. In Docker:

```bash
export OPENCLAW_INSTALL_AGENT_BROWSER=1
./docker-setup.sh
```

Verify:

```bash
agent-browser --version
```

## Core Commands

| Command | Description |
| ------- | ----------- |
| `agent-browser navigate <url>` | Open a URL in a new browser session |
| `agent-browser snapshot` | Dump the page accessibility tree (for element targeting) |
| `agent-browser screenshot --output /tmp/page.png` | Capture full-page screenshot |
| `agent-browser click --selector <css>` | Click an element |
| `agent-browser fill --selector <css> --value <text>` | Fill an input field |
| `agent-browser content` | Extract page text content |
| `agent-browser close` | Close the browser session |

## Quickstart: Read a page

```bash
# Navigate then extract text
agent-browser navigate https://example.com
agent-browser content
```

## Quickstart: Screenshot

```bash
agent-browser navigate https://example.com
agent-browser screenshot --output /tmp/screenshot.png
```

## Quickstart: Fill a form and submit

```bash
agent-browser navigate https://example.com/login
agent-browser snapshot        # find selector IDs from accessibility tree
agent-browser fill --selector "#email" --value "user@example.com"
agent-browser fill --selector "#password" --value "secret"
agent-browser click --selector "button[type=submit]"
agent-browser content         # read result page
```

## Tips

- Always run `snapshot` first to understand available elements before clicking
- Use `--output` to save screenshots to a path you can reference later
- For multi-step flows, keep the session open between commands (same shell)
- In Docker, map a volume if you need to access output files from the host
