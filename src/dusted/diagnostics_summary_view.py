import importlib.resources
import tkinter as tk
from collections.abc import Callable

import dusted
from dusted.replay_diagnostics import ReplayDiagnostics


class DiagnosticsSummaryView(tk.Frame):
    def __init__(
        self,
        parent,
        diagnostics: ReplayDiagnostics,
        command_prev: Callable[[], None],
        command_next: Callable[[], None],
    ) -> None:
        super().__init__(parent)

        self._diagnostics = diagnostics

        assets_dir = importlib.resources.files(dusted) / "assets"
        self._error_icon = tk.PhotoImage(file=str(assets_dir / "error.png"))
        self._warning_icon = tk.PhotoImage(file=str(assets_dir / "warning.png"))

        self._error_icon_label = tk.Label(self, image=self._error_icon)
        self._warning_icon_label = tk.Label(self, image=self._warning_icon)

        self._error_counts_label = tk.Label(self, text="0")
        self._warning_counts_label = tk.Label(self, text="0")

        self._prev_button = tk.Button(self, text="<", command=command_prev)
        self._next_button = tk.Button(self, text=">", command=command_next)

        self._diagnostics.subscribe(self._refresh)
        self._refresh()

    def _refresh(self):
        """Refresh the contents of this widget."""

        warning_count = len(self._diagnostics.warnings)
        error_count = len(self._diagnostics.errors)

        self._warning_counts_label.configure(text=str(warning_count))
        self._error_counts_label.configure(text=str(error_count))

        if error_count > 0:
            self._error_icon_label.grid(row=0, column=0)
            self._error_counts_label.grid(row=0, column=1)
        else:
            self._error_icon_label.grid_remove()
            self._error_counts_label.grid_remove()

        if warning_count > 0:
            self._warning_icon_label.grid(row=0, column=2)
            self._warning_counts_label.grid(row=0, column=3)
        else:
            self._warning_icon_label.grid_remove()
            self._warning_counts_label.grid_remove()

        if error_count > 0 or warning_count > 0:
            self._prev_button.grid(row=0, column=4, padx=(4, 0))
            self._next_button.grid(row=0, column=5)
        else:
            self._prev_button.grid_remove()
            self._next_button.grid_remove()
