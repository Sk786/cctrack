from datetime import date

import plotext as plt
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from .stats import ModelStats, DaySummary

console = Console()

# plotext color names that map to our cost thresholds
_PLT_GREEN = "green"
_PLT_YELLOW = "yellow"
_PLT_RED = "red"


def _plt_color(cost: float) -> str:
    if cost >= 1.0:
        return _PLT_RED
    if cost >= 0.25:
        return _PLT_YELLOW
    return _PLT_GREEN


def chart_weekly_trend(days: list[DaySummary]):
    """Line chart of daily cost over the 7-day window."""
    labels = [d.day.strftime("%a\n%m/%d") for d in days]
    costs = [round(d.total_cost, 4) for d in days]

    width = min(console.width, 100)
    plt.clf()
    plt.plotsize(width, 14)
    plt.theme("dark")
    plt.title("Daily Spend (USD)")
    plt.xlabel("Day")
    plt.ylabel("Cost $")

    # color the line by the max cost of the week
    max_cost = max(costs) if any(costs) else 0
    line_color = _plt_color(max_cost)

    plt.plot(costs, color=line_color, marker="braille")
    plt.xticks(list(range(1, len(labels) + 1)), labels)
    plt.yfrequency(5)
    plt.show()


def chart_model_bars(days: list[DaySummary]):
    """Horizontal bar chart of cost per model (all-time or period)."""
    combined: dict[str, float] = {}
    for day in days:
        for model, s in day.models.items():
            combined[model] = combined.get(model, 0.0) + s.cost

    if not combined:
        return

    sorted_models = sorted(combined.items(), key=lambda x: x[1])
    names = [short_model(m) for m, _ in sorted_models]
    costs = [round(c, 4) for _, c in sorted_models]
    colors = [_plt_color(c) for c in costs]

    width = min(console.width, 100)
    plt.clf()
    plt.plotsize(width, max(6, len(names) * 3 + 4))
    plt.theme("dark")
    plt.title("Cost by Model (USD)")
    plt.bar(names, costs, orientation="horizontal", color=colors)
    plt.show()


def chart_projects_bars(rows: list[dict]):
    """Horizontal bar chart of cost per project, top 10."""
    from .stats import cost_for_row

    projects: dict[str, float] = {}
    for row in rows:
        p = row["project"]
        projects[p] = projects.get(p, 0.0) + cost_for_row(row)

    top = sorted(projects.items(), key=lambda x: x[1])[-10:]
    names = [p.split("/")[-1] or p for p, _ in top]
    costs = [round(c, 4) for _, c in top]
    colors = [_plt_color(c) for c in costs]

    width = min(console.width, 100)
    plt.clf()
    plt.plotsize(width, max(6, len(names) * 3 + 4))
    plt.theme("dark")
    plt.title("Cost by Project — Top 10 (USD)")
    plt.bar(names, costs, orientation="horizontal", color=colors)
    plt.show()


def chart_today_tokens(stats: dict[str, ModelStats]):
    """Stacked bar showing token type breakdown per model."""
    if not stats:
        return

    models = sorted(stats.keys())
    short = [short_model(m) for m in models]

    inputs = [stats[m].input_tokens for m in models]
    outputs = [stats[m].output_tokens for m in models]
    cache_writes = [stats[m].cache_write_tokens for m in models]
    cache_reads = [stats[m].cache_read_tokens for m in models]

    width = min(console.width, 100)
    plt.clf()
    plt.plotsize(width, 16)
    plt.theme("dark")
    plt.title("Token Breakdown by Type")
    plt.multiple_bar(
        short,
        [inputs, outputs, cache_writes, cache_reads],
        labels=["Input", "Output", "Cache Write", "Cache Read"],
        color=["cyan", "green", "yellow", "magenta"],
    )
    plt.show()

_BAR_WIDTH = 28
_BAR_CHAR = "█"
_EMPTY_CHAR = "░"


def short_model(name: str) -> str:
    """Drop date-stamped snapshot suffixes so tables stay readable."""
    if len(name) > 9 and name[-9] == "-" and name[-8:].isdigit():
        return name[:-9]
    return name


