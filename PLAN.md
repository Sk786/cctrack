# cctrack — Project Plan & Build Guidelines

## What is cctrack?

A terminal-first CLI tool that helps developers track and analyze their AI token usage
across CLI agents like Claude Code and Codex CLI. Shows daily usage, cost estimates,
and patterns to help users plan and optimize their AI spending.

## Target Audience

Developers using Claude Code, Codex CLI, and other AI CLI agents who want visibility
into their token usage and costs directly from the terminal — without switching to a
web dashboard.

## Tech Stack

```
Python
├── typer         ← CLI framework (commands like: cctrack today, cctrack weekly)
├── rich          ← Terminal UI (tables, bar charts, colors)
├── sqlite3       ← Local storage for parsed session data (built into Python)
├── pydantic      ← Data validation and model definitions
└── pytest        ← Testing
```

## Why Python

- Developer (Sandeep) already knows Python and Django
- Rich ecosystem for CLI and terminal UI
- Fast to prototype and ship
- Easy to publish to PyPI

## Data Sources

### v1 — Claude Code (local files, no API key needed)
Claude Code stores full session transcripts locally at:
- Mac/Linux: `~/.claude/projects/**/*.jsonl`
- Windows: `%APPDATA%\Claude\projects\**\*.jsonl`

Parse these JSONL files directly — zero config, zero friction for the user.

### v2 — Codex / OpenAI (API key required)
OpenAI does NOT store transcripts locally like Claude Code does.
Use the OpenAI Usage API instead:
```
GET https://api.openai.com/v1/usage?date=YYYY-MM-DD
Requires: OPENAI_API_KEY with org read permissions
```
Daily granularity only — not real-time.

### v3 — Future
Gemini CLI and other tools as the ecosystem grows.

### v2.5 — OpenCode (implemented)
OpenCode stores per-message usage in a local SQLite database:
- Linux: `~/.local/share/opencode/opencode.db`
- macOS: `~/Library/Application Support/opencode/opencode.db`
- Windows: `%APPDATA%\opencode\opencode.db`

cctrack opens it read-only and reads assistant messages, which already carry
input/output/reasoning/cache token counts plus a provider-reported cost. When a
cost is present it is used as-is; otherwise cctrack estimates from `prices.json`.

## Commands to Build

```bash
cctrack today        # Token usage for today
cctrack weekly       # Last 7 days breakdown
cctrack stats        # All-time summary
cctrack projects     # Usage broken down by project/session
cctrack prices       # Show model pricing and where it loads from
cctrack setup        # First-time config (paths, API keys for v2)
cctrack prompt       # One-line stats for shell prompt integration (must be fast — reads SQLite only)
```

## Build Phases

### Phase 1 — Parsing (Weekend 1, Day 1) ~4-6 hrs
- Project scaffold (pyproject.toml, folder structure)
- Read ~/.claude/projects/ JSONL files
- Parse token counts from transcripts
- Print raw data to terminal

**Goal:** `python main.py` prints real token counts from local files.

### Phase 2 — Storage & Stats (Weekend 1, Day 2) ~4-6 hrs
- SQLite schema to store parsed sessions
- Daily/weekly aggregation queries
- Cost calculation (tokens × price per model — config file, NOT hardcoded)

**Goal:** `cctrack today` and `cctrack weekly` commands work.

### Phase 3 — Terminal UI (Weekend 2, Day 1) ~4-6 hrs
- Rich tables for usage breakdown
- Bar chart for daily trends
- Color coding: green (low) / yellow (medium) / red (high usage)
- Clean help text for all commands

**Goal:** Looks polished and usable in terminal.

### Phase 4 — Polish & Publish (Weekend 2, Day 2) ~4-6 hrs
- Error handling (missing files, empty data, first-time users)
- README with terminal screenshots
- pyproject.toml configured for PyPI
- Publish: `twine upload dist/*`

**Goal:** Anyone can `pip install cctrack`.

### Phase 5 — Charts & Visualizations (Weekend 3, Day 1) ~3-4 hrs
Add `plotext` for real terminal charts that go beyond Unicode bar rows.

**Dependency:** `plotext>=5.2` (pure Python, no system libs needed)

**Charts to add:**

| Command | Chart added |
|---|---|
| `cctrack weekly` | Line chart — daily cost trend over 7 days (below the table) |
| `cctrack stats` | Horizontal bar chart — cost per model, sorted descending |
| `cctrack projects` | Horizontal bar chart — top 10 projects by cost |
| `cctrack today` | Stacked token breakdown — input / output / cache read / cache write per model |

**Design rules:**
- Charts render below their existing table (tables stay — charts add context, not replace)
- Max width = terminal width (auto-detected via `console.width`)
- Height: 10 rows for line charts, auto for bar charts
- Color scheme consistent with cost_style: green / yellow / red
- Controlled by a `--no-chart` flag on commands that have charts (for narrow terminals or piping)

