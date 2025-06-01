"""
Upload command for imgre CLI.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from imgre.config import load_config, validate_config
from imgre.image import ImageProcessor
from imgre.storage import S3Storage


@click.command("up")
@click.option(
    "-i", "--input", "input_path", required=True, help="Path to the input image file"
)
@click.option(
    "-k",
    "--key",
    "object_key",
    help="S3 object key (path in bucket), defaults to filename",
)
@click.option("-c", "--compress", is_flag=True, help="Compress image before uploading")
@click.option(
    "-q", "--quality", type=int, help="Quality of the compressed image (1-100)"
)
@click.option(
    "-w", "--width", type=int, help="Width of the output image (0 for original)"
)
@click.option(
    "-h", "--height", type=int, help="Height of the output image (0 for original)"
)
@click.option(
    "-f", "--format", "output_format", help="Convert to format (webp, jpeg, png)"
)
def upload(
    input_path: str,
    object_key: Optional[str] = None,
    compress: bool = False,
    quality: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    output_format: Optional[str] = None,
):
    """
    Upload images to S3 with optional compression and format conversion.
    """
    # Load and validate configuration
    config = load_config()
    error = validate_config(config)
    if error:
        click.echo(f"Configuration error: {error}", err=True)
        sys.exit(1)

    # Create S3 storage handler
    storage = S3Storage(config)

    # Validate input file
    input_path = Path(input_path)
    if not input_path.exists():
        click.echo(f"Input file not found: {input_path}", err=True)
        sys.exit(1)

    # Set default object key if not provided
    if not object_key:
        object_key = input_path.name

    # Set default quality from config if not provided
    if quality is None:
        quality = config["image"]["quality"]

    # Set default format from config if not provided
    if not output_format:
        output_format = config["image"]["format"]

    try:
        # If compression or format conversion is requested
        if compress or width or height or output_format:
            click.echo(f"Processing image: {input_path}")

            # Open and process the image
            img = ImageProcessor.open_image(input_path)
            processed_data = ImageProcessor.process_image(
                img=img,
                width=width,
                height=height,
                format=output_format,
                quality=quality,
                resize_mode=config["image"]["resize_mode"],
            )

            # Update object key extension if format is different
            if output_format:
                object_path = Path(object_key)
                if object_path.suffix.lower() != f".{output_format.lower()}":
                    object_key = f"{object_path.stem}.{output_format.lower()}"

            # Upload processed image
            content_type = ImageProcessor.get_content_type(output_format)
            url = storage.upload_bytes(
                processed_data, object_key, content_type=content_type
            )

            click.echo(f"Processed and uploaded image to: {url}")
        else:
            # Direct upload without processing
            url = storage.upload_file(input_path, object_key)
            click.echo(f"Uploaded image to: {url}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