def summarize_models(models: set[str], limit: int = 3) -> str:
    """Short, deduplicated model list for narrow table cells."""
    names = sorted({short_model(m) for m in models})
    if len(names) > limit:
        return ", ".join(names[:limit]) + f" +{len(names) - limit}"
    return ", ".join(names)


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def fmt_cost(cost: float) -> str:
    if cost >= 10:
        return f"${cost:.2f}"
    return f"${cost:.4f}"


def cost_style(cost: float) -> str:
    if cost >= 1.0:
        return "red"
    if cost >= 0.25:
        return "yellow"
    return "green"


def _bar(value: float, max_value: float, width: int = _BAR_WIDTH) -> Text:
    if max_value == 0:
        filled = 0
    else:
        filled = round((value / max_value) * width)
    filled = max(0, min(filled, width))

    style = cost_style(value)
    bar = Text()
    bar.append(_BAR_CHAR * filled, style=style)
    bar.append(_EMPTY_CHAR * (width - filled), style="dim")
    return bar


def render_today_table(stats: dict[str, ModelStats], day: date) -> Table:
    table = Table(
        title=f"Today's Usage — {day.strftime('%A, %B %d %Y')}",
        box=box.ROUNDED,
        show_footer=True,
        padding=(0, 0),
    )
    table.add_column("Model", footer="[bold]TOTAL[/bold]", no_wrap=True, min_width=20)
    table.add_column("Input", justify="right", footer="")
    table.add_column("Output", justify="right", footer="")
    table.add_column("Cache Write", justify="right", footer="")
    table.add_column("Cache Read", justify="right", footer="")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right")

    total_cost = sum(s.cost for s in stats.values())
    total_tokens = sum(s.total_tokens for s in stats.values())

    for model, s in sorted(stats.items()):
        style = cost_style(s.cost)
        table.add_row(
            short_model(model),
            fmt_tokens(s.input_tokens),
            fmt_tokens(s.output_tokens),
            fmt_tokens(s.cache_write_tokens),
            fmt_tokens(s.cache_read_tokens),
            fmt_tokens(s.total_tokens),
            Text(fmt_cost(s.cost), style=style),
        )

    # patch footer for the last two columns
    table.columns[5].footer = Text(fmt_tokens(total_tokens), style="bold")
    table.columns[6].footer = Text(fmt_cost(total_cost), style=f"bold {cost_style(total_cost)}")

    return table


def render_weekly_table(days: list[DaySummary]) -> Table:
    max_cost = max((d.total_cost for d in days), default=0)

    table = Table(
        title=f"Weekly Usage — {days[0].day.strftime('%b %d')} to {days[-1].day.strftime('%b %d, %Y')}",
        box=box.ROUNDED,
        show_footer=True,
    )
    table.add_column("Date", footer="[bold]TOTAL[/bold]")
    table.add_column("Day", style="dim", footer="")
    table.add_column("Tokens", justify="right", footer="")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Spend", no_wrap=True, footer="")

    grand_cost = sum(d.total_cost for d in days)
    grand_tokens = sum(d.total_tokens for d in days)

    for day in days:
        if not day.models:
            table.add_row(
                day.day.strftime("%Y-%m-%d"),
                day.day.strftime("%a"),
                Text("—", style="dim"),
                Text("—", style="dim"),
                Text(_EMPTY_CHAR * _BAR_WIDTH, style="dim"),
            )
            continue

        style = cost_style(day.total_cost)
        table.add_row(
            day.day.strftime("%Y-%m-%d"),
            day.day.strftime("%a"),
            fmt_tokens(day.total_tokens),
            Text(fmt_cost(day.total_cost), style=style),
            _bar(day.total_cost, max_cost),
        )

    table.columns[2].footer = Text(fmt_tokens(grand_tokens), style="bold")
    table.columns[3].footer = Text(fmt_cost(grand_cost), style=f"bold {cost_style(grand_cost)}")

    return table


