"""
Command-line interface for imgre.
"""

import sys
from typing import Optional

import fire


class ImgreCLI:
    """
    imgre - Image Optimization and S3 Management Tool

    A powerful command-line tool for image optimization, format conversion, and S3 object management.
    """

    def __init__(self):
        pass

    def up(
        self,
        input_path: str,
        key: Optional[str] = None,
        compress: bool = False,
        quality: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        format: Optional[str] = None,
    ):
        """Upload images to S3 with optional compression and format conversion.

        Args:
            input_path: Path to the input image file
            key: S3 object key (path in bucket), defaults to filename
            compress: Compress image before uploading
            quality: Quality of the compressed image (1-100)
            width: Width of the output image (0 for original)
            height: Height of the output image (0 for original)
            format: Convert to format (webp, jpeg, png)
        """
        from imgre.commands.upload import UploadCommand

        return UploadCommand()(
            input_path, key, compress, quality, width, height, format
        )

    def cp(
        self,
        source: str,
        target: Optional[str] = None,
        format: Optional[str] = None,
        quality: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        """Copy objects within S3 with optional format conversion and resizing.

        Args:
            source: Source S3 object key to copy
            target: Target S3 object key (destination), defaults to source-copy
            format: Convert to format (webp, jpeg, png)
            quality: Quality of the converted image (1-100)
            width: Width of the output image (0 for original)
            height: Height of the output image (0 for original)
        """
        from imgre.commands.copy import CopyCommand

        return CopyCommand()(source, target, format, quality, width, height)

    def ls(
        self,
        prefix: Optional[str] = None,
        delimiter: str = "/",
        max_keys: int = 1000,
        token: Optional[str] = None,
        url: bool = False,
        recursive: bool = True,
    ):
        """List objects in the S3 bucket.

        Args:
            prefix: Prefix to filter objects by
            delimiter: Character used to group keys (e.g., '/' for folder-like hierarchy)
            max_keys: Maximum number of keys to return
            token: Continuation token for pagination
            url: Show URLs for objects
            recursive: List objects recursively (ignores delimiter)
        """
        from imgre.commands.list import ListCommand

        return ListCommand()(prefix, delimiter, max_keys, token, url, recursive)

    def rm(self, *object_keys: str, force: bool = False):
        """Delete one or more objects from S3 by their keys.

        Args:
            *object_keys: One or more object keys to delete
            force: Skip confirmation prompt if True
        """
        from imgre.commands.remove import RemoveCommand

        if not object_keys:
            print("Error: No object keys provided", file=sys.stderr)
            sys.exit(1)

        return RemoveCommand()(*object_keys, force=force)

    def ui(self):
        """Launch the S3 browser UI.

        Interactive TUI for browsing and managing S3 objects.
        """
        from imgre.commands.ui import UICommand

        return UICommand()()

    @property
    def version(self):
        """Print the version and exit."""
        from importlib.metadata import version

        try:
            return version("imgre")
        except ImportError:
            return "0.1.0"


def main():
    """
    Main entry point for the CLI.
    """
    try:
        fire.Fire(ImgreCLI)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
