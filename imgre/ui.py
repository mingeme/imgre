"""
Textual UI for S3 storage management.
"""

from typing import List

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Footer, Button, Static, Input, LoadingIndicator
from textual.screen import Screen, ModalScreen
from textual.binding import Binding

from imgre.config import load_config, validate_config
from imgre.storage import S3Storage


class FilterDialog(ModalScreen):
    """Modal dialog for filtering objects."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "apply_filter", "Apply"),
    ]

    def __init__(self, current_filter: str = ""):
        """Initialize with current filter string."""
        super().__init__()
        self.current_filter = current_filter

    def compose(self) -> ComposeResult:
        """Compose the filter dialog."""
        with Container(id="filter-dialog"):
            yield Static("Filter Objects", id="filter-title")
            yield Input(
                value=self.current_filter,
                placeholder="Enter filter text",
                id="filter-input",
            )
            with Horizontal(id="filter-buttons"):
                yield Button("Cancel", variant="primary", id="cancel-btn")
                yield Button("Apply", variant="success", id="apply-btn")

    def on_mount(self) -> None:
        """Focus the input when mounted."""
        self.query_one("#filter-input").focus()

    def action_cancel(self) -> None:
        """Cancel filtering."""
        self.app.pop_screen()

    def action_apply_filter(self) -> None:
        """Apply the filter."""
        filter_text = self.query_one("#filter-input").value
        self.app.pop_screen()
        self.app.apply_filter(filter_text)

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """Handle cancel button press."""
        self.action_cancel()

    @on(Button.Pressed, "#apply-btn")
    def on_apply(self) -> None:
        """Handle apply button press."""
        self.action_apply_filter()


class ConfirmDeleteScreen(Screen):
    """Screen for confirming object deletion."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]

    def __init__(self, object_keys: List[str]):
        """Initialize with object keys to delete."""
        super().__init__()
        self.object_keys = object_keys

    def compose(self) -> ComposeResult:
        """Compose the confirmation screen."""
        with Container(id="confirm-dialog"):
            yield Static(
                f"Delete {len(self.object_keys)} object(s)?", id="confirm-title"
            )
            for key in self.object_keys[:5]:  # Show first 5 objects
                yield Static(f"• {key}")

            if len(self.object_keys) > 5:
                yield Static(f"...and {len(self.object_keys) - 5} more")

            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel", variant="primary", id="cancel-btn")
                yield Button("Delete", variant="error", id="confirm-btn")

    def action_cancel(self) -> None:
        """Cancel deletion."""
        self.app.pop_screen()

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """Handle cancel button press."""
        self.action_cancel()

    def action_confirm(self) -> None:
        """Confirm deletion."""
        self.app.pop_screen()
        self.app.delete_objects(self.object_keys)

    @on(Button.Pressed, "#confirm-btn")
    def on_confirm(self) -> None:
        """Handle confirm button press."""
        self.action_confirm()


