import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import subprocess
import threading
import re
import os
import json
import shutil

# ── BBC iPlayer colour palette ───────────────────────────────────────────────
BG         = "#111111"
CARD       = "#1a1a1a"
SURFACE    = "#212020"
BORDER     = "#323232"
INPUT_BG   = "#2E2E2E"
INPUT_BD   = "#404040"
FG         = "#ffffff"
FG_MUT     = "#BDBDBD"
FG_HINT    = "#808080"
PINK       = "#f54997"
PINK_ACT   = "#cf3e80"
SUCCESS_FG = "#4caf79"
ERROR_FG   = "#f47a8a"
WARN_FG    = "#ff9600"

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
ICON_MAIN     = os.path.join(SCRIPT_DIR, "get_iplayer.ico")
ICON_PVR      = os.path.join(SCRIPT_DIR, "get_iplayer_pvr.ico")
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "iplayer_downloader_settings.json")

DEFAULT_SAVE_PATH = os.path.join(os.path.expanduser("~"), "Videos", "Iplayer")

# ── Common get_iplayer install locations on Windows ──────────────────────────
COMMON_LOCATIONS = [
    r"C:\Program Files\get_iplayer\get_iplayer.cmd",
    r"C:\Program Files\get_iplayer\get_iplayer.bat",
    r"C:\Program Files (x86)\get_iplayer\get_iplayer.cmd",
    r"C:\Program Files (x86)\get_iplayer\get_iplayer.bat",
    r"C:\get_iplayer\get_iplayer.cmd",
    r"C:\get_iplayer\get_iplayer.bat",
]