def render_model_breakdown(days: list[DaySummary]) -> Panel:
    """Side panel showing per-model totals across the period."""
    combined: dict[str, ModelStats] = {}
    for day in days:
        for model, s in day.models.items():
            if model not in combined:
                from .stats import ModelStats as MS
                combined[model] = MS(model=model)
            c = combined[model]
            c.input_tokens += s.input_tokens
            c.output_tokens += s.output_tokens
            c.cache_write_tokens += s.cache_write_tokens
            c.cache_read_tokens += s.cache_read_tokens
            c.reasoning_tokens += s.reasoning_tokens
            c.cost += s.cost

    if not combined:
        return Panel("[dim]No data[/dim]", title="By Model")

    lines = Text()
    for model, s in sorted(combined.items(), key=lambda x: x[1].cost, reverse=True):
        style = cost_style(s.cost)
        lines.append(f"  {short_model(model)}\n", style="bold")
        lines.append(f"    tokens : {fmt_tokens(s.total_tokens)}\n", style="dim")
        lines.append(f"    cost   : ", style="dim")
        lines.append(f"{fmt_cost(s.cost)}\n", style=style)

    return Panel(lines, title="[bold]By Model[/bold]", box=box.ROUNDED, padding=(0, 1))


def render_stats_table(days: list[DaySummary], earliest: str | None, latest: str | None) -> Table:
    combined: dict[str, ModelStats] = {}
    for day in days:
        for model, s in day.models.items():
            if model not in combined:
                from .stats import ModelStats as MS
                combined[model] = MS(model=model)
            c = combined[model]
            c.input_tokens += s.input_tokens
            c.output_tokens += s.output_tokens
            c.cache_write_tokens += s.cache_write_tokens
            c.cache_read_tokens += s.cache_read_tokens
            c.reasoning_tokens += s.reasoning_tokens
            c.cost += s.cost

    span = f"{earliest} → {latest}" if earliest and latest else "no data"
    table = Table(
        title=f"All-Time Usage  [{span}]",
        box=box.ROUNDED,
        show_footer=True,
        padding=(0, 0),
    )
    table.add_column("Model", footer="[bold]TOTAL[/bold]", no_wrap=True, min_width=20)
    table.add_column("Input", justify="right", footer="")
    table.add_column("Output", justify="right", footer="")
    table.add_column("Cache Write", justify="right", footer="")
    table.add_column("Cache Read", justify="right", footer="")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right")

    total_cost = sum(s.cost for s in combined.values())
    total_tokens = sum(s.total_tokens for s in combined.values())

    for model, s in sorted(combined.items(), key=lambda x: x[1].cost, reverse=True):
        style = cost_style(s.cost)
        table.add_row(
            short_model(model),
            fmt_tokens(s.input_tokens),
            fmt_tokens(s.output_tokens),
            fmt_tokens(s.cache_write_tokens),
            fmt_tokens(s.cache_read_tokens),
            fmt_tokens(s.total_tokens),
            Text(fmt_cost(s.cost), style=style),
        )

    table.columns[5].footer = Text(fmt_tokens(total_tokens), style="bold")
    table.columns[6].footer = Text(fmt_cost(total_cost), style=f"bold {cost_style(total_cost)}")
    return table


def render_projects_table(rows: list[dict]) -> Table:
    from .stats import cost_for_row

    # aggregate per project across models
    projects: dict[str, dict] = {}
    for row in rows:
        p = row["project"]
        if p not in projects:
            projects[p] = {
                "input": 0, "output": 0, "cache_write": 0, "cache_read": 0, "reasoning": 0,
                "cost": 0.0, "first_seen": row["first_seen"], "last_seen": row["last_seen"],
                "models": set(),
            }
        d = projects[p]
        d["input"] += row["input_tokens"]
        d["output"] += row["output_tokens"]
        d["cache_write"] += row["cache_write_tokens"]
        d["cache_read"] += row["cache_read_tokens"]
        d["reasoning"] += row.get("reasoning_tokens", 0)
        d["cost"] += cost_for_row(row)
        d["models"].add(row["model"])
        if row["first_seen"] < d["first_seen"]:
            d["first_seen"] = row["first_seen"]
        if row["last_seen"] > d["last_seen"]:
            d["last_seen"] = row["last_seen"]

    sorted_projects = sorted(projects.items(), key=lambda x: x[1]["cost"], reverse=True)

    table = Table(title="Usage by Project", box=box.ROUNDED, show_footer=True)
    table.add_column("Project", footer="[bold]TOTAL[/bold]")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Last Active", style="dim")
    table.add_column("Models", style="dim")

    grand_cost = sum(d["cost"] for d in projects.values())
    grand_tokens = sum(
        d["input"] + d["output"] + d["cache_write"] + d["cache_read"] + d["reasoning"]
        for d in projects.values()
    )

    for project, d in sorted_projects:
        total = d["input"] + d["output"] + d["cache_write"] + d["cache_read"] + d["reasoning"]
        style = cost_style(d["cost"])
        model_names = summarize_models(d["models"], limit=2)
        table.add_row(
            project[:50],
            fmt_tokens(total),
            Text(fmt_cost(d["cost"]), style=style),
            d["last_seen"][:10],
            model_names,
        )

    table.columns[1].footer = Text(fmt_tokens(grand_tokens), style="bold")
    table.columns[2].footer = Text(fmt_cost(grand_cost), style=f"bold {cost_style(grand_cost)}")
    return table


