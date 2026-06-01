"""CLI commands for NTS automation."""

import argparse
import sys
import json
from typing import Optional
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from core.config import SimulationConfig
from core.validator import validate_file, get_validation_summary
from core.input_builder import InputBuilder, build_input_from_file
from execution.parallel import run_parallel, run_batch
from utils.paths import (
    list_input_files, list_output_files, get_next_input_index,
    ensure_directories, verify_solver_binaries, AVAILABLE_SOLVERS,
    get_template_path, PLOTS_DIR
)
from utils.logger import setup_logging, get_logger

console = Console()


def cmd_generate(args):
    """Generate input.txt file from configuration."""
    logger = get_logger()
    
    config_file = args.config
    output_name = args.output
    
    console.print(f"[bold blue]Generating input from:[/] {config_file}")
    
    # Validate configuration
    result = validate_file(config_file)
    if not result:
        console.print("[bold red]✗ Configuration validation failed:[/]")
        for error in result.errors:
            console.print(f"  • {error}")
        return 1
    
    console.print("[bold green]✓ Configuration is valid[/]")
    
    # Load and display summary
    config = SimulationConfig.from_json_file(config_file)
    console.print("\n" + get_validation_summary(config))
    
    # Determine output path
    if output_name is None:
        ensure_directories()
        index = get_next_input_index()
        from utils.paths import get_input_path
        output_file = str(get_input_path(index))
    else:
        output_file = output_name
    
    # Generate input file
    try:
        builder = InputBuilder(config)
        builder.save(output_file)
        console.print(f"\n[bold green]✓ Input file generated:[/] {output_file}")
        
        # Show preview
        if args.preview:
            console.print("\n[bold]Preview:[/]")
            console.print(builder.preview())
        
        logger.info(f"Generated input file: {output_file}")
        return 0
    
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/] {str(e)}")
        logger.error(f"Failed to generate input: {str(e)}")
        return 1


def cmd_validate(args):
    """Validate a configuration file."""
    config_file = args.config
    
    console.print(f"[bold blue]Validating configuration:[/] {config_file}")
    
    result = validate_file(config_file)
    
    if result:
        console.print("[bold green]✓ Configuration is valid[/]")
        
        # Show summary
        config = SimulationConfig.from_json_file(config_file)
        console.print("\n" + get_validation_summary(config))
        return 0
    else:
        console.print("[bold red]✗ Validation failed:[/]")
        for error in result.errors:
            console.print(f"  • {error}")
        return 1


def cmd_run(args):
    """Run simulations."""
    logger = get_logger()
    
    ensure_directories()
    
    # Check solvers
    solver = args.solver
    if solver not in AVAILABLE_SOLVERS:
        console.print(f"[bold red]✗ Unknown solver:[/] {solver}")
        console.print(f"Available solvers: {', '.join(AVAILABLE_SOLVERS)}")
        return 1
    
    solver_status = verify_solver_binaries()
    if not solver_status[solver]:
        console.print(f"[bold red]✗ Solver binary not found:[/] {solver}")
        return 1
    
    # Get input files
    if args.inputs:
        input_files = args.inputs
    else:
        # Use all input files in inputs directory
        input_files = [str(f) for f in list_input_files()]
        if not input_files:
            console.print("[bold red]✗ No input files found in outputs/inputs/[/]")
            return 1
    
    console.print(f"[bold blue]Running {len(input_files)} simulation(s) with {solver}[/]")
    
    # Prepare tasks
    from utils.paths import RESULTS_DIR
    tasks = []
    for i, input_file in enumerate(input_files, 1):
        output_file = RESULTS_DIR / f"output_{i:03d}.json"
        tasks.append((solver, input_file, str(output_file)))
    
    # Run with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task(f"Running simulations...", total=len(tasks))
        
        def progress_callback(completed, total):
            progress.update(task, completed=completed)
        
        result = run_parallel(tasks, nproc=args.parallel, callback=progress_callback)
    
    # Show results
    console.print("\n" + result.get_summary())
    
    if result.failure_count > 0:
        return 1
    
    return 0


