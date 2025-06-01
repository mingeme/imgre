"""
List command for imgre CLI.
"""

import sys
from typing import Optional

import click

from imgre.config import load_config, validate_config
from imgre.storage import S3Storage


@click.command("ls")
@click.option("-p", "--prefix", help="Prefix to filter objects by")
@click.option(
    "-d",
    "--delimiter",
    help="Character used to group keys (e.g., '/' for folder-like hierarchy)",
)
@click.option(
    "-m", "--max-keys", type=int, default=1000, help="Maximum number of keys to return"
)
@click.option(
    "-t", "--token", "continuation_token", help="Continuation token for pagination"
)
@click.option("--url", is_flag=True, help="Show URLs for objects")
@click.option(
    "--recursive", is_flag=True, help="List objects recursively (ignores delimiter)"
)
def list_objects(
    prefix: Optional[str] = None,
    delimiter: Optional[str] = "/",
    max_keys: int = 1000,
    continuation_token: Optional[str] = None,
    url: bool = False,
    recursive: bool = False,
):
    """
    List objects in the S3 bucket.
    """
    # Load and validate configuration
    config = load_config()
    error = validate_config(config)
    if error:
        click.echo(f"Configuration error: {error}", err=True)
        sys.exit(1)

    # Create S3 storage handler
    storage = S3Storage(config)

    # If recursive, don't use delimiter
    if recursive:
        delimiter = None

    try:
        # List objects
        result = storage.list_objects(
            prefix=prefix,
            max_keys=max_keys,
            continuation_token=continuation_token,
            delimiter=delimiter,
        )

        # Display prefixes (folders)
        if result["prefixes"] and not recursive:
            click.echo("\nPrefixes (folders):")
            for prefix_path in result["prefixes"]:
                click.echo(f"  📁 {prefix_path}")

        # Display objects
        if result["objects"]:
            click.echo("\nObjects:")
            for obj in result["objects"]:
                last_modified = (
                    obj["last_modified"].strftime("%Y-%m-%d %H:%M:%S")
                    if obj["last_modified"]
                    else "N/A"
                )
                key_display = obj["key"]

                # If using delimiter, show only the last part of the key for better readability
                if delimiter and not recursive and prefix:
                    key_parts = obj["key"][len(prefix) :].split(delimiter)
                    if key_parts and key_parts[-1]:
                        key_display = key_parts[-1]
                    else:
                        key_display = obj["key"]

                # Format the output
                line = f"  📄 {key_display} ({obj['size_formatted']}, {last_modified})"

                # Add URL if requested
                if url:
                    line += f"\n     URL: {obj['url']}"

                click.echo(line)

        # Show pagination info
        if result["is_truncated"]:
            click.echo("\nResults truncated. For more results, use:")
            click.echo(
                f"imgre ls --token {result['next_token']}"
                + (f" --prefix {prefix}" if prefix else "")
                + (" --recursive" if recursive else "")
            )

        # Show summary
        click.echo(
            f"\nTotal: {len(result['objects'])} objects"
            + (f", {len(result['prefixes'])} prefixes" if not recursive else "")
        )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
