"""
Copy command for imgre CLI.
"""

import sys
from pathlib import Path
from typing import Optional

import pyvips

from imgre.config import load_config, validate_config
from imgre.image import ImageProcessor
from imgre.storage import S3Storage


class CopyCommand:
    """Copy objects within S3 with optional format conversion and resizing."""

    def __call__(
        self,
        source: str,
        target: Optional[str] = None,
        format: Optional[str] = None,
        quality: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        """
        Copy objects within S3 with optional format conversion and resizing.

        Args:
            source: Source S3 object key to copy
            target: Target S3 object key (destination), defaults to source-copy
            format: Convert to format (webp, jpeg, png)
            quality: Quality of the converted image (1-100)
            width: Width of the output image (0 for original)
            height: Height of the output image (0 for original)
        """
        # Load and validate configuration
        config = load_config()
        error = validate_config(config)
        if error:
            print(f"Configuration error: {error}", file=sys.stderr)
            sys.exit(1)

        # Create S3 storage handler
        storage = S3Storage(config)

        # Set default format from config if not provided
        output_format = format if format else config["image"]["format"]

        if not output_format:
            print("Error: Output format not specified", file=sys.stderr)
            sys.exit(1)

        # Set default quality from config if not provided
        if quality is None:
            quality = config["image"]["quality"]

        try:
            # Set default target key if not provided
            source_key = source
            target_key = target
            if not target_key:
                source_path = Path(source_key)
                target_key = f"{source_path.stem}.{output_format.lower()}"

            if target_key == source_key:
                print("Error: Target key is the same as source key", file=sys.stderr)
                sys.exit(1)

            # Download source object
            source_data = storage.download_object(source_key)

            # Use pyvips to load from memory buffer
            img = pyvips.Image.new_from_buffer(source_data, "")
            print(f"Original image: {img.width}x{img.height}, {len(source_data)} bytes")

            # Process the image
            processed_data = ImageProcessor.process_image(
                img=img,
                width=width,
                height=height,
                format=output_format,
                quality=quality,
                resize_mode=config["image"]["resize_mode"],
            )
            print(
                f"Processed image: {len(processed_data)} bytes ({len(processed_data) / len(source_data) * 100:.2f}% of original)"
            )

            # Update target key extension if format is different
            if output_format:
                target_path = Path(target_key)
                if target_path.suffix.lower() != f".{output_format.lower()}":
                    target_key = f"{target_path.stem}.{output_format.lower()}"

            # Upload processed image
            content_type = ImageProcessor.get_content_type(output_format)
            url = storage.upload_bytes(processed_data, target_key, content_type=content_type)

            print(f"Copied and transformed object to: {url}")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
