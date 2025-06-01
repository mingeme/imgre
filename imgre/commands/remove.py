"""
Remove command for imgre CLI.
"""

import sys

import click

from imgre.config import load_config, validate_config
from imgre.storage import S3Storage


@click.command("rm")
@click.argument("object_key", required=True)
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
def remove(object_key: str, force: bool = False):
    """
    Delete an object from S3 by its key.

    OBJECT_KEY is the full path/key of the object to delete.
    """
    # Load and validate configuration
    config = load_config()
    error = validate_config(config)
    if error:
        click.echo(f"Configuration error: {error}", err=True)
        sys.exit(1)

    # Create S3 storage handler
    storage = S3Storage(config)

    try:
        # Confirm deletion unless force flag is used
        if not force:
            confirm = click.confirm(f"Are you sure you want to delete '{object_key}'?")
            if not confirm:
                click.echo("Deletion cancelled.")
                return

        # Delete the object
        storage.delete_object(object_key)
        click.echo(f"Deleted object: {object_key}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
