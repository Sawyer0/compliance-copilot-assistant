"""Main CLI entry point for the compliance ingestion engine."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.config import get_settings
from .core.logging import setup_logging, get_logger
from .core.registry import SourceRegistry
from .services.ingestion_engine import IngestionEngine
from .models.ingestion import IngestionJob, JobType

console = Console()
logger = get_logger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config-file', type=click.Path(exists=True), help='Configuration file path')
def cli(verbose: bool, config_file: Optional[str]) -> None:
    """Compliance Document Ingestion Engine CLI."""
    # Setup logging
    if verbose:
        import os
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    setup_logging()
    
    if config_file:
        console.print(f"Using config file: {config_file}")


@cli.command()
def sources() -> None:
    """List all registered sources."""
    registry = SourceRegistry()
    sources = registry.list_sources()
    
    if not sources:
        console.print("[yellow]No sources registered.[/yellow]")
        return
    
    table = Table(title="Registered Sources")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Last Fetched", style="dim")
    table.add_column("Documents", justify="right")
    table.add_column("Success Rate", justify="right")
    
    for source in sources:
        config = source.config
        status = "🟢 Active" if config.is_active else "🔴 Inactive"
        last_fetched = config.last_fetched.strftime("%Y-%m-%d %H:%M") if config.last_fetched else "Never"
        
        total_docs = source.total_documents_fetched
        success_rate = (source.successful_fetches / total_docs * 100) if total_docs > 0 else 0
        
        table.add_row(
            config.name,
            config.source_type.value,
            status,
            last_fetched,
            str(total_docs),
            f"{success_rate:.1f}%"
        )
    
    console.print(table)


@cli.command()
@click.argument('source_name', required=False)
@click.option('--all', 'all_sources', is_flag=True, help='Process all active sources')
@click.option('--priority', default=5, help='Job priority (1-10)')
def ingest(source_name: Optional[str], all_sources: bool, priority: int) -> None:
    """Run document ingestion for specified source(s)."""
    
    if not source_name and not all_sources:
        console.print("[red]Error: Specify a source name or use --all flag[/red]")
        sys.exit(1)
    
    if source_name and all_sources:
        console.print("[red]Error: Cannot specify both source name and --all flag[/red]")
        sys.exit(1)
    
    async def run_ingestion():
        engine = IngestionEngine()
        
        try:
            if all_sources:
                console.print("[bold blue]Running ingestion for all sources...[/bold blue]")
                result = await engine.process_all_sources()
            else:
                console.print(f"[bold blue]Running ingestion for source: {source_name}[/bold blue]")
                result = await engine.process_single_source(source_name)
            
            # Display results
            console.print("\n[bold green]Ingestion completed![/bold green]")
            
            table = Table(title="Ingestion Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")
            
            table.add_row("Total Documents", str(result.total_documents_processed))
            table.add_row("Successful", str(result.successful_documents))
            table.add_row("Failed", str(result.failed_documents))
            table.add_row("Duration", f"{result.total_execution_time:.2f}s" if result.total_execution_time else "N/A")
            table.add_row("Docs/min", f"{result.documents_per_minute:.1f}" if result.documents_per_minute else "N/A")
            
            console.print(table)
            
            # Show failed documents if any
            if result.failed_documents > 0:
                console.print("\n[yellow]Failed Documents:[/yellow]")
                for task_result in result.task_results:
                    if not task_result.success:
                        console.print(f"  • {task_result.error_message}")
        
        except Exception as e:
            console.print(f"[red]Ingestion failed: {str(e)}[/red]")
            logger.error("Ingestion failed", error=str(e))
            sys.exit(1)
    
    # Run async function
    asyncio.run(run_ingestion())


@cli.command()
@click.argument('source_name')
def test_source(source_name: str) -> None:
    """Test connectivity to a specific source."""
    
    async def test_connectivity():
        registry = SourceRegistry()
        source = registry.get_source_by_name(source_name)
        
        if not source:
            console.print(f"[red]Source '{source_name}' not found[/red]")
            sys.exit(1)
        
        from .fetchers import NISTFetcher, EUAIActFetcher, FPFFetcher
        
        # Get appropriate fetcher
        fetcher_class = NISTFetcher  # Default, should be determined dynamically
        if 'nist' in source_name.lower():
            fetcher_class = NISTFetcher
        elif 'eu' in source_name.lower() or 'ai act' in source_name.lower():
            fetcher_class = EUAIActFetcher
        elif 'fpf' in source_name.lower():
            fetcher_class = FPFFetcher
        
        console.print(f"Testing connectivity to: [bold]{source_name}[/bold]")
        
        async with fetcher_class(source) as fetcher:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Checking connectivity...", total=None)
                
                is_healthy = await fetcher.health_check()
                
                if is_healthy:
                    console.print("[green]✓ Source is accessible[/green]")
                else:
                    console.print("[red]✗ Source is not accessible[/red]")
                    sys.exit(1)
    
    asyncio.run(test_connectivity())


@cli.command()
def status() -> None:
    """Show overall system status."""
    settings = get_settings()
    registry = SourceRegistry()
    
    console.print("[bold]Compliance Ingestion Engine Status[/bold]\n")
    
    # Configuration
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value")
    
    config_table.add_row("Base Directory", str(settings.base_dir))
    config_table.add_row("Log Level", settings.log_level)
    config_table.add_row("OCR Enabled", "Yes" if settings.ocr_enabled else "No")
    config_table.add_row("Max Concurrent Jobs", str(settings.max_concurrent_jobs))
    config_table.add_row("Deduplication", "Enabled" if settings.enable_deduplication else "Disabled")
    
    console.print(config_table)
    console.print()
    
    # Sources summary
    sources = registry.list_sources()
    active_sources = [s for s in sources if s.config.is_active]
    
    sources_table = Table(title="Sources Summary")
    sources_table.add_column("Metric", style="cyan")
    sources_table.add_column("Count", justify="right")
    
    sources_table.add_row("Total Sources", str(len(sources)))
    sources_table.add_row("Active Sources", str(len(active_sources)))
    sources_table.add_row("Inactive Sources", str(len(sources) - len(active_sources)))
    
    console.print(sources_table)
    console.print()
    
    # Storage info
    storage_table = Table(title="Storage")
    storage_table.add_column("Directory", style="cyan")
    storage_table.add_column("Path")
    storage_table.add_column("Exists")
    
    directories = [
        ("Raw", settings.raw_output_path),
        ("Parsed", settings.parsed_output_path),
        ("Metadata", settings.metadata_output_path),
        ("Logs", settings.logs_output_path),
    ]
    
    for name, path in directories:
        exists = "✓" if path.exists() else "✗"
        storage_table.add_row(name, str(path), exists)
    
    console.print(storage_table)


@cli.command()
def init() -> None:
    """Initialize the ingestion engine with sample configuration."""
    console.print("[bold]Initializing Compliance Ingestion Engine...[/bold]")
    
    settings = get_settings()
    
    # Create sample sources configuration
    from .registry.sources import create_sample_sources
    create_sample_sources()
    
    console.print("[green]✓ Sample sources configuration created[/green]")
    console.print("[green]✓ Output directories created[/green]")
    console.print("[green]✓ Initialization complete![/green]")
    
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Review and customize sources in registry/sources.yaml")
    console.print("2. Run: [cyan]python -m ingestion.main sources[/cyan] to view sources")
    console.print("3. Run: [cyan]python -m ingestion.main ingest --all[/cyan] to start ingestion")


if __name__ == "__main__":
    cli()
