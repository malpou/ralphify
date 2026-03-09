import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from ralphify.detector import detect_project

app = typer.Typer(help="Harness toolkit for autonomous AI coding loops.")

CONFIG_FILENAME = "ralph.toml"

RALPH_TOML_TEMPLATE = """\
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
prompt = "PROMPT.md"
"""

PROMPT_TEMPLATE = """\
# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

- Implement one thing per iteration
- Search before creating anything new
- No placeholder code — full implementations only
- Run tests and fix failures before committing
- Commit with a descriptive message

<!-- Add your project-specific instructions below -->
"""


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files."),
) -> None:
    """Initialize ralph config and prompt template."""
    config_path = Path(CONFIG_FILENAME)
    prompt_path = Path("PROMPT.md")

    project_type = detect_project()

    if config_path.exists() and not force:
        rprint(f"[yellow]{CONFIG_FILENAME} already exists. Use --force to overwrite.[/yellow]")
        raise typer.Exit(1)

    config_path.write_text(RALPH_TOML_TEMPLATE)
    rprint(f"[green]Created {CONFIG_FILENAME}[/green]")

    if prompt_path.exists() and not force:
        rprint(f"[yellow]PROMPT.md already exists. Use --force to overwrite.[/yellow]")
    else:
        prompt_path.write_text(PROMPT_TEMPLATE)
        rprint(f"[green]Created PROMPT.md[/green]")

    rprint(f"\nDetected project type: [bold]{project_type}[/bold]")
    rprint("Edit PROMPT.md to customize your agent's behavior.")


@app.command()
def run(
    n: Optional[int] = typer.Option(None, "-n", help="Max number of iterations. Infinite if not set."),
) -> None:
    """Run the autonomous coding loop."""
    config_path = Path(CONFIG_FILENAME)

    if not config_path.exists():
        rprint(f"[red]{CONFIG_FILENAME} not found. Run 'ralph init' first.[/red]")
        raise typer.Exit(1)

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    agent = config["agent"]
    command = agent["command"]
    args = agent.get("args", [])
    prompt_file = agent["prompt"]

    prompt_path = Path(prompt_file)
    if not prompt_path.exists():
        rprint(f"[red]Prompt file '{prompt_file}' not found.[/red]")
        raise typer.Exit(1)

    cmd = [command] + args
    iteration = 0

    try:
        while True:
            iteration += 1
            if n is not None and iteration > n:
                break

            rprint(f"\n[bold blue]── Iteration {iteration} ──[/bold blue]")
            prompt = prompt_path.read_text()
            subprocess.run(cmd, input=prompt, text=True)

    except KeyboardInterrupt:
        pass

    rprint(f"\n[green]Completed {iteration if n is None else min(iteration, n)} iteration(s).[/green]")