def cmd_list(args):
    """List input files or results."""
    if args.type == 'inputs':
        files = list_input_files()
        title = "Input Files"
    else:
        files = list_output_files()
        title = "Output Files"
    
    if not files:
        console.print(f"[yellow]No {args.type} found[/]")
        return 0
    
    table = Table(title=title)
    table.add_column("Index", style="cyan", no_wrap=True)
    table.add_column("Filename", style="green")
    table.add_column("Size", justify="right", style="yellow")
    
    for i, file_path in enumerate(files, 1):
        size_kb = file_path.stat().st_size / 1024
        table.add_row(str(i), file_path.name, f"{size_kb:.1f} KB")
    
    console.print(table)
    return 0


def cmd_show(args):
    """Show result details."""
    result_file = args.result
    
    if not Path(result_file).exists():
        console.print(f"[bold red]✗ File not found:[/] {result_file}")
        return 1
    
    # Output files are already JSON - just display them
    try:
        with open(result_file, 'r') as f:
            data = json.load(f)
        
        console.print("\n[bold cyan]Simulation Result:[/]")
        console.print_json(data=data)
        
        # Show summary
        if 'STATUS' in data:
            status = "✓ Success" if data['STATUS'] == 0 else "✗ Failed"
            console.print(f"\n[bold]Status:[/] {status}")
        if 'ITER' in data:
            console.print(f"[bold]Iterations:[/] {data['ITER']}")
        if 'CPU' in data:
            console.print(f"[bold]CPU Time:[/] {data['CPU']:.6f}s")
            
    except json.JSONDecodeError as e:
        console.print(f"[bold red]✗ Invalid JSON:[/] {e}")
        return 1
    except Exception as e:
        console.print(f"[bold red]✗ Error reading file:[/] {e}")
        return 1
    
    return 0


def cmd_status(args):
    """Show system status."""
    ensure_directories()
    
    console.print("[bold]NTS Automation System Status[/]\n")
    
    # Solver status
    console.print("[bold blue]Solvers:[/]")
    solver_status = verify_solver_binaries()
    for solver, exists in solver_status.items():
        status = "[green]✓[/]" if exists else "[red]✗[/]"
        console.print(f"  {status} {solver}")
    
    # File counts
    console.print("\n[bold blue]Files:[/]")
    input_files = list_input_files()
    output_files = list_output_files()
    console.print(f"  • Input files: {len(input_files)}")
    console.print(f"  • Output files: {len(output_files)}")
    
    # Template
    template_path = get_template_path()
    template_exists = template_path.exists()
    status = "[green]✓[/]" if template_exists else "[red]✗[/]"
    console.print(f"\n[bold blue]Template:[/]")
    console.print(f"  {status} {template_path}")
    
    return 0


def _load_mflux(result_path: Path) -> list[list[float]]:
    with open(result_path, "r") as f:
        data = json.load(f)

    if "MFLUX" not in data:
        raise ValueError("Result file does not contain 'MFLUX'")

    mflux = data["MFLUX"]
    if not isinstance(mflux, list) or not mflux:
        raise ValueError("MFLUX is empty or invalid")

    first_row = mflux[0]
    if not isinstance(first_row, list) or not first_row:
        raise ValueError("MFLUX must be a 2D array")

    row_len = len(first_row)
    for row in mflux:
        if not isinstance(row, list) or len(row) != row_len:
            raise ValueError("MFLUX rows must have consistent length")

    return mflux


def _select_result_file(result_path: Optional[str]) -> Path:
    if result_path:
        return Path(result_path)

    files = sorted(PLOTS_DIR.parent.glob("output_*.json"))
    if not files:
        raise FileNotFoundError("No output files found in outputs/results/")

    return files[-1]


