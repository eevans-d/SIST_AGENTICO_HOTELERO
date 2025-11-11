# MCP Servers Setup (Filesystem, Postgres, GitHub, Inspector, Playwright)

This project can be enhanced with Model Context Protocol (MCP) servers. Below are example configurations and setup notes to enable them locally with an MCP-compatible client (e.g., GitHub Copilot Chat with MCP support or other MCP hosts).

Important:
- The commands below are examples; install each MCP server following its official docs and adjust the command paths.
- Use environment variables for credentials (never commit secrets).

## Servers Overview

- Filesystem: read/write files under the project root with explicit allowlist
- Postgres: safe, read-first database exploration and queries
- GitHub: repository operations (issues/PRs/search) scoped to your token
- Inspector: runtime inspection (host-dependent; optional)
- Playwright: browser automation/testing (optional; requires browser drivers)

## Example Servers Configuration

Create a user-level MCP config (host-specific). For Copilot Chat, add these to your MCP settings, mapping `${workspaceRoot}` to your local path and setting env vars.

```json
{
  "servers": {
    "filesystem": {
      "command": "mcp-filesystem",
      "args": [
        "--root", "${workspaceRoot}",
        "--allow", "app/",
        "--allow", "tests/",
        "--allow", "docs/",
        "--deny", "**/.git/**"
      ]
    },
    "postgres": {
      "command": "mcp-postgres",
      "env": {
        "PGURL": "${POSTGRES_URL}"
      }
    },
    "github": {
      "command": "mcp-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "GITHUB_REPO": "eevans-d/SIST_AGENTICO_HOTELERO"
      }
    },
    "inspector": {
      "command": "mcp-inspector"
    },
    "playwright": {
      "command": "mcp-playwright",
      "env": {
        "PLAYWRIGHT_BROWSERS_PATH": "0"
      }
    }
  }
}
```

## Environment Variables

- POSTGRES_URL: e.g. `postgresql://user:pass@localhost:5432/agentdb`
- GITHUB_TOKEN: fine-scoped PAT (repo read/write as needed)

## Installation Hints

- Filesystem: install the filesystem MCP server (Node/TS or Python impl)
- Postgres: install the postgres MCP server and ensure network access to DB
- GitHub: install the github MCP server and set `GITHUB_TOKEN`
- Inspector: optional; install as per its documentation
- Playwright: install server and browsers (`npx playwright install`), or set `PLAYWRIGHT_BROWSERS_PATH`

## Safety Defaults

- Prefer read-only until explicitly allowed per task
- Never store secrets in repo; use env files excluded from VCS
- For DB ops, use read-only roles by default; switch to DML only with approval

## Project Integration

This repo already includes:
- Postgres utilities via test/dev Make targets
- Extensive tests and docs describing DB schemas and flows

Use MCP to augment these workflows (schema browsing, controlled migrations, PR automation, and browser flows for E2E when required).
