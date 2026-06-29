# cctrack

Track and analyze your AI token usage from Claude Code and other CLI agents — directly in the terminal.

No API key needed. Reads local session files, stores in SQLite, shows cost breakdowns with charts.

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
pip install cctrack
```

Or from source:

```bash
git clone https://github.com/yourusername/cctrack
cd cctrack
pip install -e .
```

## Commands

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
│ claude-opus-4-8    │ $15.00 │ $75.00 │      $18.75 │      $1.50 │
│ claude-haiku-4-5   │  $0.80 │  $4.00 │       $1.00 │      $0.08 │
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

1. Claude Code stores full session transcripts at `~/.claude/projects/**/*.jsonl`
2. `cctrack` parses these files and stores token counts in `~/.config/cctrack/usage.db`
3. All commands query SQLite — fast and offline

No API key needed. Everything is local.

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

- **v0.2** — Codex / OpenAI support via the Usage API
- **v0.3** — Gemini CLI support
- **v0.4** — Budget alerts and weekly digest

## License

MIT
