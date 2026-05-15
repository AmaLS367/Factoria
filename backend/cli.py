import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner

from clients.llm_client import LLMClient
from config import settings
from promts.generator import generate_prompt
from utils.parse import parse_answer
from utils.db_writer import init_db, save_results_bulk

# Force UTF-8 for Windows if needed, but rich usually handles it
console = Console()

def process_single_item(item_id: str):
    console.print(
        Panel(
            f"[bold blue]Processing {settings.item_label}:[/] [green]{item_id}[/]",
            expand=False
        )
    )

    with Live(Spinner("dots", text="Consulting AI..."), refresh_per_second=10, transient=True):
        client = LLMClient()
        prompt = generate_prompt(item_id, settings.item_label, settings.target_fields)

        try:
            raw_response = client.get_answer(prompt)
            data = parse_answer(raw_response, settings.target_fields)
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")
            return

    if not data:
        console.print("[bold yellow]AI returned no data or data was invalid.[/]")
        return

    # Display results
    title = f"Extracted Info: {item_id}"
    table = Table(title=title, show_header=True, header_style="bold blue", border_style="bright_black")
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
    init_db(settings.target_fields)

    # Prepare row for DB
    row_data = (item_id, *[
        data.get(f, "Not found")
        for f in settings.target_fields
        if f != settings.column_name
    ])

    save_results_bulk([row_data], settings.target_fields)
    console.print(f"\n[bold green]Success![/] [dim]({settings.db_path})[/]")

def main():
    console.print("[bold blue]Welcome to AI Data Collector CLI[/]\n", justify="center")

    if len(sys.argv) > 1:
        item_id = " ".join(sys.argv[1:])
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
