"""
Copy command for imgre CLI.
"""

import sys
from pathlib import Path
from typing import Optional

import click
import pyvips

from imgre.config import load_config, validate_config
from imgre.image import ImageProcessor
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

    if not output_format:
        click.echo("Error: Output format not specified", err=True)
        sys.exit(1)

    # Set default quality from config if not provided
    if quality is None:
        quality = config["image"]["quality"]

    try:
        # Set default target key if not provided
        if not target_key:
            source_path = Path(source_key)
            target_key = f"{source_path.stem}.{output_format.lower()}"

        if target_key == source_key:
            click.echo("Error: Target key is the same as source key", err=True)
            sys.exit(1)

        # Download source object
        source_data = storage.download_object(source_key)

        # Use pyvips to load from memory buffer
        img = pyvips.Image.new_from_buffer(source_data, "")
        click.echo(f"Original image: {img.width}x{img.height}, {len(source_data)} bytes")

        # Process the image
        processed_data = ImageProcessor.process_image(
            img=img,
            width=width,
            height=height,
            format=output_format,
            quality=quality,
            resize_mode=config["image"]["resize_mode"],
        )
        click.echo(f"Processed image: {len(processed_data)} bytes ({len(processed_data) / len(source_data) * 100:.2f}% of original)")

        # Update target key extension if format is different
        if output_format:
            target_path = Path(target_key)
            if target_path.suffix.lower() != f".{output_format.lower()}":
                target_key = f"{target_path.stem}.{output_format.lower()}"

        # Upload processed image
        content_type = ImageProcessor.get_content_type(output_format)
        url = storage.upload_bytes(processed_data, target_key, content_type=content_type)

        click.echo(f"Copied and transformed object to: {url}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
