"""
Remove command for imgre CLI.
"""

import sys

from imgre.config import load_config, validate_config
from imgre.storage import S3Storage


class RemoveCommand:
    """Delete one or more objects from S3 by their keys."""

    def __call__(self, *object_keys: str, force: bool = False):
        """
        Delete one or more objects from S3 by their keys.

        Args:
            *object_keys: One or more object keys to delete
            force: Skip confirmation prompt if True
        """
        try:
            # Load and validate configuration
            config = load_config()
            error = validate_config(config)
            if error:
                print(f"Configuration error: {error}", file=sys.stderr)
                sys.exit(1)

            # Create S3 storage handler
            storage = S3Storage(config)

            # Handle multiple keys
            keys_to_delete = list(object_keys)

            if len(keys_to_delete) == 0:
                print("Error: No object keys provided", file=sys.stderr)
                sys.exit(1)

            # Confirm deletion unless force flag is used
            if not force:
                if len(keys_to_delete) == 1:
                    prompt = f"Are you sure you want to delete '{keys_to_delete[0]}'? (y/N): "
                else:
                    prompt = f"Are you sure you want to delete {len(keys_to_delete)} objects? (y/N): "
                    print("Objects to delete:")
                    for key in keys_to_delete:
                        print(f"  - {key}")

                confirm = input(prompt).lower() == "y"
                if not confirm:
                    print("Deletion cancelled.")
                    return

            # Delete the objects
            deleted_count = 0
            for key in keys_to_delete:
                try:
                    storage.delete_object(key)
                    print(f"Deleted object: {key}")
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting '{key}': {e}", file=sys.stderr)

            # Show summary
            if len(keys_to_delete) > 1:
                print(f"\nDeleted {deleted_count} of {len(keys_to_delete)} objects.")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