def render_setup_guide(projects_dir: str, db_path: str, prices_path: str, user_prices_path: str, openai_key_path: str = "", opencode_db_path: str = "", codex_sessions_dir: str = ""):
    from rich.padding import Padding

    console.print()
    console.print(Panel(
        Text("cctrack is ready to use!", style="bold green", justify="center"),
        box=box.ROUNDED,
    ))
    console.print()

    console.print("[bold]Data Sources[/bold]")
    console.print(f"  Claude Code sessions : [cyan]{projects_dir}[/cyan]")
    if opencode_db_path:
        console.print(f"  OpenCode database    : [cyan]{opencode_db_path}[/cyan]")
    if codex_sessions_dir:
        console.print(f"  Codex sessions       : [cyan]{codex_sessions_dir}[/cyan]")
    console.print(f"  SQLite database      : [cyan]{db_path}[/cyan]")
    console.print(f"  Bundled prices       : [cyan]{prices_path}[/cyan]")
    console.print(f"  Custom prices (opt.) : [cyan]{user_prices_path}[/cyan]")
    if openai_key_path:
        console.print(f"  OpenAI key (opt.)    : [cyan]{openai_key_path}[/cyan]")
    console.print()

    console.print("[bold]Commands[/bold]")
    cmds = [
        ("cctrack today",        "Token usage for today"),
        ("cctrack weekly",       "Last 7 days breakdown + bar chart"),
        ("cctrack heatmap",      "AI activity calendar + shareable SVG export"),
        ("cctrack stats",        "All-time summary by model"),
        ("cctrack projects",     "Usage broken down by project"),
        ("cctrack prices",       "Show model pricing"),
        ("cctrack prompt",       "Compact string for shell prompt"),
        ("cctrack openai-sync",  "Fetch usage from OpenAI Usage API"),
        ("cctrack resync",       "Rebuild the local database from all sources"),
    ]
    for cmd, desc in cmds:
        console.print(f"  [bold cyan]{cmd:<24}[/bold cyan] {desc}")
    console.print()

    console.print("[bold]Shell Prompt Integration[/bold]")
    console.print("  Add one line to your shell config to see today's spend on every prompt:\n")
    console.print("  [dim]# bash (~/.bashrc) or zsh (~/.zshrc)[/dim]")
    console.print('  [bold green]export PS1="$(cctrack-prompt) $PS1"[/bold green]\n')
    console.print("  [dim]# fish (~/.config/fish/config.fish)[/dim]")
    console.print('  [bold green]function fish_prompt; echo (cctrack-prompt) (fish_prompt); end[/bold green]\n')
    console.print("  [dim]# Starship (~/.config/starship.toml)[/dim]")
    console.print("  [bold green][custom.cctrack][/bold green]")
    console.print('  [bold green]command = "cctrack-prompt"[/bold green]')
    console.print('  [bold green]when = "true"[/bold green]\n')
    console.print("  Output format options:  [cyan]--format tokens[/cyan]  [cyan]--format cost[/cyan]  [cyan]--format both[/cyan] (default)\n")

    console.print("[bold]Override Prices[/bold]")
    console.print(f"  Copy the bundled prices.json to [cyan]{user_prices_path}[/cyan]")
    console.print("  and edit the values — cctrack will prefer your copy automatically.")
    console.print()


def print_no_data(period: str):
    console.print(f"[yellow]No usage found for {period}.[/yellow]")


def print_sync_note(new: int):
    if new:
        console.print(f"[dim]Synced {new} new entries.[/dim]")
