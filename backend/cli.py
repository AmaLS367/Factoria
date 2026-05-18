import os
import sys

# Add the project root to sys.path so 'backend.*' imports work when run as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table

from backend.agents.research_agent import ResearchAgent, build_search_query, ensure_sources_field
from backend.clients.llm_client import LLMClient
from backend.config import settings
from backend.tools.web_search import WebSearchTool
from backend.utils.db_writer import fetch_review_queue, save_single_item, update_field_review

# Force UTF-8 for Windows if needed, but rich usually handles it
console = Console()


def process_single_item(item_id: str) -> None:
    console.print(
        Panel(f"[bold blue]Processing {settings.item_label}:[/] [green]{item_id}[/]", expand=False)
    )

    with Live(Spinner("dots", text="Consulting AI..."), refresh_per_second=10, transient=True):
        agent = ResearchAgent(llm_client=LLMClient())

        try:
            data, conf, usage = agent.collect_item_with_confidence(item_id)
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")
            return

    if not data:
        console.print("[bold yellow]AI returned no data or data was invalid.[/]")
        return

    # Display results
    title = f"Extracted Info: {item_id}"
    table = Table(
        title=title, show_header=True, header_style="bold blue", border_style="bright_black"
    )
    table.add_column("Field", style="dim", width=20)
    table.add_column("Value", style="bold white")

    # Add identifier field first
    table.add_row(settings.column_name, f"[green]{item_id}[/]")

    for field, value in data.items():
        if field == settings.column_name:
            continue
        table.add_row(field, value or "")

    console.print(table)

    # Save to DB
    output_fields = ensure_sources_field(settings.target_fields)
    save_single_item(item_id, data, output_fields, confidence=conf, token_usage=usage)
    console.print(f"\n[bold green]Success![/] [dim]({settings.db_path})[/]")


def search_item(item_id: str) -> None:
    output_fields = ensure_sources_field(settings.target_fields)
    query = build_search_query(item_id, settings.item_label, output_fields)
    results = WebSearchTool().search(query)
    print(json.dumps([result.to_dict() for result in results], ensure_ascii=False, indent=2))


def run_review_mode(limit: int, as_json: bool) -> None:
    queue = fetch_review_queue(status="needs_review", limit=limit)
    if as_json:
        print(json.dumps(queue, ensure_ascii=False, indent=2))
        return

    if not queue:
        console.print("[bold green]No fields need review.[/]")
        return

    console.print(f"[bold blue]Starting review mode for {len(queue)} items...[/]\n")

    for i, item in enumerate(queue):
        field_id = item["field_id"]
        ident_col = item["identifier_column"]
        ident_val = item["identifier_value"]
        console.print(
            Panel(
                f"[bold blue]Review item {i + 1}/{len(queue)}[/]\n"
                f"[bold]Item:[/] {ident_col} = [green]{ident_val}[/]\n"
                f"[bold]Field:[/] {item['field_name']}\n"
                f"[bold]Current Value:[/] {item['field_value']}\n"
                f"[bold]Confidence:[/] {item['confidence']}",
                expand=False,
            )
        )

        while True:
            try:
                choice = (
                    console.input(
                        "[bold cyan]Action [a]pprove, [e]dit, [r]eject, [s]kip, [q]uit: [/]"
                    )
                    .strip()
                    .lower()
                )
            except EOFError:
                console.print("\n[yellow]Review session ended by user.[/]")
                return

            if choice in ("q", "quit"):
                console.print("[yellow]Exiting review mode.[/]")
                return
            elif choice in ("s", "skip"):
                console.print("[yellow]Skipped.[/]\n")
                break
            elif choice in ("a", "approve"):
                update_field_review(field_id=field_id, status="approved")
                console.print("[bold green]Approved![/]\n")
                break
            elif choice in ("r", "reject"):
                update_field_review(field_id=field_id, status="rejected")
                console.print("[bold red]Rejected![/]\n")
                break
            elif choice in ("e", "edit"):
                while True:
                    try:
                        new_val = console.input("[bold yellow]Enter corrected value: [/]").strip()
                    except EOFError:
                        return
                    if new_val:
                        break
                    console.print("[bold red]Value cannot be empty for edit![/]")

                try:
                    note = console.input("[bold yellow]Enter reviewer note (optional): [/]").strip()
                except EOFError:
                    note = ""

                update_field_review(
                    field_id=field_id,
                    status="corrected",
                    field_value=new_val,
                    reviewer_note=note if note else None,
                )
                console.print("[bold green]Corrected and updated![/]\n")
                break
            else:
                console.print("[bold red]Invalid option. Please choose a, e, r, s, or q.[/]")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Data Collector CLI")
    parser.add_argument("item", nargs="*", help="Item identifier or search query")
    parser.add_argument("--search", action="store_true", help="Run only the web search tool")
    parser.add_argument("--review", action="store_true", help="Interactive review mode")
    parser.add_argument("--limit", type=int, default=100, help="Limit number of review items")
    parser.add_argument("--json", action="store_true", help="Print review queue as JSON")
    args = parser.parse_args()

    if args.review:
        run_review_mode(limit=args.limit, as_json=args.json)
        return

    if args.search:
        item_id = " ".join(args.item).strip()
        if not item_id:
            print(json.dumps({"error": "Item identifier cannot be empty"}, ensure_ascii=False))
            return
        search_item(item_id)
        return

    console.print("[bold blue]Welcome to AI Data Collector CLI[/]\n", justify="center")

    if args.item:
        item_id = " ".join(args.item)
    else:
        try:
            item_id = console.input(f"[bold yellow]Enter {settings.item_label}: [/]")
        except EOFError:
            return

    if not item_id.strip():
        console.print("[bold red]Item identifier cannot be empty![/]")
        return

    process_single_item(item_id)


if __name__ == "__main__":
    main()
