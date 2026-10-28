# cctrack

Know your AI activity. Keep it local. Share a heatmap.

`cctrack` tracks AI usage from Claude Code, OpenCode, and OpenAI, then turns it into useful terminal reports and a GitHub-style activity heatmap. Local sources need no account or API key. Export a heatmap as SVG for your profile or README.

**Local-first:** your session history stays on your machine. No account or upload is required to use the CLI.

```
$ cctrack today

  Today's Usage — Monday, June 29 2026
╭────────────────────┬───────┬────────┬─────────────┬────────────┬──────────────┬────────────╮
│ Model              │ Input │ Output │ Cache Write │ Cache Read │ Total Tokens │ Cost (USD) │
├────────────────────┼───────┼────────┼─────────────┼────────────┼──────────────┼────────────┤
│ claude-sonnet-4-6  │ 12.4k │  89.1k │       640k  │      8.2M  │        9.0M  │     $5.31  │
├────────────────────┼───────┼────────┼─────────────┼────────────┼──────────────┼────────────┤
│ TOTAL              │       │        │             │            │        9.0M  │     $5.31  │
╰────────────────────┴───────┴────────┴─────────────┴────────────┴──────────────┴────────────╯
```

## Install

```bash
pip install cctrack-ai
```

Or from source:

```bash
git clone https://github.com/Sk786/cctrack.git
cd cctrack
pip install -e .
```

## Commands

### `cctrack heatmap`
See your AI activity across the last year, directly in the terminal. The default intensity is total tokens; choose estimated spend or active days instead.

```bash
cctrack heatmap
cctrack heatmap --metric cost --days 90
cctrack heatmap --metric active-days
cctrack heatmap --output ~/ai-activity.svg
```

The exported SVG contains dates and relative activity levels only—never prompts or project names. It is generated locally and is not uploaded anywhere. Heatmap intensity is a picture of usage, not a productivity score.

### `cctrack today`
Token usage and cost for the current day, broken down by model. Includes a stacked token-type chart.

```
$ cctrack today

  Today's Usage — Monday, June 29 2026
╭────────────────────┬───────┬────────┬─────────────┬────────────┬──────────────┬────────────╮
│ Model              │ Input │ Output │ Cache Write │ Cache Read │ Total Tokens │ Cost (USD) │
├────────────────────┼───────┼────────┼─────────────┼────────────┼──────────────┼────────────┤
│ claude-sonnet-4-6  │ 12.4k │  89.1k │        640k │       8.2M │         9.0M │      $5.31 │
│ claude-haiku-4-5   │  3.1k │  14.2k │        120k │       1.1M │         1.2M │      $0.12 │
├────────────────────┼───────┼────────┼─────────────┼────────────┼──────────────┼────────────┤
│ TOTAL              │       │        │             │            │        10.2M │      $5.43 │
╰────────────────────┴───────┴────────┴─────────────┴────────────┴──────────────┴────────────╯

                           Token Breakdown by Type
  ┌──────────────────────────────────────────────────────────────────────┐
  │ ██ Input        ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  Cache Read      │
  │ ██ Output                                                             │
  │ ██ Cache Write                                                        │
  │ ██ Cache Read                                                         │
  └──────────────────────────────────────────────────────────────────────┘
```

### `cctrack weekly`
Last 7 days with a proportional spend bar per day and a daily cost line chart.

