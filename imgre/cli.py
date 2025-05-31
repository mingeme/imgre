"""
Command-line interface for imgre.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from imgre.config import load_config, validate_config
from imgre.image import ImageProcessor
from imgre.storage import S3Storage
from imgre.ui import run_ui


@click.group()
@click.version_option()
def cli():
    """
    imgre - Image Optimization and S3 Management Tool
    """
    pass


@cli.command("up")
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


@cli.command("cp")
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


@cli.command("ls")
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


@cli.command("rm")
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


@cli.command("ui")
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