**Goal:** `cctrack weekly` shows a line chart of spend-per-day; `cctrack stats` shows a model cost bar chart.

### Phase 6 — Shell Prompt Integration (Weekend 3, Day 2) ~2-3 hrs
Passive awareness — show today's token spend on every new terminal prompt without
the user having to run a command. Same pattern as git branch indicators.

**How it works:**
- `cctrack prompt` outputs a compact string like `[CC 45k · $0.12]`
- User adds one line to `.bashrc` / `.zshrc`:
  `export PS1="$(cctrack prompt) $PS1"`
- Or via Starship (cross-shell): a custom module calling `cctrack prompt`

**Requirements:**
- Must complete in <50ms — reads from SQLite cache only, never re-parses JSONL
- Output format is configurable: tokens, cost, or both
- Degrades silently to empty string if no data (new install, no sessions yet)
- `cctrack setup` prints the exact line to add to shell config

**Goal:** User sees `[CC 45k · $0.12]` in their prompt while Claude Code or
Codex CLI is active, with zero manual effort after one-time setup.

### Phase 7 — Codex / OpenAI Support (v2)
Add OpenAI token tracking via the Usage API.

- `cctrack setup` prompts for `OPENAI_API_KEY` and stores it in `~/.config/cctrack/config.toml`
- New data source module `cctrack/sources/openai.py` — hits `GET https://api.openai.com/v1/usage?date=YYYY-MM-DD`
- Ingests daily totals into SQLite alongside Claude data
- All existing commands (`today`, `weekly`, `stats`, `projects`) show combined multi-source data
- Model name prefix in display: `claude/...` vs `openai/...` to disambiguate

**Goal:** `cctrack weekly` shows both Claude Code and Codex usage in the same table.

### Phase 8 — Usage Projections

Predict next week's token usage and cost from historical weekly data. No ML libraries —
pure Python math only.

**New command:**
```bash
cctrack forecast      # next-week projection + trend summary
```

**Two formulas combined:**

*Exponential smoothing* — point estimate for next week's tokens.
Weights recent weeks more heavily than old ones. `α` controls how fast old data fades.
```
S_1 = x_1
S_n = α * x_n + (1 - α) * S_{n-1}    # α = 0.3 (configurable)
forecast = S_n
```

*Linear regression* — trend direction (growing / shrinking, and by how much).
Fit a line through weekly totals; the slope tells the story.
```
slope = (n * Σ(i * x_i) - Σi * Σx_i) / (n * Σi² - (Σi)²)
trend_pct = slope / mean(x) * 100
```

*Confidence range* — ±1 standard deviation of the last N weeks gives a simple
low/high band without overstating precision.

**Minimum data requirement:** 3 weeks of history to show a projection;
below that, print a message asking the user to come back after more usage.

**Output (example):**
```
Next week estimate:  ~142k tokens · ~$4.20
Trend:               +18% week-over-week (6 weeks of data)
Range:               110k – 175k  (±1 std dev)
```

**Implementation notes:**
- All math lives in `cctrack/stats.py` — no new dependencies
- `α = 0.3` default (slow decay, trusts history); user can override in config
- Projection shown per model if the user has used more than one model
- `cctrack weekly` gets a `--forecast` flag to append the projection below the table

**Goal:** `cctrack forecast` gives a useful next-week estimate in under 100ms from SQLite data.

### Phase 9 — Share & Iterate
- Post on r/ClaudeAI, r/Python, Hacker News
- Collect feedback, fix bugs
- Plan v3 (Gemini CLI, other tools)

### Phase 10 — Product validation: AI activity heatmap

**Product direction:** Make an AI usage activity profile—the equivalent of a GitHub contribution
graph—the primary shareable feature. A leaderboard is an optional social layer, not the product's
only value. The chart describes usage, not productivity or developer skill.

**Before building a server:** Show a local heatmap to developers and test whether they want to
share it and return to update it. Get feedback on which measure is meaningful (tokens, sessions,
or active days), what they are comfortable sharing, and whether private group comparisons matter.

**Validation questions:**
- Do developers share the chart without being prompted?
- Which measure and time range do they want to show?
- Do they prefer exact numbers or activity bands?
- Do teams or communities want invite-only boards, and do they return after the first week?

**Goal:** Validate repeated use and voluntary sharing with a small group before building accounts,
hosting, or billing.

### Phase 11 — Local heatmap and shareable export

Build this into the existing CLI using data already stored in SQLite. No account or network access
is required for this phase.

