"""
Textual UI for S3 storage management.
"""

from typing import List, Optional

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import (
    DataTable,
    Footer,
    Button,
    Static,
    Input,
    LoadingIndicator,
    Tree,
)
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
    /* Main layout */
    #app-grid {
        layout: grid;
        grid-size: 3 3;  /* 3 columns, 3 rows */
        grid-rows: 1fr 12fr 1fr;  /* Top info bar, main content, status bar */
        grid-columns: 1fr 3fr 1fr;  /* Left panel, main content, right panel */
        height: 100%;
        width: 100%;
    }

    /* Top info bar */
    #info-bar {
        column-span: 3;  /* Span all columns */
        background: $surface;
        border-bottom: solid $primary;
        height: 100%;
        padding: 0 1;
    }

    /* Left panel - folders/buckets */
    #left-panel {
        background: $surface-darken-1;
        border-right: solid $primary-background;
        height: 100%;
        overflow: auto;
    }

    /* Main content - objects table */
    #main-content {
        height: 100%;
        overflow: auto;
    }

    /* Right panel - object details */
    #right-panel {
        background: $surface-darken-1;
        border-left: solid $primary-background;
        height: 100%;
        overflow: auto;
        padding: 1;
    }

    /* Status bar */
    #status-bar {
        column-span: 3;  /* Span all columns */
        background: $surface;
        border-top: solid $primary;
        height: 100%;
        padding: 0 1;
    }

    /* Object table styling */
    #objects-table {
        width: 100%;
        height: 100%;
    }

    /* Loading indicator */
    #loading {
        align: center middle;
    }

    /* Dialog styling */
    #confirm-dialog, #filter-dialog {
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        width: 60;
        height: auto;
        align: center middle;
    }

    #confirm-title, #filter-title {
        text-align: center;
        margin-bottom: 1;
        text-style: bold;
    }

    #filter-input {
        margin: 1 0;
        width: 100%;
    }

    #confirm-buttons, #filter-buttons {
        margin-top: 1;
        align-horizontal: center;
    }

    Button {
        margin: 0 1;
    }

    /* Tree styling */
    #bucket-tree {
        padding: 1;
    }

    /* Object details styling */
    #object-details {
        padding: 1;
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
        with Container(id="app-grid"):
            # Top info bar
            yield Static("S3 Browser", id="info-bar")

            # Left panel - folder/bucket tree
            with VerticalScroll(id="left-panel"):
                yield Tree("Buckets", id="bucket-tree")

            # Main content - objects table
            with Container(id="main-content"):
                yield DataTable(id="objects-table")
                yield LoadingIndicator(id="loading")

            # Right panel - object details
            with VerticalScroll(id="right-panel"):
                yield Static("Object Details", id="object-details")

            # Bottom status bar
            yield Static("", id="status-bar")

        # Footer for keyboard shortcuts
        yield Footer()

    def on_mount(self) -> None:
        """Set up the app when mounted."""
        # Set up the table
        table = self.query_one(DataTable)
        table.add_columns("Key", "Size", "Last Modified", "URL")
        table.cursor_type = "row"

        # Set up the status bar
        status_bar = self.query_one("#status-bar")
        status_bar.update("Ready")

        # Load config and initialize storage
        self.load_config()

        # Set up the bucket tree
        self._setup_bucket_tree()

        # Initial data load
        self.load_data()

    def _setup_bucket_tree(self) -> None:
        """Set up the bucket tree in the left panel."""
        if not self.storage:
            return

        bucket_tree = self.query_one("#bucket-tree", Tree)
        bucket_node = bucket_tree.root.add(self.config["s3"]["bucket"], expand=True)

        # Add a node for the current prefix if it's not empty
        if self.current_prefix:
            prefix_parts = self.current_prefix.strip("/").split("/")
            current_node = bucket_node

            # Build the prefix tree
            current_path = ""
            for part in prefix_parts:
                if not part:
                    continue

                current_path += part + "/"
                current_node = current_node.add(part, data={"prefix": current_path})

        # Add common prefixes as folders
        try:
            result = self.storage.list_objects(prefix=None, delimiter="/")

            # Add prefixes as folders
            for prefix in result.get("prefixes", []):
                if prefix != self.current_prefix:
                    prefix_name = prefix.rstrip("/")
                    if "/" in prefix_name:
                        prefix_name = prefix_name.split("/")[-1]
                    bucket_node.add(prefix_name, data={"prefix": prefix})

        except Exception as e:
            self.notify(f"Error loading prefixes: {e}", severity="error")

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

        # Update info bar with current location
        info_bar = self.query_one("#info-bar", Static)
        bucket_name = self.config["s3"]["bucket"]
        info_bar.update(f"S3 Browser - {bucket_name}/{self.current_prefix}")

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
                    table.add_row(f"📁 {prefix}", "", "", "", key=f"prefix:{prefix}")

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
                    f"📄 {key_display}",
                    obj["size_formatted"],
                    last_modified,
                    obj["url"],
                    key=f"object:{obj['key']}",
                )

            # Update continuation token
            self.continuation_token = result["next_token"]

            # Update status bar with stats
            stats_text = (
                f"Objects: {len(filtered_objects)}/{len(result['objects'])}"
                + (
                    f", Prefixes: {len(result['prefixes'])}"
                    if not self.recursive
                    else ""
                )
            )

            # Show pagination info in status bar
            if result["is_truncated"]:
                stats_text += " (More results available, press 'n' for next page)"

            # Show filter status in status bar
            status_bar = self.query_one("#status-bar", Static)
            if self.filter_text:
                status_bar.update(f"Filter: '{self.filter_text}' | {stats_text}")
            else:
                status_bar.update(stats_text)

        except Exception as e:
            self.notify(f"Error loading data: {e}", severity="error")
        finally:
            loading.display = False

    def _update_object_details(self, obj_key: Optional[str] = None) -> None:
        """Update the object details panel with information about the selected object."""
        details_panel = self.query_one("#object-details", Static)

        if not obj_key:
            details_panel.update("No object selected")
            return

        try:
            # Get object details from S3
            obj_info = self.storage.get_object_info(obj_key)
            if not obj_info:
                details_panel.update(f"Object not found: {obj_key}")
                return

            # Format the details
            details = f"""# Object Details

            **Key:** {obj_info["key"]}
            **Size:** {obj_info["size_formatted"]}
            **Last Modified:** {obj_info["last_modified"].strftime("%Y-%m-%d %H:%M:%S") if obj_info["last_modified"] else "N/A"}
            **ETag:** {obj_info.get("etag", "N/A")}
            **Content Type:** {obj_info.get("content_type", "N/A")}

            [View in Browser]({obj_info["url"]})"""

            details_panel.update(details)

        except Exception as e:
            details_panel.update(f"Error loading object details: {e}")
            self.notify(f"Error: {e}", severity="error")

    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        row_key = event.row_key.value

        # Toggle selection in our tracking set
        if row_key in self.selected_rows:
            self.selected_rows.remove(row_key)
        else:
            self.selected_rows.add(row_key)

        # Update object details panel if it's an object (not a prefix)
        if row_key.startswith("object:"):
            obj_key = row_key.split(":", 1)[1]
            self._update_object_details(obj_key)
        elif row_key.startswith("prefix:"):
            # If it's a prefix, show folder info
            prefix = row_key.split(":", 1)[1]
            details_panel = self.query_one("#object-details", Static)
            details_panel.update(
                f"# Folder: {prefix}\n\nSelect an object to view its details."
            )

    @on(DataTable.CellSelected)
    def on_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection for navigation."""
        # If it's a prefix row, navigate to that prefix
        row_key = event.cell_key.row_key.value
        if str(row_key).startswith("prefix:"):
            prefix = row_key.split(":", 1)[1]
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

        # Update status display in the status bar
        status_bar = self.query_one("#status-bar", Static)
        if filter_text:
            status_bar.update(f"Filter: '{filter_text}'")
        else:
            status_bar.update("")

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
