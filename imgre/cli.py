"""
Command-line interface for imgre.
"""

import sys

import click

# Import commands from separate modules
from imgre.commands.copy import copy
from imgre.commands.list import list_objects
from imgre.commands.remove import remove
from imgre.commands.ui import ui
from imgre.commands.upload import upload


@click.group()
@click.version_option()
def cli():
    """
    imgre - Image Optimization and S3 Management Tool
    """
    pass


# Register commands
cli.add_command(upload)
cli.add_command(copy)
cli.add_command(list_objects)
cli.add_command(remove)
cli.add_command(ui)


def main():
    """
    Main entry point for the CLI.
    """
    try:
        cli()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