def _get_next_plot_index() -> int:
    existing = list(PLOTS_DIR.glob("plot_*.png"))
    if not existing:
        return 1

    indices = []
    for path in existing:
        try:
            num_str = path.stem.split("_")[1]
            indices.append(int(num_str))
        except (IndexError, ValueError):
            continue

    return max(indices) + 1 if indices else 1


def cmd_plot(args):
    """Plot MFLUX as a 2D heatmap."""
    logger = get_logger()
    ensure_directories()

    try:
        result_file = _select_result_file(args.result)
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/] {str(e)}")
        return 1

    if not result_file.exists():
        console.print(f"[bold red]✗ File not found:[/] {result_file}")
        return 1

    try:
        mflux = _load_mflux(result_file)
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/] {str(e)}")
        return 1

    if args.out is None:
        index = _get_next_plot_index()
        plot_path = PLOTS_DIR / f"plot_{index:03d}.png"
    else:
        plot_path = Path(args.out)

    if args.show:
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
    else:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

    try:
        fig, ax = plt.subplots(figsize=(7.5, 6.0), dpi=150)
    except Exception:
        if args.show:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            console.print("[yellow]GUI backend unavailable; saving PNG only.[/]")
            fig, ax = plt.subplots(figsize=(7.5, 6.0), dpi=150)
        else:
            raise
    im = ax.imshow(mflux, origin="lower", cmap="viridis", aspect="auto")
    ax.set_title("Neutron Flux (MFLUX)")
    ax.set_xlabel("X index")
    ax.set_ylabel("Y index")

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Flux intensity")

    plot_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(plot_path, bbox_inches="tight")

    if args.show:
        if plt.get_backend().lower() == "agg":
            console.print("[yellow]Plot saved (no GUI backend available). Use the PNG output instead.[/]")
        else:
            plt.show()

    plt.close(fig)

    console.print(f"[bold green]✓ Plot saved:[/] {plot_path}")
    logger.info(f"Plot saved: {plot_path}")
    return 0


def create_parser():
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="NTS Automation - Neutron Transport Simulation Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # No verbose flag needed - logs are minimal by default
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate input.txt from configuration')
    gen_parser.add_argument('config', help='Configuration JSON file')
    gen_parser.add_argument('-o', '--output', help='Output file path (default: auto-numbered)')
    gen_parser.add_argument('-p', '--preview', action='store_true', help='Show preview of generated input')
    gen_parser.set_defaults(func=cmd_generate)
    
    # Validate command
    val_parser = subparsers.add_parser('validate', help='Validate configuration file')
    val_parser.add_argument('config', help='Configuration JSON file')
    val_parser.set_defaults(func=cmd_validate)
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run simulations')
    run_parser.add_argument('-s', '--solver', default='NTS_DD', choices=AVAILABLE_SOLVERS, 
                           help='Solver to use (default: NTS_DD)')
    run_parser.add_argument('-i', '--inputs', nargs='+', help='Input files (default: all in outputs/inputs/)')
    run_parser.add_argument('-p', '--parallel', type=int, default=4, 
                           help='Number of parallel processes (default: 4)')
    run_parser.set_defaults(func=cmd_run)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List input files or results')
    list_parser.add_argument('type', choices=['inputs', 'outputs'], help='What to list')
    list_parser.set_defaults(func=cmd_list)
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show result details')
    show_parser.add_argument('result', help='Result file path (JSON)')
    show_parser.set_defaults(func=cmd_show)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    status_parser.set_defaults(func=cmd_status)

    # Plot command
    plot_parser = subparsers.add_parser('plot', help='Plot MFLUX heatmap from results')
    plot_parser.add_argument('-r', '--result', help='Result file path (JSON). Default: latest output_*.json')
    plot_parser.add_argument('-o', '--out', help='Output plot path (default: outputs/results/plots/plot_###.png)')
    plot_parser.add_argument('--show', action='store_true', help='Display the plot window')
    plot_parser.set_defaults(func=cmd_plot)
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Logging already setup in main.py with WARNING level
    
    # Execute command
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