def sanitize(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def find_get_iplayer():
    """Try the script's own folder first, then PATH, then common install paths."""
    local_names = ["get_iplayer.cmd", "get_iplayer.bat", "get_iplayer.exe", "get_iplayer.pl"]
    for name in local_names:
        local = os.path.join(SCRIPT_DIR, name)
        if os.path.isfile(local):
            return local
    found = shutil.which("get_iplayer")
    if found:
        return found
    for loc in COMMON_LOCATIONS:
        if os.path.isfile(loc):
            return loc
    return None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("get_iplayer Downloader")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.settings = load_settings()
        self.save_base = self.settings.get("save_path", DEFAULT_SAVE_PATH)
        self.exe_path  = self.settings.get("exe_path", "") or find_get_iplayer() or ""

        if os.path.exists(ICON_MAIN):
            try:
                self.iconbitmap(ICON_MAIN)
            except Exception:
                pass

        self._build_ui()
        self._center()

        # Warn if get_iplayer not found
        if not self.exe_path:
            self.after(300, self._warn_no_exe)

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        PAD = 20
        outer = tk.Frame(self, bg=BG, padx=PAD, pady=PAD)
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=CARD, bd=0,
                        highlightthickness=1, highlightbackground=BORDER,
                        padx=PAD, pady=PAD)
        card.pack(fill="both", expand=True)

        # Header
        self._build_header(card)
        self._sep(card)

        # Save path row
        self._label(card, "SAVE LOCATION")
        path_row = tk.Frame(card, bg=CARD)
        path_row.pack(fill="x", pady=(4, 12))

        self.save_path_var = tk.StringVar(value=self.save_base)
        path_entry = tk.Entry(path_row, textvariable=self.save_path_var,
                              bg=INPUT_BG, fg=PINK, insertbackground=FG,
                              relief="flat", font=("Consolas", 10),
                              highlightthickness=1,
                              highlightbackground=INPUT_BD,
                              highlightcolor=PINK)
        path_entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.save_path_var.trace_add("write", self._on_save_path_changed)

        browse_btn = tk.Button(path_row, text="📁 Browse",
                               bg=SURFACE, fg=FG_MUT,
                               font=("Segoe UI", 9),
                               relief="flat", cursor="hand2",
                               activebackground=BORDER, activeforeground=FG,
                               highlightthickness=1, highlightbackground=BORDER,
                               command=self._browse_save_path)
        browse_btn.pack(side="left", padx=(6, 0), ipady=7, ipadx=6)

        # Show name
        self._label(card, "SHOW NAME")
        self.show_name_var = tk.StringVar()
        self.show_name_var.trace_add("write", self._update_output_path)
        self._entry(card, self.show_name_var, "e.g. Blue Planet")

        # Output path preview
        preview_frame = tk.Frame(card, bg=SURFACE,
                                 highlightthickness=1, highlightbackground=BORDER)
        preview_frame.pack(fill="x", pady=(0, 14))

        tk.Label(preview_frame, text="→", bg=SURFACE, fg=FG_HINT,
                 font=("Segoe UI", 10)).pack(side="left", padx=(10, 4), pady=6)

        self.output_path_var = tk.StringVar(value=self.save_base + "\\")
        tk.Label(preview_frame, textvariable=self.output_path_var,
                 bg=SURFACE, fg=PINK,
                 font=("Consolas", 10), anchor="w",
                 wraplength=390, justify="left").pack(
                     side="left", pady=6, padx=(0, 8))

        # IDs
        self._label(card, "SHOW / SEASON / EPISODE IDs  (comma-separated)")
        self.ids_var = tk.StringVar()
        self._entry(card, self.ids_var, "e.g. b09w7fd3, p07qr8bz")

        tk.Frame(card, bg=CARD, height=4).pack()

        # Download button
        self.dl_btn = tk.Button(
            card, text="⬇  Start download",
            bg=PINK, fg=FG,
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            activebackground=PINK_ACT, activeforeground=FG,
            command=self._start_download
        )
        self.dl_btn.pack(fill="x", ipady=9)

        # Reset button
        tk.Button(
            card, text="↺   Download another show",
            bg=CARD, fg=FG_MUT,
            font=("Segoe UI", 10),
            relief="flat", cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER,
            activebackground=SURFACE, activeforeground=PINK,
            command=self._reset
        ).pack(fill="x", ipady=7, pady=(8, 0))

        self._sep(card)

        # get_iplayer exe path row
        self._label(card, "get_iplayer EXECUTABLE")
        exe_row = tk.Frame(card, bg=CARD)
        exe_row.pack(fill="x", pady=(4, 12))

        self.exe_var = tk.StringVar(value=self.exe_path)
        exe_entry = tk.Entry(exe_row, textvariable=self.exe_var,
                             bg=INPUT_BG, fg=FG_MUT, insertbackground=FG,
                             relief="flat", font=("Consolas", 10),
                             highlightthickness=1,
                             highlightbackground=INPUT_BD,
                             highlightcolor=PINK)
        exe_entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.exe_var.trace_add("write", self._on_exe_changed)

        tk.Button(exe_row, text="🔍 Browse",
                  bg=SURFACE, fg=FG_MUT,
                  font=("Segoe UI", 9),
                  relief="flat", cursor="hand2",
                  activebackground=BORDER, activeforeground=FG,
                  highlightthickness=1, highlightbackground=BORDER,
                  command=self._browse_exe
                  ).pack(side="left", padx=(6, 0), ipady=7, ipadx=6)

        self._sep(card)

        # Log
        self._label(card, "OUTPUT")
        self.log = scrolledtext.ScrolledText(
            card, height=11, bg="#0d0d0d", fg=FG_MUT,
            insertbackground=FG, relief="flat",
            font=("Consolas", 10), wrap="word",
            highlightthickness=1, highlightbackground=BORDER,
            state="disabled"
        )
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        self.log.tag_config("info",    foreground=FG_MUT)
        self.log.tag_config("cmd",     foreground=PINK)
        self.log.tag_config("success", foreground=SUCCESS_FG)
        self.log.tag_config("error",   foreground=ERROR_FG)
        self.log.tag_config("warning", foreground=WARN_FG)

    def _build_header(self, parent):
        hdr = tk.Frame(parent, bg=CARD)
        hdr.pack(fill="x", pady=(0, 14))

        self._pvr_img = None
        if os.path.exists(ICON_PVR):
            try:
                from PIL import Image, ImageTk
                img = Image.open(ICON_PVR).resize((32, 32), Image.LANCZOS)
                self._pvr_img = ImageTk.PhotoImage(img)
                tk.Label(hdr, image=self._pvr_img, bg=CARD).pack(side="left", padx=(0, 10))
            except Exception:
                self._pvr_img = None

        if self._pvr_img is None:
            tk.Label(hdr, text="▶", bg=PINK, fg=FG,
                     font=("Segoe UI", 13, "bold"),
                     width=3, pady=5).pack(side="left", padx=(0, 10))

        tf = tk.Frame(hdr, bg=CARD)
        tf.pack(side="left", anchor="w")
        tk.Label(tf, text="get_iplayer", bg=CARD, fg=PINK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(tf, text="BBC iPlayer downloader", bg=CARD, fg=FG_HINT,
                 font=("Segoe UI", 9)).pack(anchor="w")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sep(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(0, 14))

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=CARD, fg=FG_HINT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

    def _entry(self, parent, var, placeholder=""):
        e = tk.Entry(parent, textvariable=var,
                     bg=INPUT_BG, fg=FG, insertbackground=FG,
                     relief="flat", font=("Segoe UI", 11),
                     highlightthickness=1,
                     highlightbackground=INPUT_BD,
                     highlightcolor=PINK)
        e.pack(fill="x", ipady=7, pady=(4, 12))

        if placeholder:
            def _fi(event, e=e, ph=placeholder):
                if e.get() == ph:
                    e.delete(0, "end")
                    e.config(fg=FG)
            def _fo(event, e=e, ph=placeholder):
                if not e.get():
                    e.insert(0, ph)
                    e.config(fg=FG_HINT)
            e.insert(0, placeholder)
            e.config(fg=FG_HINT)
            e.bind("<FocusIn>",  _fi)
            e.bind("<FocusOut>", _fo)
            orig = var.get
            var.get = lambda ph=placeholder, orig=orig: ("" if orig() == ph else orig())
        return e

    def _log(self, text, tag="info"):
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_save_path_changed(self, *_):
        self.save_base = self.save_path_var.get()
        self._update_output_path()
        self.settings["save_path"] = self.save_base
        save_settings(self.settings)

    def _on_exe_changed(self, *_):
        self.exe_path = self.exe_var.get()
        self.settings["exe_path"] = self.exe_path
        save_settings(self.settings)

    def _update_output_path(self, *_):
        clean = sanitize(self.show_name_var.get())
        self.output_path_var.set(
            self.save_base.rstrip("\\") + "\\" + clean
        )

    def _browse_save_path(self):
        chosen = filedialog.askdirectory(
            title="Choose default save folder",
            initialdir=self.save_base if os.path.isdir(self.save_base) else "/"
        )
        if chosen:
            # Normalise to Windows-style path
            chosen = os.path.normpath(chosen)
            self.save_path_var.set(chosen)

    def _browse_exe(self):
        chosen = filedialog.askopenfilename(
            title="Locate get_iplayer executable",
            filetypes=[("Executables / Scripts", "*.cmd *.bat *.exe *.pl *"),
                       ("All files", "*.*")]
        )
        if chosen:
            self.exe_var.set(os.path.normpath(chosen))

    def _warn_no_exe(self):
        self._log(
            "⚠  get_iplayer not found automatically.\n"
            "   Set the path to the executable in the field below, or ensure\n"
            "   get_iplayer is on your system PATH.\n\n",
            "warning"
        )

    def _reset(self):
        self.show_name_var.set("")
        self.ids_var.set("")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.dl_btn.configure(state="normal")

    # ── Download ──────────────────────────────────────────────────────────────

    def _start_download(self):
        show_name = sanitize(self.show_name_var.get().strip())
        show_id   = self.ids_var.get().strip()

        if not show_name:
            self._log("⚠  Please enter a show name.\n", "warning"); return
        if not show_id:
            self._log("⚠  Please enter at least one ID.\n", "warning"); return

        # Resolve executable
        exe = self.exe_var.get().strip() or find_get_iplayer()
        if not exe:
            self._log(
                "✖  Cannot find get_iplayer.\n"
                "   Use the 🔍 Browse button below to locate it.\n", "error"
            )
            return

        out_path = self.save_base.rstrip("\\") + "\\" + show_name
        cmd = [exe, f"--pid={show_id}", "--force", "--pid-recursive",
               "--file-prefix=<senum> - <-episodeshort>", "-o", out_path]

        self._log("Command:\n", "info")
        self._log("  " + " ".join(f'"{c}"' if " " in c else c for c in cmd) + "\n\n", "cmd")
        self.dl_btn.configure(state="disabled")

        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()

    def _run(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                shell=False,
            )
            for line in proc.stdout:
                self.after(0, self._log, line, "info")
            proc.wait()
            if proc.returncode == 0:
                self.after(0, self._log, "\n✔  Done.\n", "success")
            else:
                self.after(0, self._log,
                           f"\n✖  Exited with code {proc.returncode}\n", "error")
        except FileNotFoundError:
            self.after(0, self._log,
                       "\n✖  Executable not found — use 🔍 Browse to set the path.\n",
                       "error")
        except Exception as e:
            self.after(0, self._log, f"\n✖  Error: {e}\n", "error")
        finally:
            self.after(0, self.dl_btn.configure, {"state": "normal"})


if __name__ == "__main__":
    app = App()
    app.mainloop()
