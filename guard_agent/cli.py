"""CLI entry point for guard-agent.

Commands:
  setup    — Auto-configure a coding agent (Claude Code, etc.)
  init     — Create a .guard-agent.yaml template
  analyze  — Inspect codebase and show resilience analysis
  check    — Quick check if a file needs checkpointing (used by hooks)
  guide    — Show VeloC API reference documentation
  serve    — Start the MCP server (stdio transport)
  run      — Run full VeloC agent autonomously (requires LLM key)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click


@click.group()
@click.version_option(package_name="guard-agent")
def cli():
    """guard-agent: Automatic VeloC checkpointing for resilient HPC applications."""
    pass


# ---------------------------------------------------------------------------
# setup — auto-configure coding agent
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--agent", "-a",
    type=click.Choice(["claude-code"]),
    required=True,
    help="Coding agent to configure.",
)
@click.option(
    "--global", "global_scope",
    is_flag=True,
    help="Apply globally (default is project-level).",
)
def setup(agent: str, global_scope: bool):
    """Auto-configure a coding agent for guard-agent integration.

    Adds MCP server, PostToolUse hook, and CLAUDE.md instructions.
    """
    if agent == "claude-code":
        _setup_claude_code(global_scope)


def _setup_claude_code(global_scope: bool):
    """Configure Claude Code with MCP server, hook, and CLAUDE.md."""
    # 1. Settings file
    if global_scope:
        settings_path = Path.home() / ".claude" / "settings.json"
    else:
        settings_path = Path.cwd() / ".claude" / "settings.json"

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings = {}
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Add MCP server
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}
    settings["mcpServers"]["guard-agent"] = {
        "command": "guard-agent",
        "args": ["serve"],
    }

    # Add PostToolUse hook for C/C++ files
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PostToolUse" not in settings["hooks"]:
        settings["hooks"]["PostToolUse"] = []

    # Check if hook already exists
    hook_exists = any(
        h.get("command", "").startswith("guard-agent check")
        for h in settings["hooks"]["PostToolUse"]
    )
    if not hook_exists:
        settings["hooks"]["PostToolUse"].append({
            "matcher": "Edit|Write",
            "command": "guard-agent check $FILEPATH",
        })

    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    click.echo(f"  Updated {settings_path}")

    # 2. CLAUDE.md
    claude_md = Path.cwd() / "CLAUDE.md"
    resilience_section = """\

## Resilience (guard-agent)

After modifying any C/C++ file, perform a resilience check:
1. Call `inspect_codebase` with the modified file paths
2. Review the identified critical state and checkpoint candidates
3. Call `get_checkpoint_plan` with your confirmed critical state
4. Apply the returned VeloC code templates
5. Call `validate_injection` to verify correctness
6. If validation fails, analyze the error and retry from step 1

