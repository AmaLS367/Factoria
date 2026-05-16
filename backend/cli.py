import argparse
import json

from agents.research_agent import ResearchAgent, build_search_query, ensure_sources_field
from clients.llm_client import LLMClient
from config import settings
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from tools.web_search import WebSearchTool
from utils.db_writer import init_db, save_results_bulk

# Force UTF-8 for Windows if needed, but rich usually handles it
console = Console()

def process_single_item(item_id: str) -> None:
    console.print(
        Panel(
            f"[bold blue]Processing {settings.item_label}:[/] [green]{item_id}[/]",
            expand=False
        )
    )

    with Live(Spinner("dots", text="Consulting AI..."), refresh_per_second=10, transient=True):
        agent = ResearchAgent(llm_client=LLMClient())

        try:
            data = agent.collect_item(item_id)
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")
            return

    if not data:
        console.print("[bold yellow]AI returned no data or data was invalid.[/]")
        return

    # Display results
    title = f"Extracted Info: {item_id}"
    table = Table(
        title=title,
        show_header=True,
        header_style="bold blue",
        border_style="bright_black"
    )
    table.add_column("Field", style="dim", width=20)
    table.add_column("Value", style="bold white")

    # Add identifier field first
    table.add_row(settings.column_name, f"[green]{item_id}[/]")

    for field, value in data.items():
        if field == settings.column_name:
            continue
        table.add_row(str(field), str(value))

    console.print(table)

    # Save to DB
    output_fields = ensure_sources_field(settings.target_fields)
    init_db(output_fields)

    # Prepare row for DB
    row_data = (item_id, *[
        data.get(f, "Not found")
        for f in output_fields
        if f != settings.column_name
    ])

    save_results_bulk([row_data], output_fields)
    console.print(f"\n[bold green]Success![/] [dim]({settings.db_path})[/]")


def search_item(item_id: str) -> None:
    output_fields = ensure_sources_field(settings.target_fields)
    query = build_search_query(item_id, settings.item_label, output_fields)
    results = WebSearchTool().search(query)
    print(json.dumps([result.to_dict() for result in results], ensure_ascii=False, indent=2))

def main() -> None:
    parser = argparse.ArgumentParser(description="AI Data Collector CLI")
    parser.add_argument("item", nargs="*", help="Item identifier or search query")
    parser.add_argument("--search", action="store_true", help="Run only the web search tool")
    args = parser.parse_args()

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
