"""
UI command for imgre CLI.
"""

import sys

import click

from imgre.ui import run_ui


@click.command("ui")
def ui():
    """
    Launch the S3 browser UI.

    Interactive TUI for browsing and managing S3 objects.
    """
    try:
        run_ui()
    except Exception as e:
        click.echo(f"Error launching UI: {e}", err=True)
        sys.exit(1)