Use `get_veloc_reference` for VeloC API documentation.
Configuration: .guard-agent.yaml (if present).
"""

    if claude_md.is_file():
        content = claude_md.read_text()
        if "guard-agent" not in content:
            claude_md.write_text(content + resilience_section)
            click.echo(f"  Updated {claude_md}")
        else:
            click.echo(f"  {claude_md} already has guard-agent instructions")
    else:
        claude_md.write_text(resilience_section.lstrip())
        click.echo(f"  Created {claude_md}")

    click.echo("\nSetup complete. guard-agent is now configured for Claude Code.")


# ---------------------------------------------------------------------------
# init — create config file
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--path", "-p", default=".", help="Directory to create config in.")
def init(path: str):
    """Create a .guard-agent.yaml configuration template."""
    from guard_agent.project_config import create_default_config

    config_path = Path(path) / ".guard-agent.yaml"
    if config_path.exists():
        click.echo(f"{config_path} already exists.")
        return

    config_path.write_text(create_default_config())
    click.echo(f"Created {config_path}")


# ---------------------------------------------------------------------------
# analyze — inspect codebase
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("paths", nargs=-1, required=True)
@click.option("--config", "-c", help="Path to .guard-agent.yaml.")
@click.option(
    "--format", "-f", "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
)
def analyze(paths: tuple[str, ...], config: str | None, output_format: str):
    """Inspect source files and show resilience analysis."""
    from guard_agent.analyzer import analyze_project
    from guard_agent.project_config import load_config

    cfg = load_config(path=config)
    inspection = analyze_project(list(paths), cfg)

    if output_format == "json":
        click.echo(inspection.model_dump_json(indent=2))
        return

    # Text output
    click.echo(f"Files analyzed: {len(inspection.files_analyzed)}")
    click.echo(f"Language: {inspection.language}")
    click.echo()

    if inspection.process_structure.uses_mpi:
        ps = inspection.process_structure
        click.echo(f"MPI: rank={ps.rank_variable}, size={ps.size_variable}")
    if inspection.process_structure.uses_openmp:
        click.echo("OpenMP: detected")
    click.echo()

    if inspection.existing_veloc.is_protected:
        click.echo("VeloC: Already instrumented")
        click.echo()

    if inspection.critical_state_candidates:
        click.echo("Critical state candidates:")
        for c in inspection.critical_state_candidates:
            click.echo(f"  [{c.confidence:.0%}] {c.name} ({c.type_str}): {c.rationale}")
        click.echo()

    if inspection.computation_loops:
        click.echo("Computation loops:")
        for l in inspection.computation_loops:
            click.echo(
                f"  for ({l.iterator_var} = {l.start_expr}; ... < {l.end_expr}; ...) "
                f"at line {l.location.line_number}"
                f"{' [MPI]' if l.contains_mpi_calls else ''}"
            )
        click.echo()

    for w in inspection.warnings:
        click.echo(f"Warning: {w}")

    if inspection.guided_prompt:
        click.echo()
        click.echo(inspection.guided_prompt)


# ---------------------------------------------------------------------------
# check — quick check for hook
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("filepath")
def check(filepath: str):
    """Quick check if a file needs checkpointing (used by PostToolUse hook).

    Outputs a warning if the file has critical state but no VeloC protection.
    Outputs nothing if the file is already protected or doesn't need it.
    """
    from guard_agent.analyzer import quick_check

    path = Path(filepath)

    # Only check C/C++ files
    if path.suffix not in {".c", ".cc", ".cpp", ".cxx", ".C", ".h", ".hpp", ".hxx"}:
        return

    if quick_check(filepath):
        click.echo(
            "[guard-agent] This file has critical state that should be checkpointed "
            "but no VeloC protection found.\n"
            "Call inspect_codebase and get_checkpoint_plan to inject resilience support."
        )


# ---------------------------------------------------------------------------
# guide — VeloC reference docs
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("section", required=False)
@click.option("--list-sections", "-l", is_flag=True, help="List available sections.")
def guide(section: str | None, list_sections: bool):
    """Show VeloC API reference documentation."""
    from guard_agent.guide import list_sections as _list_sections, get_section, load_full_guide

    if list_sections:
        for s in _list_sections():
            click.echo(f"  {s}")
        return

    if section:
        content = get_section(section)
        if content:
            click.echo(content)
        else:
            click.echo(f"Section '{section}' not found.")
            click.echo("Available sections:")
            for s in _list_sections():
                click.echo(f"  {s}")
    else:
        click.echo(load_full_guide())


# ---------------------------------------------------------------------------
# serve — start MCP server
# ---------------------------------------------------------------------------

@cli.command()
def serve():
    """Start the MCP server (stdio transport)."""
    from guard_agent.mcp_server import run_server
    run_server()


# ---------------------------------------------------------------------------
# run — full autonomous agent mode
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("project_dir")
@click.option("--prompt", "-p", help="Resilience prompt (or reads from stdin).")
@click.option("--provider", help="LLM provider (openai, argo, generic).")
@click.option("--model", help="LLM model name.")
def run(project_dir: str, prompt: str | None, provider: str | None, model: str | None):
    """Run the full VeloC agent autonomously (requires LLM API key)."""
    import asyncio

    if not prompt:
        if sys.stdin.isatty():
            click.echo("Enter resilience prompt (end with empty line):")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            prompt = "\n".join(lines)
        else:
            prompt = sys.stdin.read()

    if provider:
        os.environ["LLM_PROVIDER"] = provider
    if model:
        os.environ["LLM_MODEL"] = model
    os.environ["GUARD_AGENT_PROJECT_ROOT"] = str(Path(project_dir).resolve())

    try:
        from agents.veloc.agent import run_veloc_agent

        messages = [{"role": "user", "content": prompt}]
        result = asyncio.run(run_veloc_agent(messages))
        click.echo(json.dumps(result, default=str, indent=2))
    except ImportError:
        click.echo("Error: agents.veloc package not found. Is the project installed?", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