```
$ cctrack weekly

           Weekly Usage — Jun 23 to Jun 29, 2026
╭────────────┬─────┬────────┬────────────┬──────────────────────────────╮
│ Date       │ Day │ Tokens │ Cost (USD) │ Spend                        │
├────────────┼─────┼────────┼────────────┼──────────────────────────────┤
│ 2026-06-23 │ Mon │      — │          — │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ 2026-06-24 │ Tue │   3.1M │     $2.14  │ ████░░░░░░░░░░░░░░░░░░░░░░░░ │
│ 2026-06-25 │ Wed │ 820.4k │     $0.61  │ █░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ 2026-06-26 │ Thu │  14.7M │     $9.88  │ ████████████████░░░░░░░░░░░░ │
│ 2026-06-27 │ Fri │  22.3M │    $14.92  │ ████████████████████████░░░░ │
│ 2026-06-28 │ Sat │      — │          — │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ 2026-06-29 │ Sun │  10.2M │     $5.43  │ █████████░░░░░░░░░░░░░░░░░░░ │
├────────────┼─────┼────────┼────────────┼──────────────────────────────┤
│ TOTAL      │     │  51.1M │    $32.98  │                              │
╰────────────┴─────┴────────┴────────────┴──────────────────────────────╯

  By Model
  ─────────────────────────────────────────────────────
  claude-sonnet-4-6
    tokens : 47.8M
    cost   : $31.44
  claude-haiku-4-5
    tokens :  3.3M
    cost   :  $1.54

  Daily Spend (USD)  — line chart
  14.9 ┤                              ⢀⠔⠣⡀
       │                             ⡠⠊  ⠑⡄
   9.9 ┤                            ⡔⠁    ⠑⢄
       │                         ⢠⠊        ⠈⢢
   5.0 ┤              ⢀⠔⠣⡀      ⡔⠁           ⠑⢄      ⢀⠔
       │             ⡠⠊  ⠑⡄  ⡠⠊                ⠈⢢  ⡠⠊
   0.0 ┤⣀⣀⣀⡠⠤⠴⠁      ⠊    ⠑⠁                    ⠑⠁
       └┬───────────┬──────────┬───────────┬───────────┬
      Mon/23    Tue/24     Wed/25      Thu/26      Fri/27 …
```

### `cctrack stats`
All-time summary across every session, sorted by cost. Includes a model cost bar chart.

```
$ cctrack stats

             All-Time Usage  [2026-06-01 → 2026-06-29]
╭────────────────────────┬────────┬────────┬─────────────┬────────────┬──────────────┬────────────╮
│ Model                  │  Input │ Output │ Cache Write │ Cache Read │ Total Tokens │ Cost (USD) │
├────────────────────────┼────────┼────────┼─────────────┼────────────┼──────────────┼────────────┤
│ claude-sonnet-4-6      │  84.3k │   1.1M │        8.4M │      98.7M │       108.3M │     $74.20 │
│ claude-haiku-4-5       │  12.1k │  44.2k │        900k │      16.3M │        17.3M │      $2.41 │
├────────────────────────┼────────┼────────┼─────────────┼────────────┼──────────────┼────────────┤
│ TOTAL                  │        │        │             │            │       125.6M │     $76.61 │
╰────────────────────────┴────────┴────────┴─────────────┴────────────┴──────────────┴────────────╯

  Cost by Model (USD)
  ────────────────────────────────────────────────────────
       sonnet-4-6 ┤████████████████████████████████  $74.20
        haiku-4-5 ┤██  $2.41
                  └─────────────────────────────────────
                  0          20          40          60         80
```

### `cctrack projects`
Usage ranked by project, showing which directories are spending the most.

```
$ cctrack projects

                      Usage by Project
╭────────────────────────┬────────┬────────────┬─────────────┬───────────────╮
│ Project                │ Tokens │ Cost (USD) │ Last Active │ Models        │
├────────────────────────┼────────┼────────────┼─────────────┼───────────────┤
│ home/user/projects/api │  58.2M │     $38.91 │ 2026-06-29  │ sonnet        │
│ home/user/projects/web │  31.4M │     $21.07 │ 2026-06-28  │ sonnet        │
│ home/user/projects/cli │  22.1M │     $11.22 │ 2026-06-27  │ haiku, sonnet │
│ home/user/scratch      │   8.6M │      $4.19 │ 2026-06-25  │ haiku         │
│ home/user/dotfiles     │ 213.4k │      $0.18 │ 2026-06-22  │ sonnet        │
├────────────────────────┼────────┼────────────┼─────────────┼───────────────┤
│ TOTAL                  │ 120.5M │     $75.57 │             │               │
╰────────────────────────┴────────┴────────────┴─────────────┴───────────────╯
```

