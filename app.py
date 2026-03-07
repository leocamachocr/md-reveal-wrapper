"""
app.py — Tkinter GUI for md-reveal-wrapper.
Wraps the SOLID-refactored pipeline in src/ without modifying it.

Two presentation modes:
  Immediate — generates a temp HTML file and opens it via file:// URL.
  Live      — starts a local HTTP server, watches the source .md file and
              images for changes, and auto-reloads the browser tab.
"""
import functools
import http.server
import json
import socketserver
import threading
import time
import webbrowser
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

# Injected into the served HTML in live mode.
# Polls /_live every second; reloads when the version counter changes.
_LIVE_RELOAD_SCRIPT = """\
<script>
(function () {
    var _lrv = null;
    function _lrPoll() {
        fetch('/_live', {cache: 'no-store'})
            .then(function (r) { return r.text(); })
            .then(function (v) {
                if (_lrv === null) { _lrv = v; }
                else if (v !== _lrv) { location.reload(); }
            })
            .catch(function () {});
    }
    setInterval(_lrPoll, 1000);
})();
</script>"""


# ---------------------------------------------------------------------------
# Live HTTP server
# ---------------------------------------------------------------------------

def _make_handler(live_server: "LiveServer") -> type:
    """Return a request-handler class closed over *live_server*."""

    class _Handler(http.server.SimpleHTTPRequestHandler):
        _ls = live_server

        def do_GET(self) -> None:
            if self.path == "/_live":
                self._serve_version()
            elif self.path in ("/", "/presentation.html"):
                self._serve_html()
            else:
                super().do_GET()

        def _serve_version(self) -> None:
            data = str(self._ls.version).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _serve_html(self) -> None:
            try:
                html = (self._ls.output_dir / "presentation.html").read_text(encoding="utf-8")
            except FileNotFoundError:
                self.send_error(503, "Presentation not ready yet")
                return
            html = html.replace("</body>", _LIVE_RELOAD_SCRIPT + "\n</body>", 1)
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            # Prevent the browser from sending a Referer header when loading
            # external resources (images, fonts, etc.). Without this, CDNs with
            # hotlink protection return 403 because they see an unknown referer
            # (http://127.0.0.1:<port>) instead of the expected file:// origin.
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args) -> None:  # silence request logs
            pass

    return _Handler


class LiveServer:
    """HTTP server + file watcher for live-preview mode."""

    _IMG_GLOBS = (
        "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.webp",
        "*.PNG", "*.JPG", "*.JPEG",
    )

    def __init__(self) -> None:
        self._server: Optional[socketserver.TCPServer] = None
        self._port: int = 0
        self._version: int = 0
        self._running: bool = False
        self._output_dir: Optional[Path] = None
        self._md_file: Optional[Path] = None
        self._on_change = None

    # -- public interface ----------------------------------------------------

    @property
    def version(self) -> int:
        return self._version

    @property
    def output_dir(self) -> Optional[Path]:
        return self._output_dir

    @property
    def port(self) -> int:
        return self._port

    @property
    def running(self) -> bool:
        return self._running

    def start(self, output_dir: Path, md_file: Path, on_change) -> int:
        """Start HTTP server and file watcher; return the port."""
        self._output_dir = output_dir
        self._md_file = md_file
        self._on_change = on_change
        self._version = 0
        self._running = True

        handler_cls = _make_handler(self)
        handler = functools.partial(handler_cls, directory=str(output_dir))

        class _TCP(socketserver.TCPServer):
            allow_reuse_address = True

        self._server = _TCP(("127.0.0.1", 0), handler)
        self._port = self._server.server_address[1]

        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        threading.Thread(target=self._watch, daemon=True).start()
        return self._port

    def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server = None

    def bump(self) -> None:
        """Increment version so connected browsers reload."""
        self._version += 1

    # -- private -------------------------------------------------------------

    def _watch(self) -> None:
        last_mtimes: dict = {}
        first = True
        while self._running:
            watched: set = {self._md_file}
            for pat in self._IMG_GLOBS:
                watched.update(self._md_file.parent.glob(pat))

            changed = False
            for p in list(watched):
                if p.exists():
                    mt = p.stat().st_mtime
                    if p in last_mtimes and last_mtimes[p] != mt:
                        changed = True
                    last_mtimes[p] = mt
                elif p in last_mtimes:
                    del last_mtimes[p]
                    changed = True

            if changed and not first and callable(self._on_change):
                self._on_change()

            first = False
            time.sleep(1)