class S3BrowserApp(App):
    """Textual app for browsing S3 objects."""

    CSS = """
    #header-container {
        height: auto;
        padding: 1;
    }

    #controls {
        height: auto;
        margin: 1 0;
    }

    #prefix-input {
        width: 60%;
    }

    #loading {
        align: center middle;
    }

    #confirm-dialog {
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        width: 60;
        height: auto;
        align: center middle;
    }

    #confirm-title {
        text-align: center;
        margin-bottom: 1;
        text-style: bold;
    }

    #confirm-buttons {
        margin-top: 1;
        align-horizontal: center;
    }

    #filter-dialog {
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        width: 60;
        height: auto;
        align: center middle;
    }

    #filter-title {
        text-align: center;
        margin-bottom: 1;
        text-style: bold;
    }

    #filter-input {
        margin: 1 0;
        width: 100%;
    }

    #filter-buttons {
        margin-top: 1;
        align-horizontal: center;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "delete_selected", "Delete Selected"),
        Binding("/", "show_filter", "Filter"),
        Binding("escape", "clear_selection", "Clear Selection"),
    ]

    def __init__(self):
        """Initialize the app."""
        super().__init__()
        self.config = None
        self.storage = None
        self.current_prefix = ""
        self.continuation_token = None
        self.recursive = False
        self.selected_rows = set()
        self.filter_text = ""

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield DataTable(id="objects-table")
        yield LoadingIndicator(id="loading")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the app when mounted."""
        # Set up the table
        table = self.query_one(DataTable)
        table.add_columns("Select", "Type", "Key", "Size", "Last Modified", "URL")

        # Load config and initialize storage
        self.load_config()

        # Initial data load
        self.load_data()

    def load_config(self) -> None:
        """Load configuration and initialize S3 storage."""
        try:
            # Load config without parameters
            self.config = load_config()
            error = validate_config(self.config)
            if error:
                self.exit(message=f"Configuration error: {error}")
                return

            self.storage = S3Storage(self.config)
            self.title = f"S3 Browser - {self.config['s3']['bucket']}"
        except Exception as e:
            self.exit(message=f"Error loading configuration: {e}")

    def load_data(self) -> None:
        """Load S3 objects data."""
        if not self.storage:
            return

        loading = self.query_one(LoadingIndicator)
        loading.display = True

        table = self.query_one(DataTable)
        table.clear()

        # Use the stored values for prefix and recursive mode
        # since we no longer have UI elements for them

        # Reset selection
        self.selected_rows = set()

        try:
            # List objects
            delimiter = None if self.recursive else "/"
            result = self.storage.list_objects(
                prefix=self.current_prefix or None,
                continuation_token=self.continuation_token,
                delimiter=delimiter,
            )

            # Add prefixes (folders) if not recursive
            if result["prefixes"] and not self.recursive:
                for prefix in result["prefixes"]:
                    table.add_row("□", "📁", prefix, "", "", "", key=f"prefix:{prefix}")

            # Add objects
            filtered_objects = []
            for obj in result["objects"]:
                # Apply filter if set
                if (
                    self.filter_text
                    and self.filter_text.lower() not in obj["key"].lower()
                ):
                    continue

                filtered_objects.append(obj)
                key_display = obj["key"]

                # If using delimiter, show only the last part of the key for better readability
                if delimiter and not self.recursive and self.current_prefix:
                    key_parts = obj["key"][len(self.current_prefix) :].split(delimiter)
                    if key_parts:
                        key_display = key_parts[-1]
                    else:
                        key_display = obj["key"]

                # Format last modified
                last_modified = (
                    obj["last_modified"].strftime("%Y-%m-%d %H:%M:%S")
                    if obj["last_modified"]
                    else "N/A"
                )

                table.add_row(
                    "□",
                    "📄",
                    key_display,
                    obj["size_formatted"],
                    last_modified,
                    obj["url"],
                    key=f"object:{obj['key']}",
                )

            # Update continuation token
            self.continuation_token = result["next_token"]

            # Update footer with stats
            stats_text = (
                f"Objects: {len(filtered_objects)}/{len(result['objects'])}"
                + (
                    f", Prefixes: {len(result['prefixes'])}"
                    if not self.recursive
                    else ""
                )
            )

            # Show pagination info in footer
            if result["is_truncated"]:
                stats_text += " (More results available, press 'n' for next page)"

            # Show filter status in footer
            if self.filter_text:
                self.sub_title = f"Filter: '{self.filter_text}' | {stats_text}"
            else:
                self.sub_title = stats_text

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

        finally:
            loading.display = False

    # Removed button and input handlers since we removed those UI elements

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        table = self.query_one(DataTable)
        row_key = event.row_key.value

        # Toggle selection
        if row_key in self.selected_rows:
            self.selected_rows.remove(row_key)
            table.update_cell(row_key, 0, "□")
        else:
            self.selected_rows.add(row_key)
            table.update_cell(row_key, 0, "☑")

    @on(DataTable.CellSelected)
    def on_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection."""
        # If it's a prefix cell, navigate to that prefix
        row_key = event.cell_key.row_key
        if str(row_key).startswith("prefix:"):
            prefix = str(row_key)[7:]  # Remove "prefix:" prefix
            # Update the current prefix directly
            self.current_prefix = prefix
            self.continuation_token = None
            self.load_data()

    @on(Button.Pressed, "#delete-btn")
    def on_delete_button(self) -> None:
        """Handle Delete button press."""
        self.action_delete_selected()

    def action_delete_selected(self) -> None:
        """Delete selected objects."""
        # Get selected object keys
        object_keys = []
        for row_key in self.selected_rows:
            if str(row_key).startswith("object:"):
                object_key = str(row_key)[7:]  # Remove "object:" prefix
                object_keys.append(object_key)

        if not object_keys:
            self.notify("No objects selected", severity="warning")
            return

        # Show confirmation screen
        self.push_screen(ConfirmDeleteScreen(object_keys))

    def delete_objects(self, object_keys: List[str]) -> None:
        """Delete objects from S3."""
        loading = self.query_one(LoadingIndicator)
        loading.display = True

        try:
            deleted_count = 0
            for key in object_keys:
                self.storage.delete_object(key)
                deleted_count += 1

            self.notify(f"Deleted {deleted_count} object(s)", severity="information")

            # Refresh the data
            self.continuation_token = None
            self.load_data()

        except Exception as e:
            self.notify(f"Error deleting objects: {e}", severity="error")

        finally:
            loading.display = False

    def action_refresh(self) -> None:
        """Refresh the data."""
        self.continuation_token = None
        self.load_data()

    def action_show_filter(self) -> None:
        """Show the filter dialog."""
        self.push_screen(FilterDialog(self.filter_text))

    def apply_filter(self, filter_text: str) -> None:
        """Apply the filter to the objects list."""
        self.filter_text = filter_text

        # Update status display
        if filter_text:
            self.sub_title = f"Filter: {filter_text}"
        else:
            self.sub_title = ""

        # Refresh the data with the filter
        self.load_data()

    def action_clear_selection(self) -> None:
        """Clear all selections."""
        table = self.query_one(DataTable)
        for row_key in self.selected_rows:
            table.update_cell(row_key, 0, "□")
        self.selected_rows = set()


def run_ui() -> None:
    """Run the S3 browser UI app."""
    app = S3BrowserApp()
    app.run()
