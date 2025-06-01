"""
List command for imgre CLI.
"""

import sys
from typing import Optional

from imgre.config import load_config, validate_config
from imgre.storage import S3Storage


class ListCommand:
    """List objects in the S3 bucket."""

    def __call__(
        self,
        prefix: Optional[str] = None,
        delimiter: str = "/",
        max_keys: int = 1000,
        token: Optional[str] = None,
        url: bool = False,
        recursive: bool = False,
    ):
        """
        List objects in the S3 bucket.

        Args:
            prefix: Prefix to filter objects by
            delimiter: Character used to group keys (e.g., '/' for folder-like hierarchy)
            max_keys: Maximum number of keys to return
            token: Continuation token for pagination
            url: Show URLs for objects
            recursive: List objects recursively (ignores delimiter)

        Returns:
            Dictionary containing the list results
        """
        # Load and validate configuration
        config = load_config()
        error = validate_config(config)
        if error:
            print(f"Configuration error: {error}", file=sys.stderr)
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
                continuation_token=token,
                delimiter=delimiter,
            )

            # Display prefixes (folders)
            if result["prefixes"] and not recursive:
                print("\nPrefixes (folders):")
                for prefix_path in result["prefixes"]:
                    print(f"  📁 {prefix_path}")

            # Display objects
            if result["objects"]:
                for obj in result["objects"]:
                    # Format timestamp with local timezone
                    last_modified = "N/A"
                    if obj["last_modified"]:
                        # Get timezone name from the datetime object
                        tz_name = obj["last_modified"].tzname() or "UTC"
                        last_modified = obj["last_modified"].strftime(
                            f"%Y-%m-%d %H:%M:%S ({tz_name})"
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
                    line = (
                        f"  📄 {key_display} ({obj['size_formatted']}, {last_modified})"
                    )

                    # Add URL if requested
                    if url:
                        line += f"\n     URL: {obj['url']}"

                    print(line)

            # Show pagination info
            if result["is_truncated"]:
                print("\nResults truncated. For more results, use:")
                print(
                    f"imgre ls --token {result['next_token']}"
                    + (f" --prefix {prefix}" if prefix else "")
                    + (" --recursive" if recursive else "")
                )

            print(f"\nTotal: {len(result['objects'])} objects")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