# ---------------------------------------------------------------------------
# Settings persistence
# ---------------------------------------------------------------------------

class SettingsManager:
    PATH = Path.home() / ".md-wrapper-settings"

    def load(self) -> dict:
        try:
            return json.loads(self.PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save(self, data: dict) -> None:
        self.PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _build_generator(open_browser: bool = True) -> PresentationGenerator:
    """Compose the object graph — mirrors main.py's build_generator()."""
    file_manager = FileManager()
    return PresentationGenerator(
        parser=MarkdownParser(),
        pipeline=DefaultSlideProcessorPipeline(),
        renderer=TemplateRenderer(file_manager),
        file_manager=file_manager,
        open_browser=open_browser,
    )


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("md-reveal-wrapper")
        self.minsize(860, 580)
        _ico = resolve_resource("assets/app.ico")
        if Path(_ico).exists():
            self.iconbitmap(_ico)

        self._settings_mgr = SettingsManager()
        _settings = self._settings_mgr.load()
        self._favorites: list = _settings.get("favorites", [])

        if "config" in _settings:
            raw = _settings["config"]
            if not raw.get("custom_theme"):
                raw["custom_theme"] = None
            self._defaults = ConfigLoader()._to_config(raw)
        else:
            try:
                self._defaults = ConfigLoader().load(resolve_resource("config.properties"))
            except Exception:
                self._defaults = PresentationConfig()

        themes_dir = Path(resolve_resource("templates/themes"))
        self._css_themes = ["(none)"] + sorted(p.name for p in themes_dir.glob("*.css"))

        self._vars: dict = {}
        self._working_dir = tk.StringVar()
        self._mode_var = tk.StringVar(value="immediate")

        # Live-mode state
        self._live_server = LiveServer()
        self._live_md_file: Optional[Path] = None
        self._regen_in_progress = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
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
        self._refresh_favorites()

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

        # --- Left: favorites + file list ---
        left = ttk.Frame(paned, padding=4)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        fav_lf = ttk.LabelFrame(left, text="★ Favoritos", padding=4)
        fav_lf.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        fav_lf.columnconfigure(0, weight=1)

        fav_btn_bar = ttk.Frame(fav_lf)
        fav_btn_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Button(fav_btn_bar, text="[+] Agregar", command=self._add_favorite).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(fav_btn_bar, text="[−] Quitar", command=self._remove_favorite).pack(side=tk.LEFT)

        self._fav_listbox = tk.Listbox(fav_lf, selectmode=tk.SINGLE, activestyle="dotbox", height=5, width=26)
        self._fav_listbox.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self._fav_listbox.bind("<<ListboxSelect>>", self._select_favorite)

        fav_sb = ttk.Scrollbar(fav_lf, orient=tk.VERTICAL, command=self._fav_listbox.yview)
        fav_sb.grid(row=1, column=1, sticky="ns", pady=(4, 0))
        self._fav_listbox.configure(yscrollcommand=fav_sb.set)

        files_lf = ttk.LabelFrame(left, text="Archivos .md", padding=4)
        files_lf.grid(row=1, column=0, columnspan=2, sticky="nsew")
        files_lf.columnconfigure(0, weight=1)
        files_lf.rowconfigure(0, weight=1)

        self._listbox = tk.Listbox(files_lf, selectmode=tk.SINGLE, activestyle="dotbox", width=26)
        self._listbox.grid(row=0, column=0, sticky="nsew")
        self._listbox.bind("<Double-Button-1>", lambda _e: self._generate())

        sb_left = ttk.Scrollbar(files_lf, orient=tk.VERTICAL, command=self._listbox.yview)
        sb_left.grid(row=0, column=1, sticky="ns")
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

        form_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))

        canvas.bind("<Enter>", lambda _e: canvas.bind_all(
            "<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units")
        ))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        self._build_config_form(form_frame)
        paned.add(right, weight=3)

    def _build_bottom_bar(self) -> None:
        bar = ttk.Frame(self, padding=(6, 4))
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(4, weight=1)

        ttk.Button(bar, text="💾 Guardar predeterminados", command=self._save_settings).grid(
            row=0, column=0, padx=(0, 10)
        )

        mode_lf = ttk.LabelFrame(bar, text="Modo", padding=(6, 2))
        mode_lf.grid(row=0, column=1, padx=(0, 8))
        ttk.Radiobutton(
            mode_lf, text="Inmediato", variable=self._mode_var, value="immediate",
            command=self._on_mode_change,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Radiobutton(
            mode_lf, text="Live", variable=self._mode_var, value="live",
            command=self._on_mode_change,
        ).pack(side=tk.LEFT)

        self._gen_btn = ttk.Button(bar, text="⚡ Generate & Open", command=self._generate)
        self._gen_btn.grid(row=0, column=2, padx=(0, 6))

        self._stop_btn = ttk.Button(bar, text="■ Stop Live", command=self._stop_live)
        self._stop_btn.grid(row=0, column=3, padx=(0, 10))
        self._stop_btn.grid_remove()  # hidden until live server starts

        self._status_var = tk.StringVar(value="No directory selected.")
        ttk.Label(bar, textvariable=self._status_var, anchor="w").grid(row=0, column=4, sticky="ew")

    # ------------------------------------------------------------------
    # Config form
    # ------------------------------------------------------------------

    def _build_config_form(self, parent: ttk.Frame) -> None:
        d = self._defaults
        row = 0

        lf, row = self._lf(parent, "Reveal.js", row)
        self._erow(lf, 0, "Version",    "reveal_version", d.reveal_version)
        self._erow(lf, 1, "CDN",        "reveal_cdn",     d.reveal_cdn)
        self._crow(lf, 2, "Transition", "transition",     d.transition, TRANSITIONS)

        lf, row = self._lf(parent, "Slide Layout", row)
        self._erow(lf, 0, "Separator", "slide_separator", d.slide_separator)
        self._erow(lf, 1, "Width",     "width",           d.width)
        self._erow(lf, 2, "Height",    "height",          d.height)
        self._erow(lf, 3, "Margin",    "margin",          d.margin)
        self._erow(lf, 4, "Min Scale", "min_scale",       d.min_scale)
        self._erow(lf, 5, "Max Scale", "max_scale",       d.max_scale)

        lf, row = self._lf(parent, "Features", row)
        bool_fields = [
            ("enable_progress",   "Progress",     d.enable_progress),
            ("enable_controls",   "Controls",     d.enable_controls),
            ("enable_history",    "History",      d.enable_history),
            ("align_center",      "Center",       d.align_center),
            ("enable_fragments",  "Fragments",    d.enable_fragments),
            ("show_header_trail", "Header Trail", d.show_header_trail),
        ]
        for i, (key, label, default) in enumerate(bool_fields):
            var = tk.BooleanVar(value=default.lower() == "true")
            self._vars[key] = var
            ttk.Checkbutton(lf, text=label, variable=var).grid(
                row=i // 2, column=i % 2, sticky="w", padx=8, pady=1
            )

        default_ct = d.custom_theme if d.custom_theme in self._css_themes else "(none)"
        lf, row = self._lf(parent, "Custom Theme", row)
        self._crow(lf, 0, "CSS file", "custom_theme", default_ct, self._css_themes)

        lf, row = self._lf(parent, "Font Sizes", row)
        font_fields = [
            ("font_base", "Base", d.font_base), ("font_h1", "H1", d.font_h1),
            ("font_h2",   "H2",  d.font_h2),   ("font_h3", "H3", d.font_h3),
            ("font_h4",   "H4",  d.font_h4),   ("font_h5", "H5", d.font_h5),
            ("font_h6",   "H6",  d.font_h6),   ("font_p",  "P",  d.font_p),
            ("font_li",   "LI",  d.font_li),
        ]
        for i, (key, label, default) in enumerate(font_fields):
            var = tk.StringVar(value=default)
            self._vars[key] = var
            col = (i % 2) * 2
            ttk.Label(lf, text=label + ":").grid(row=i // 2, column=col,     sticky="e", padx=(8, 2))
            ttk.Entry(lf, textvariable=var, width=9).grid(row=i // 2, column=col + 1, sticky="w", padx=(0, 12))

    # ------------------------------------------------------------------
    # LabelFrame / row helpers
    # ------------------------------------------------------------------

    def _lf(self, parent, title, row):
        lf = ttk.LabelFrame(parent, text=title, padding=6)
        lf.grid(row=row, column=0, sticky="ew", padx=4, pady=(0, 6))
        lf.columnconfigure(1, weight=1)
        return lf, row + 1

    def _erow(self, lf, row, label, key, default):
        var = tk.StringVar(value=default)
        self._vars[key] = var
        ttk.Label(lf, text=label + ":").grid(row=row, column=0, sticky="e", padx=(4, 6), pady=1)
        ttk.Entry(lf, textvariable=var).grid(row=row, column=1, sticky="ew", padx=(0, 4), pady=1)

    def _crow(self, lf, row, label, key, default, values):
        var = tk.StringVar(value=default)
        self._vars[key] = var
        ttk.Label(lf, text=label + ":").grid(row=row, column=0, sticky="e", padx=(4, 6), pady=1)
        ttk.Combobox(lf, textvariable=var, values=values, state="readonly", width=22).grid(
            row=row, column=1, sticky="ew", padx=(0, 4), pady=1
        )

    # ------------------------------------------------------------------
    # Favorites management
    # ------------------------------------------------------------------

    def _add_favorite(self) -> None:
        path = self._working_dir.get()
        if path and path not in self._favorites:
            self._favorites.append(path)
            self._refresh_favorites()
            self._save_settings()

    def _remove_favorite(self) -> None:
        sel = self._fav_listbox.curselection()
        if sel:
            self._favorites.pop(sel[0])
            self._refresh_favorites()
            self._save_settings()

    def _select_favorite(self, _event=None) -> None:
        sel = self._fav_listbox.curselection()
        if sel:
            self._set_working_dir(self._favorites[sel[0]])

    def _refresh_favorites(self) -> None:
        self._fav_listbox.delete(0, tk.END)
        for path in self._favorites:
            self._fav_listbox.insert(tk.END, Path(path).name)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _save_settings(self) -> None:
        raw_config = {}
        for key, var in self._vars.items():
            val = var.get()
            if isinstance(val, bool):
                raw_config[key] = "true" if val else "false"
            else:
                raw_config[key] = str(val).strip()
        if raw_config.get("custom_theme") == "(none)":
            raw_config["custom_theme"] = ""
        self._settings_mgr.save({"favorites": self._favorites, "config": raw_config})

    def _on_close(self) -> None:
        self._save_settings()
        if self._live_server.running:
            self._live_server.stop()
        self.destroy()

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

    def _read_config(self, live_mode: bool = False) -> PresentationConfig:
        kw: dict = {}
        for key, var in self._vars.items():
            if key in _BOOL_FIELDS:
                kw[key] = "true" if var.get() else "false"
            else:
                kw[key] = str(var.get())

        raw_ct = kw.get("custom_theme", "(none)")
        kw["custom_theme"] = None if raw_ct == "(none)" else raw_ct

        if live_mode:
            # Use a stable subdir next to the source so the HTTP server
            # can keep serving from the same path across re-generations.
            kw["output_in_md_dir"] = "true"
        else:
            kw["output_in_md_dir"] = "false"

        return PresentationConfig(**kw)

    # ------------------------------------------------------------------
    # Mode toggle
    # ------------------------------------------------------------------

    def _on_mode_change(self) -> None:
        if self._mode_var.get() == "immediate" and self._live_server.running:
            self._stop_live()

    # ------------------------------------------------------------------
    # Generation — dispatch
    # ------------------------------------------------------------------

    def _generate(self) -> None:
        md_file = self._selected_md_file()
        if md_file is None:
            messagebox.showwarning("No file selected", "Please select a Markdown file first.")
            return
        if not md_file.exists():
            messagebox.showerror("File not found", f"{md_file} does not exist.")
            return

        if self._mode_var.get() == "live":
            self._generate_live(md_file)
        else:
            self._generate_immediate(md_file)

    # ------------------------------------------------------------------
    # Generation — immediate mode
    # ------------------------------------------------------------------

    def _generate_immediate(self, md_file: Path) -> None:
        config = self._read_config(live_mode=False)
        self._gen_btn.state(["disabled"])
        self._status_var.set("Generating…")

        def _worker() -> None:
            try:
                output_file = _build_generator(open_browser=True).generate(md_file, config)
                self.after(0, lambda: self._on_success(output_file))
            except Exception as exc:
                self.after(0, lambda: self._on_error(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_success(self, output_file: Path) -> None:
        self._gen_btn.state(["!disabled"])
        self._status_var.set(f"✓ Opened — {output_file}")

    # ------------------------------------------------------------------
    # Generation — live mode
    # ------------------------------------------------------------------

    def _generate_live(self, md_file: Path) -> None:
        # If the server is running for a different file, restart it.
        if self._live_server.running and self._live_md_file != md_file:
            self._live_server.stop()
            self._stop_btn.grid_remove()

        self._gen_btn.state(["disabled"])
        self._status_var.set("Live: generating…")
        is_first_start = not self._live_server.running

        def _worker() -> None:
            try:
                output_file = _build_generator(open_browser=False).generate(
                    md_file, self._read_config(live_mode=True)
                )
                self.after(0, lambda: self._on_live_generated(md_file, output_file.parent, is_first_start))
            except Exception as exc:
                self.after(0, lambda: self._on_error(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_live_generated(self, md_file: Path, output_dir: Path, first_start: bool) -> None:
        self._gen_btn.state(["!disabled"])
        self._live_md_file = md_file

        if first_start:
            port = self._live_server.start(
                output_dir=output_dir,
                md_file=md_file,
                on_change=self._on_file_changed,
            )
            webbrowser.open(f"http://127.0.0.1:{port}")
            self._stop_btn.grid()
        else:
            # Server already running — bump version so the browser reloads.
            self._live_server.bump()

        self._status_var.set(
            f"Live  http://127.0.0.1:{self._live_server.port}  —  watching {md_file.name}"
        )

    def _on_file_changed(self) -> None:
        """Called from the watcher thread; schedules a regen on the main thread."""
        self.after(0, self._regen_live)

    def _regen_live(self) -> None:
        if self._regen_in_progress or not self._live_server.running:
            return
        md_file = self._live_md_file
        if md_file is None:
            return

        self._regen_in_progress = True
        self._status_var.set("Live: regenerating…")

        def _worker() -> None:
            try:
                _build_generator(open_browser=False).generate(
                    md_file, self._read_config(live_mode=True)
                )
                self._live_server.bump()
                self.after(0, lambda: self._status_var.set(
                    f"Live  http://127.0.0.1:{self._live_server.port}  —  watching {md_file.name}"
                ))
            except Exception as exc:
                self.after(0, lambda: self._status_var.set(f"Live: regen error — {exc}"))
            finally:
                self._regen_in_progress = False

        threading.Thread(target=_worker, daemon=True).start()

    def _stop_live(self) -> None:
        self._live_server.stop()
        self._live_md_file = None
        self._regen_in_progress = False
        self._stop_btn.grid_remove()
        self._status_var.set("Live server stopped.")

    # ------------------------------------------------------------------
    # Shared error handler
    # ------------------------------------------------------------------

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