### `cctrack prices`
Show the model pricing table and where it's loaded from.

```
$ cctrack prices

          Model Pricing (USD per 1M tokens)
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Model              ┃  Input ┃ Output ┃ Cache Write ┃ Cache Read ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ claude-sonnet-4-6  │  $3.00 │ $15.00 │       $3.75 │      $0.30 │
│ claude-opus-4-8    │  $5.00 │ $25.00 │       $6.25 │      $0.50 │
│ claude-haiku-4-5   │  $1.00 │  $5.00 │       $1.25 │      $0.10 │
│ default (fallback) │  $3.00 │ $15.00 │       $3.75 │      $0.30 │
└────────────────────┴────────┴────────┴─────────────┴────────────┘

Loaded from: ~/.local/lib/python/site-packages/cctrack/data/prices.json
To override, copy to: ~/.config/cctrack/prices.json
```

### `cctrack setup`
Show all config paths and a getting-started guide.

## Shell Prompt Integration

See today's spend on every new terminal prompt — same pattern as a git branch indicator.

**bash / zsh** — add to `~/.bashrc` or `~/.zshrc`:
```bash
export PS1="$(cctrack-prompt) $PS1"
```

**fish** — add to `~/.config/fish/config.fish`:
```fish
function fish_prompt; echo (cctrack-prompt) (fish_prompt); end
```

**Starship** — add to `~/.config/starship.toml`:
```toml
[custom.cctrack]
command = "cctrack-prompt"
when = "true"
```

Output looks like:
```
[CC 10.2M · $5.43] user@host ~/projects $
```

Format options:
```bash
cctrack-prompt                  # [CC 10.2M · $5.43]  (default)
cctrack-prompt --format tokens  # [CC 10.2M]
cctrack-prompt --format cost    # [CC $5.43]
```

`cctrack-prompt` reads SQLite only — no JSONL parsing — and completes in ~40ms.

## How It Works

cctrack reads usage that the tools already keep on your machine:

| Source | Location | Notes |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/**/*.jsonl` | Parsed from session transcripts |
| OpenCode | `~/.local/share/opencode/opencode.db` | Read-only; includes reasoning tokens and provider-reported cost |
| OpenAI | Usage API | Opt-in via `cctrack openai-sync`, needs an organization API key |

Everything is stored in `~/.config/cctrack/usage.db`, and every command queries that file — fast and offline.

**Cost resolution:** when OpenCode reports what a request actually cost, cctrack uses that number. Otherwise it estimates from the bundled price table. Reasoning tokens are billed at the output rate.

The CLI never uploads local transcripts or project names.

## Customizing Prices

Prices are bundled at `cctrack/data/prices.json`. To override:

```bash
mkdir -p ~/.config/cctrack
cp $(python -c "import cctrack; print(cctrack.__file__.replace('__init__.py','data/prices.json'))") \
   ~/.config/cctrack/prices.json
# edit ~/.config/cctrack/prices.json
```

cctrack always prefers your copy if it exists.

## Cost Color Coding

All cost values are color coded consistently across every command:

| Color  | Threshold     |
|--------|---------------|
| Green  | < $0.25       |
| Yellow | $0.25 – $1.00 |
| Red    | > $1.00       |

## Roadmap

- **Available** — Claude Code and OpenCode tracking, OpenAI Usage API import, reports, and local activity heatmap/SVG export
- **Exploring** — Opt-in shareable profiles and private team boards
- **Future** — More local AI usage sources based on demand

Product site: [cctrack.sandeepk.dev](https://cctrack.sandeepk.dev/)

## License

MIT
