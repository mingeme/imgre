"""
Upload command for imgre CLI.
"""

import sys
from pathlib import Path
from typing import Optional

from imgre.config import load_config, validate_config
from imgre.image import ImageProcessor
from imgre.storage import S3Storage


class UploadCommand:
    """Upload images to S3 with optional compression and format conversion."""

    def __call__(
        self,
        input_path: str,
        key: Optional[str] = None,
        compress: bool = False,
        quality: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        format: Optional[str] = None,
    ):
        """
        Upload images to S3 with optional compression and format conversion.

        Args:
            input_path: Path to the input image file
            key: S3 object key (path in bucket), defaults to filename
            compress: Compress image before uploading
            quality: Quality of the compressed image (1-100)
            width: Width of the output image (0 for original)
            height: Height of the output image (0 for original)
            format: Convert to format (webp, jpeg, png)
        """
        # Load and validate configuration
        config = load_config()
        error = validate_config(config)
        if error:
            print(f"Configuration error: {error}", file=sys.stderr)
            sys.exit(1)

        # Create S3 storage handler
        storage = S3Storage(config)

        # Validate input file
        input_path_obj = Path(input_path)
        if not input_path_obj.exists():
            print(f"Input file not found: {input_path_obj}", file=sys.stderr)
            sys.exit(1)

        # Set default object key if not provided
        object_key = key if key else input_path_obj.name

        # Set default quality from config if not provided
        if quality is None:
            quality = config["image"]["quality"]

        # Set default format from config if not provided
        output_format = format if format else config["image"]["format"]

        try:
            # Print origin image info
            img = ImageProcessor.open_image(input_path_obj)
            print(f"Original image: {img.width}x{img.height}, {input_path_obj.stat().st_size} bytes, format: {input_path_obj.suffix}")  # fmt: skip
            # If compression or format conversion is requested
            if compress:
                processed_data = ImageProcessor.process_image(
                    img=img,
                    width=width,
                    height=height,
                    format=output_format,
                    quality=quality,
                    resize_mode=config["image"]["resize_mode"],
                )
                print(f"Compressed image: {len(processed_data)} bytes ({len(processed_data) / input_path_obj.stat().st_size * 100:.2f}% of original)")  # fmt: skip

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

                print(f"Uploaded image to: {url}")
            else:
                # Direct upload without processing
                url = storage.upload_file(input_path_obj, object_key)
                print(f"Uploaded image to: {url}")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
