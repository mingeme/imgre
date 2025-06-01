"""
Copy command for imgre CLI.
"""

import sys
from typing import Optional

import click

from imgre.config import load_config, validate_config
from imgre.storage import S3Storage


@click.command("cp")
@click.option(
    "-s", "--source", "source_key", required=True, help="Source S3 object key to copy"
)
@click.option(
    "-t",
    "--target",
    "target_key",
    help="Target S3 object key (destination), defaults to source-copy",
)
@click.option(
    "-f", "--format", "output_format", help="Convert to format (webp, jpeg, png)"
)
@click.option(
    "-q", "--quality", type=int, help="Quality of the converted image (1-100)"
)
@click.option(
    "-w", "--width", type=int, help="Width of the output image (0 for original)"
)
@click.option(
    "-h", "--height", type=int, help="Height of the output image (0 for original)"
)
def copy(
    source_key: str,
    target_key: Optional[str] = None,
    output_format: Optional[str] = None,
    quality: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
):
    """
    Copy objects within S3 with optional format conversion and resizing.
    """
    # Load and validate configuration
    config = load_config()
    error = validate_config(config)
    if error:
        click.echo(f"Configuration error: {error}", err=True)
        sys.exit(1)

    # Create S3 storage handler
    storage = S3Storage(config)

    # Set default format from config if not provided
    if not output_format:
        output_format = config["image"]["format"]

    # Set default quality from config if not provided
    if quality is None:
        quality = config["image"]["quality"]

    try:
        # Perform copy with transformation
        url = storage.copy_with_transform(
            source_key=source_key,
            target_key=target_key,
            format=output_format,
            width=width,
            height=height,
            quality=quality,
            resize_mode=config["image"]["resize_mode"],
        )

        click.echo(f"Copied and transformed object to: {url}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
