from datetime import date, timedelta
from pathlib import Path

import typer

from .parser import parse_all
from .config import (
    load_prices, get_user_prices_path, get_bundled_prices_path, get_claude_projects_dir,
    get_openai_api_key, save_openai_api_key, get_openai_key_path,
)
from .storage import sync, query_range, query_all, query_by_project, get_date_bounds, get_db_path, query_today_totals
from .opencode import get_db_path as get_opencode_db_path
from .stats import summarize_rows, daily_breakdown
from .heatmap import METRICS, aggregate_daily, export_svg, render_heatmap
from .display import (
    console,
    render_today_table,
    render_weekly_table,
    render_model_breakdown,
    render_stats_table,
    render_projects_table,
    render_setup_guide,
    chart_weekly_trend,
    chart_model_bars,
    chart_projects_bars,
    chart_today_tokens,
    print_no_data,
    print_sync_note,
)

from rich.table import Table

app = typer.Typer(help="Track AI usage and visualize your activity.")


@app.command()
def today(no_chart: bool = typer.Option(False, "--no-chart", help="Skip the token breakdown chart.")):
    """Show token usage and cost for today."""
    new = sync()
    d = date.today()
    rows = query_range(d, d)

    if not rows:
        print_no_data("today")
        print_sync_note(new)
        raise typer.Exit()

    stats = summarize_rows(rows)
    console.print(render_today_table(stats, d))
    if not no_chart:
        chart_today_tokens(stats)
    print_sync_note(new)


@app.command()
def weekly(no_chart: bool = typer.Option(False, "--no-chart", help="Skip the trend line chart.")):
    """Show token usage and cost for the last 7 days."""
    new = sync()
    end = date.today()
    start = end - timedelta(days=6)
    rows = query_range(start, end)

    days = daily_breakdown(rows, days=7)

    console.print(render_weekly_table(days))
    console.print(render_model_breakdown(days))
    if not no_chart:
        chart_weekly_trend(days)
    print_sync_note(new)


@app.command()
def stats(no_chart: bool = typer.Option(False, "--no-chart", help="Skip the model cost bar chart.")):
    """All-time token usage and cost summary."""
    new = sync()
    rows = query_all()

    if not rows:
        print_no_data("any period (no sessions found)")
        print_sync_note(new)
        raise typer.Exit()

    earliest, latest = get_date_bounds()
    start = date.fromisoformat(earliest)
    end = date.fromisoformat(latest)
    days_count = (end - start).days + 1
    all_rows = query_range(start, end)
    days = daily_breakdown(all_rows, days=days_count)

    console.print(render_stats_table(days, earliest, latest))
    if not no_chart:
        chart_model_bars(days)
    print_sync_note(new)


@app.command()
def projects(no_chart: bool = typer.Option(False, "--no-chart", help="Skip the project cost bar chart.")):
    """Show token usage broken down by project."""
    new = sync()
    rows = query_by_project()

    if not rows:
        print_no_data("any project (no sessions found)")
        print_sync_note(new)
        raise typer.Exit()

    console.print(render_projects_table(rows))
    if not no_chart:
        chart_projects_bars(rows)
    print_sync_note(new)


@app.command()
def heatmap(
    metric: str = typer.Option("tokens", "--metric", help="Heatmap intensity: tokens, cost, or active-days."),
    days: int = typer.Option(365, "--days", min=1, max=1825, help="History window (1–1825 days)."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Export a shareable SVG to this path."),
):
    """Show your local AI activity heatmap, or export it as an SVG."""
    if metric not in METRICS:
        raise typer.BadParameter(f"choose one of: {', '.join(METRICS)}", param_hint="--metric")

    new = sync()
    end = date.today()
    start = end - timedelta(days=days - 1)
    rows = query_range(start, end)
    values = aggregate_daily(rows, metric)

    if output:
        saved = export_svg(values, start, end, metric, output)
        console.print(f"[green]Heatmap saved to {saved}[/green]")
    else:
        console.print(render_heatmap(values, start, end, metric, width=console.width))

    if not rows:
        console.print("[dim]No usage in this period yet. cctrack reads supported local usage data.[/dim]")
    print_sync_note(new)


@app.command()
def prompt(
    format: str = typer.Option("both", "--format", "-f", help="Output format: 'tokens', 'cost', or 'both'."),
):
    """Print a compact usage string for shell prompt integration.

    Reads SQLite only — never re-parses JSONL. Safe to call on every prompt.
    Prints nothing if no data exists yet.
    """
    result = query_today_totals()
    if result is None:
        return  # degrade silently

    total_tokens, total_cost = result

    def _fmt_tokens(n: int) -> str:
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.0f}k"
        return str(n)

    if format == "tokens":
        out = f"[CC {_fmt_tokens(total_tokens)}]"
    elif format == "cost":
        out = f"[CC ${total_cost:.2f}]"
    else:
        out = f"[CC {_fmt_tokens(total_tokens)} · ${total_cost:.2f}]"

    print(out)  # plain print — no Rich markup, must be embeddable in PS1


