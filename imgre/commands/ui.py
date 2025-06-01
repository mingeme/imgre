"""
UI command for imgre CLI.
"""

import sys

from imgre.ui import run_ui


class UICommand:
    """Launch the S3 browser UI."""

    def __call__(self):
        """
        Launch the S3 browser UI.

        Interactive TUI for browsing and managing S3 objects.
        """
        try:
            run_ui()
        except Exception as e:
            print(f"Error launching UI: {e}", file=sys.stderr)
            sys.exit(1)