**CLI direction:**
```bash
cctrack heatmap                   # show recent activity in the terminal
cctrack heatmap --metric tokens   # choose tokens, sessions, or active days
cctrack heatmap --export image    # export a shareable chart
```

**Requirements:**
- Calendar grid with clear date ranges, legend, and empty states.
- Make the metric explicit; do not label token volume as productivity.
- Export should be legible when shared and should not expose project names or prompts.
- Continue to work offline and without an account.

**Goal:** A user can produce and share a useful heatmap from local data alone.

### Phase 12 — Opt-in account, profile, and aggregate sync

Only proceed after the local heatmap demonstrates interest. Keep the CLI useful when offline and
logged out. Decide hosting, authentication, retention, and operational costs before implementation.

**Privacy boundary:** Sync daily aggregate records only. Never upload raw transcripts, prompts,
project paths, or project names. Before first sync, show exactly which fields will be uploaded.

**User controls:** Explicit opt-in, preview, pause sync, disconnect, leave a board, and delete
uploaded data. Public profile visibility is off until the user explicitly enables it. Allow users
to hide exact counts and model breakdowns.

**Data integrity:** Treat client-submitted totals as reported usage, not verified facts. Avoid
claiming that token volume measures productivity. Document limits and deduplicate updates safely.

**Goal:** Users can inspect what is shared and revoke sharing without losing local tracking.

### Phase 13 — Invite-only boards

Add private boards only after profile sharing and sync are working reliably. Start with a small
pilot among a team or existing developer community.

**CLI direction:**
```bash
cctrack account connect
cctrack sync
cctrack board create
cctrack board join <invite-url>
cctrack board show
cctrack board leave
```

**Requirements:**
- Invite-only membership; owners can delete boards and members can leave at any time.
- Clearly identify ranking metric and window; offer usage measures such as tokens, spend, and
  active days without presenting them as measures of quality.
- Sync is explicit initially; do not silently upload on every CLI command.
- Network failure must not break local CLI features; provide an understandable sync status.

**Goal:** A real group uses a private board over multiple weeks and members voluntarily invite
others.

### Phase 14 — Monetization experiments

Keep local tracking and basic heatmaps free while testing demand. Monetization should follow
observed repeat usage, not precede it.

**Potential paid team features to validate:** More private boards or members, longer history,
team summaries, exports, and administrative controls. Test willingness to pay with pilot teams
before building billing or promising a hosted service level.

**Goal:** Identify a specific team feature users repeatedly use and are willing to pay for.

## Folder Structure (Target)

```
cctrack/
├── cctrack/
│   ├── __init__.py
│   ├── main.py          ← Typer app entry point
│   ├── parser.py        ← JSONL transcript parsing logic
│   ├── storage.py       ← SQLite read/write
│   ├── stats.py         ← Aggregation and cost calculations
│   ├── display.py       ← Rich UI rendering
│   └── config.py        ← Model pricing, paths, user settings
├── tests/
│   ├── test_parser.py
│   ├── test_stats.py
│   └── fixtures/        ← Sample JSONL files for testing
├── PLAN.md
├── README.md
├── pyproject.toml
└── .gitignore
```

## Important Implementation Notes

- **Token pricing in prices.json** — bundled at `cctrack/data/prices.json`, user override at `~/.config/cctrack/prices.json`. Never hardcode prices.
- **Cross-platform paths** — handle `~/.claude/` (Mac/Linux) vs `%APPDATA%\Claude\` (Windows)
- **JSONL format** — inspect actual `~/.claude/projects/` files before writing parser
- **Empty state handling** — graceful message if no Claude Code sessions found
- **No API calls in v1** — everything reads local files only
- **Shell prompt command must be fast** — `cctrack prompt` reads SQLite only, never touches JSONL files. Target <50ms.

## How to Use Claude AI While Building

| Do this | Avoid this |
|---|---|
| Paste actual JSONL sample from `~/.claude/` | Ask Claude to guess the file format |
| One feature per prompt | Ask Claude to build everything at once |
| Paste error messages directly into chat | Try to debug alone first |
| Ask Claude to explain code you don't understand | Ship code you can't read |

## Risks & Watch-outs

- Claude Code's JSONL format may be complex — budget extra parsing time
- OpenAI Usage API requires org-level permissions — some users may not have access
- Windows path handling needs testing separately
- PyPI package name `cctrack` may already be taken — verify before building

## Market Context

- **ccusage** exists as a basic community script — not a full CLI tool
- OpenAI/Anthropic web dashboards exist but are web-only and lagged
- No comprehensive multi-tool terminal aggregator exists yet
- Risk: providers could add this natively — build fast, build open-source

## Timeline

| Scenario | Estimated Time |
|---|---|
| Focused weekends with Claude AI | 2 weekends |
| Casual evenings | 2-3 weeks |
| Learning as you go | 1 month |
