"""
Remove command for imgre CLI.
"""

import sys

from imgre.config import load_config, validate_config
from imgre.storage import S3Storage


class RemoveCommand:
    """Delete an object from S3 by its key."""

    def __call__(self, object_key: str, force: bool = False):
        """
        Delete an object from S3 by its key.

        Args:
            object_key: The full path/key of the object to delete
            force: Skip confirmation prompt if True
        """
        # Load and validate configuration
        config = load_config()
        error = validate_config(config)
        if error:
            print(f"Configuration error: {error}", file=sys.stderr)
            sys.exit(1)

        # Create S3 storage handler
        storage = S3Storage(config)

        try:
            # Confirm deletion unless force flag is used
            if not force:
                confirm = (
                    input(
                        f"Are you sure you want to delete '{object_key}'? (y/N): "
                    ).lower()
                    == "y"
                )
                if not confirm:
                    print("Deletion cancelled.")
                    return

            # Delete the object
            storage.delete_object(object_key)
            print(f"Deleted object: {object_key}")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
