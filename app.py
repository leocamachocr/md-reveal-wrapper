"""
app.py — Tkinter GUI for md-reveal-wrapper.
Wraps the SOLID-refactored pipeline in src/ without modifying it.
"""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from src.application.markdown_parser import MarkdownParser
from src.application.presentation_generator import PresentationGenerator
from src.application.slide_processor_pipeline import DefaultSlideProcessorPipeline
from src.domain.config import PresentationConfig
from src.infrastructure.config_loader import ConfigLoader
from src.infrastructure.file_manager import FileManager
from src.infrastructure.resource_resolver import resolve_resource
from src.infrastructure.template_renderer import TemplateRenderer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRANSITIONS = ["none", "fade", "slide", "convex", "concave", "zoom"]
_BOOL_FIELDS = frozenset({
    "enable_progress", "enable_controls", "enable_history",
    "align_center", "enable_fragments", "show_header_trail",
})


def _build_generator() -> PresentationGenerator:
    """Compose the object graph — mirrors main.py's build_generator()."""
    file_manager = FileManager()
    return PresentationGenerator(
        parser=MarkdownParser(),
        pipeline=DefaultSlideProcessorPipeline(),
        renderer=TemplateRenderer(file_manager),
        file_manager=file_manager,
        open_browser=True,
    )


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("md-reveal-wrapper")
        self.minsize(860, 580)

        # Load defaults from config.properties
        try:
            self._defaults = ConfigLoader().load(resolve_resource("config.properties"))
        except Exception:
            self._defaults = PresentationConfig()

        # Discover CSS themes from templates/themes/
        themes_dir = Path(resolve_resource("templates/themes"))
        self._css_themes = ["(none)"] + sorted(p.name for p in themes_dir.glob("*.css"))

        # Stores all tk.Variable instances keyed by PresentationConfig field name
        self._vars: dict = {}
        self._working_dir = tk.StringVar()

        self._build_ui()
        self.after(150, self._ask_working_dir)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_dir_bar()
        self._build_main_panels()
        self._build_bottom_bar()

    def _build_dir_bar(self) -> None:
        bar = ttk.Frame(self, padding=(6, 4))
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        ttk.Label(bar, text="Working directory:").grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(bar, textvariable=self._working_dir, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(0, 4)
        )
        ttk.Button(bar, text="Browse…", command=self._browse_dir).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(bar, text="↺", width=3, command=self._refresh_files).grid(row=0, column=3)

    def _build_main_panels(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)

        # --- Left: file list ---
        left = ttk.Frame(paned, padding=4)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text="Markdown Files").grid(row=0, column=0, sticky="w")

        self._listbox = tk.Listbox(left, selectmode=tk.SINGLE, activestyle="dotbox", width=26)
        self._listbox.grid(row=1, column=0, sticky="nsew")
        self._listbox.bind("<Double-Button-1>", lambda _e: self._generate())

        sb_left = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self._listbox.yview)
        sb_left.grid(row=1, column=1, sticky="ns")
        self._listbox.configure(yscrollcommand=sb_left.set)

        paned.add(left, weight=1)

        # --- Right: scrollable config form ---
        right = ttk.Frame(paned, padding=4)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        canvas = tk.Canvas(right, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        sb_right = ttk.Scrollbar(right, orient=tk.VERTICAL, command=canvas.yview)
        sb_right.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=sb_right.set)

        form_frame = ttk.Frame(canvas)
        form_frame.columnconfigure(0, weight=1)
        canvas_window = canvas.create_window((0, 0), window=form_frame, anchor="nw")

        def _on_frame_configure(_e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)

        form_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse-wheel: only when pointer is over the canvas
        def _on_enter(_e):
            canvas.bind_all(
                "<MouseWheel>",
                lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"),
            )

        def _on_leave(_e):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)

        self._build_config_form(form_frame)
        paned.add(right, weight=3)

    def _build_bottom_bar(self) -> None:
        bar = ttk.Frame(self, padding=(6, 4))
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        self._gen_btn = ttk.Button(bar, text="⚡ Generate & Open", command=self._generate)
        self._gen_btn.grid(row=0, column=0, padx=(0, 10))

        self._status_var = tk.StringVar(value="No directory selected.")
        ttk.Label(bar, textvariable=self._status_var, anchor="w").grid(row=0, column=1, sticky="ew")

    # ------------------------------------------------------------------
    # Config form — widgets are created with the correct LabelFrame parent
    # ------------------------------------------------------------------
    def _build_config_form(self, parent: ttk.Frame) -> None:
        d = self._defaults
        row = 0

        # Section 1 — Reveal.js
        lf, row = self._lf(parent, "Reveal.js", row)
        self._erow(lf, 0, "Version",    "reveal_version", d.reveal_version)
        self._erow(lf, 1, "CDN",        "reveal_cdn",     d.reveal_cdn)
        self._crow(lf, 2, "Transition", "transition",     d.transition,      TRANSITIONS)

        # Section 2 — Slide Layout
        lf, row = self._lf(parent, "Slide Layout", row)
        self._erow(lf, 0, "Separator", "slide_separator", d.slide_separator)
        self._erow(lf, 1, "Width",     "width",           d.width)
        self._erow(lf, 2, "Height",    "height",          d.height)
        self._erow(lf, 3, "Margin",    "margin",          d.margin)
        self._erow(lf, 4, "Min Scale", "min_scale",       d.min_scale)
        self._erow(lf, 5, "Max Scale", "max_scale",       d.max_scale)

        # Section 3 — Features (checkbuttons in 2-column grid)
        lf, row = self._lf(parent, "Features", row)
        bool_fields = [
            ("enable_progress",   "Progress",    d.enable_progress),
            ("enable_controls",   "Controls",    d.enable_controls),
            ("enable_history",    "History",     d.enable_history),
            ("align_center",      "Center",      d.align_center),
            ("enable_fragments",  "Fragments",   d.enable_fragments),
            ("show_header_trail", "Header Trail", d.show_header_trail),
        ]
        for i, (key, label, default) in enumerate(bool_fields):
            var = tk.BooleanVar(value=default.lower() == "true")
            self._vars[key] = var
            ttk.Checkbutton(lf, text=label, variable=var).grid(
                row=i // 2, column=i % 2, sticky="w", padx=8, pady=1
            )

        # Section 4 — Custom Theme
        default_ct = d.custom_theme if d.custom_theme in self._css_themes else "(none)"
        lf, row = self._lf(parent, "Custom Theme", row)
        self._crow(lf, 0, "CSS file", "custom_theme", default_ct, self._css_themes)

        # Section 5 — Font Sizes (2-column grid)
        lf, row = self._lf(parent, "Font Sizes", row)
        font_fields = [
            ("font_base", "Base", d.font_base),
            ("font_h1",   "H1",   d.font_h1),
            ("font_h2",   "H2",   d.font_h2),
            ("font_h3",   "H3",   d.font_h3),
            ("font_h4",   "H4",   d.font_h4),
            ("font_h5",   "H5",   d.font_h5),
            ("font_h6",   "H6",   d.font_h6),
            ("font_p",    "P",    d.font_p),
            ("font_li",   "LI",   d.font_li),
        ]
        for i, (key, label, default) in enumerate(font_fields):
            var = tk.StringVar(value=default)
            self._vars[key] = var
            col = (i % 2) * 2
            ttk.Label(lf, text=label + ":").grid(row=i // 2, column=col,     sticky="e", padx=(8, 2))
            ttk.Entry(lf, textvariable=var, width=9).grid(row=i // 2, column=col + 1, sticky="w", padx=(0, 12))

    # ------------------------------------------------------------------
    # LabelFrame / row helpers — widgets created with correct parent
    # ------------------------------------------------------------------
    def _lf(self, parent: ttk.Frame, title: str, row: int):
        """Create a LabelFrame at *row* and return (frame, next_row)."""
        lf = ttk.LabelFrame(parent, text=title, padding=6)
        lf.grid(row=row, column=0, sticky="ew", padx=4, pady=(0, 6))
        lf.columnconfigure(1, weight=1)
        return lf, row + 1

    def _erow(self, lf: ttk.LabelFrame, row: int, label: str, key: str, default: str) -> None:
        """Add a labeled Entry row to *lf*."""
        var = tk.StringVar(value=default)
        self._vars[key] = var
        ttk.Label(lf, text=label + ":").grid(row=row, column=0, sticky="e", padx=(4, 6), pady=1)
        ttk.Entry(lf, textvariable=var).grid(row=row, column=1, sticky="ew", padx=(0, 4), pady=1)

    def _crow(self, lf: ttk.LabelFrame, row: int, label: str, key: str, default: str, values: list) -> None:
        """Add a labeled Combobox row to *lf*."""
        var = tk.StringVar(value=default)
        self._vars[key] = var
        ttk.Label(lf, text=label + ":").grid(row=row, column=0, sticky="e", padx=(4, 6), pady=1)
        ttk.Combobox(lf, textvariable=var, values=values, state="readonly", width=22).grid(
            row=row, column=1, sticky="ew", padx=(0, 4), pady=1
        )

    # ------------------------------------------------------------------
    # Directory / file management
    # ------------------------------------------------------------------
    def _ask_working_dir(self) -> None:
        path = filedialog.askdirectory(title="Select working directory")
        if path:
            self._set_working_dir(path)

    def _browse_dir(self) -> None:
        path = filedialog.askdirectory(title="Select working directory")
        if path:
            self._set_working_dir(path)

    def _refresh_files(self) -> None:
        d = self._working_dir.get()
        if d:
            self._populate_files(Path(d))

    def _set_working_dir(self, path: str) -> None:
        self._working_dir.set(path)
        self._populate_files(Path(path))

    def _populate_files(self, directory: Path) -> None:
        self._listbox.delete(0, tk.END)
        files = sorted(directory.glob("*.md"))
        for f in files:
            self._listbox.insert(tk.END, f.name)
        count = len(files)
        if count:
            self._status_var.set(f"{count} file{'s' if count != 1 else ''} found.")
            self._listbox.selection_set(0)
        else:
            self._status_var.set("No .md files found.")

    def _selected_md_file(self) -> Optional[Path]:
        sel = self._listbox.curselection()
        if not sel:
            return None
        name = self._listbox.get(sel[0])
        return Path(self._working_dir.get()) / name

    # ------------------------------------------------------------------
    # Config reading
    # ------------------------------------------------------------------
    def _read_config(self) -> PresentationConfig:
        kw: dict = {}
        for key, var in self._vars.items():
            if key in _BOOL_FIELDS:
                kw[key] = "true" if var.get() else "false"
            else:
                kw[key] = str(var.get())

        # "(none)" sentinel → None
        raw_ct = kw.get("custom_theme", "(none)")
        kw["custom_theme"] = None if raw_ct == "(none)" else raw_ct

        # GUI always outputs to a temp dir, never next to source file
        kw["output_in_md_dir"] = "false"

        return PresentationConfig(**kw)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def _generate(self) -> None:
        md_file = self._selected_md_file()
        if md_file is None:
            messagebox.showwarning("No file selected", "Please select a Markdown file first.")
            return
        if not md_file.exists():
            messagebox.showerror("File not found", f"{md_file} does not exist.")
            return

        config = self._read_config()
        self._gen_btn.state(["disabled"])
        self._status_var.set("Generating…")

        def _worker() -> None:
            try:
                generator = _build_generator()
                output_file = generator.generate(md_file, config)
                self.after(0, lambda: self._on_success(output_file))
            except Exception as exc:
                self.after(0, lambda: self._on_error(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_success(self, output_file: Path) -> None:
        self._gen_btn.state(["!disabled"])
        self._status_var.set(f"✓ Opened — {output_file}")

    def _on_error(self, exc: Exception) -> None:
        self._gen_btn.state(["!disabled"])
        self._status_var.set(f"✗ {exc}")
        messagebox.showerror("Generation failed", str(exc))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