@app.command()
def setup():
    """Show configuration paths and a getting-started guide."""
    render_setup_guide(
        projects_dir=str(get_claude_projects_dir()),
        db_path=str(get_db_path()),
        prices_path=str(get_bundled_prices_path()),
        user_prices_path=str(get_user_prices_path()),
        openai_key_path=str(get_openai_key_path()),
        opencode_db_path=str(get_opencode_db_path() or "not found"),
    )


@app.command(name="openai-sync")
def openai_sync(
    api_key: str = typer.Option(None, "--api-key", "-k", help="OpenAI API key (saved to ~/.config/cctrack/openai_key)."),
    days: int = typer.Option(30, "--days", "-d", help="How many days of history to fetch (max 90)."),
):
    """Fetch token usage from the OpenAI Usage API and store it in the local DB.

    Requires an API key with the usage.read permission.
    The key is saved to ~/.config/cctrack/openai_key for future runs.
    You can also set the OPENAI_API_KEY environment variable.
    """
    from .openai_client import fetch_openai_usage
    from .storage import upsert_entries, init_db

    if api_key:
        save_openai_api_key(api_key)
        console.print(f"[dim]API key saved to {get_openai_key_path()}[/dim]")

    key = get_openai_api_key()
    if not key:
        console.print(
            "[red]No OpenAI API key found.[/red]\n"
            "Pass one with [bold]--api-key sk-...[/bold] or set [bold]OPENAI_API_KEY[/bold]."
        )
        raise typer.Exit(1)

    days = max(1, min(days, 90))
    console.print(f"[dim]Fetching OpenAI usage for the last {days} days…[/dim]")

    try:
        entries = fetch_openai_usage(key, days=days)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if not entries:
        console.print("[yellow]No usage data returned from OpenAI.[/yellow]")
        raise typer.Exit()

    init_db()
    new = upsert_entries(entries)
    console.print(f"[green]Synced {len(entries)} OpenAI usage records ({new} new).[/green]")


@app.command()
def debug():
    """Print raw token entries parsed from local Claude Code sessions."""
    entries = parse_all()
    if not entries:
        console.print("[yellow]No Claude Code sessions found.[/yellow]")
        raise typer.Exit()

    table = Table(title=f"Raw Token Data ({len(entries)} entries)")
    table.add_column("Timestamp", style="dim")
    table.add_column("Model")
    table.add_column("Project")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Cache Write", justify="right")
    table.add_column("Cache Read", justify="right")

    for e in entries[-20:]:
        table.add_row(
            e.timestamp.strftime("%Y-%m-%d %H:%M"),
            e.model,
            e.project[:40],
            str(e.input_tokens),
            str(e.output_tokens),
            str(e.cache_write_tokens),
            str(e.cache_read_tokens),
        )

    console.print(table)
    console.print(f"\n[dim]Showing last 20 of {len(entries)} total entries[/dim]")


@app.command()
def prices():
    """Show current model pricing and where it's loaded from."""
    data = load_prices()
    source = data["_source"]
    user_path = get_user_prices_path()

    table = Table(title="Model Pricing (USD per 1M tokens)")
    table.add_column("Model")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Cache Write", justify="right")
    table.add_column("Cache Read", justify="right")

    for model, p in data.get("models", {}).items():
        table.add_row(
            model,
            f"${p['input']:.2f}",
            f"${p['output']:.2f}",
            f"${p['cache_write']:.2f}",
            f"${p['cache_read']:.2f}",
        )

    default = data.get("default", {})
    table.add_row(
        "[dim]default (fallback)[/dim]",
        f"${default['input']:.2f}",
        f"${default['output']:.2f}",
        f"${default['cache_write']:.2f}",
        f"${default['cache_read']:.2f}",
        style="dim",
    )

    console.print(table)
    console.print(f"\n[dim]Loaded from: {source}[/dim]")
    if source == str(get_bundled_prices_path()):
        console.print(f"[dim]To override, copy to: {user_path}[/dim]")


if __name__ == "__main__":
    app()
