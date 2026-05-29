"""get_iplayer GUI — a small BBC iPlayer download front-end for get_iplayer."""

import os
import re
import json
import shutil
import struct
import threading
import subprocess
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox

# ── BBC iPlayer colour palette ───────────────────────────────────────────────
BG, CARD, SURFACE, BORDER          = "#111111", "#1a1a1a", "#212020", "#323232"
INPUT_BG, INPUT_BD                 = "#2E2E2E", "#404040"
FG, FG_MUT, FG_HINT                = "#ffffff", "#BDBDBD", "#808080"
PINK, PINK_ACT                     = "#f54997", "#cf3e80"
SUCCESS_FG, ERROR_FG, WARN_FG      = "#4caf79", "#f47a8a", "#ff9600"
LOG_BG                             = "#0d0d0d"

# ── Fonts ─────────────────────────────────────────────────────────────────────
F_TITLE   = ("Segoe UI", 12, "bold")
F_SUB     = ("Segoe UI", 10)
F_BTN     = ("Segoe UI", 10)
F_BTN_BD  = ("Segoe UI", 11, "bold")
F_LABEL   = ("Segoe UI", 9, "bold")
F_SMALL   = ("Segoe UI", 9)
F_ENTRY   = ("Segoe UI", 11)
F_MONO    = ("Consolas", 10)

# ── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
ICON_MAIN     = os.path.join(SCRIPT_DIR, "get_iplayer.ico")
ICON_PVR      = os.path.join(SCRIPT_DIR, "get_iplayer_pvr.ico")
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "iplayer_downloader_settings.json")
DEFAULT_SAVE_PATH = os.path.join(os.path.expanduser("~"), "Videos", "Iplayer")

EXE_NAMES = ("get_iplayer.cmd", "get_iplayer.bat", "get_iplayer.exe", "get_iplayer.pl")
COMMON_LOCATIONS = [
    os.path.join(base, "get_iplayer", name)
    for base in (r"C:\Program Files", r"C:\Program Files (x86)", "C:\\")
    for name in ("get_iplayer.cmd", "get_iplayer.bat")
]
_INVALID = re.compile(r'[\\/:*?"<>|]')


# ── Helpers ───────────────────────────────────────────────────────────────────
def sanitize(name):
    return _INVALID.sub("", name)


def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
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
    """Return path to get_iplayer: script dir, then PATH, then common locations."""
    for name in EXE_NAMES:
        local = os.path.join(SCRIPT_DIR, name)
        if os.path.isfile(local):
            return local
    found = shutil.which("get_iplayer")
    if found:
        return found
    return next((loc for loc in COMMON_LOCATIONS if os.path.isfile(loc)), None)


def load_icon(size=50):
    """Load an icon as a Tk image, trying PIL then raw PNG-in-ICO. Returns img or None."""
    for path in (ICON_MAIN, ICON_PVR):
        if not os.path.exists(path):
            continue
        try:  # PIL
            from PIL import Image, ImageTk
            ico = Image.open(path)
            best = None
            for frame in range(getattr(ico, "n_frames", 1)):
                ico.seek(frame)
                if best is None or ico.size[0] > best.size[0]:
                    best = ico.copy()
            return ImageTk.PhotoImage(best.resize((size, size), Image.LANCZOS).convert("RGBA"))
        except Exception:
            pass
        try:  # raw PNG extracted from .ico (no dependencies)
            with open(path, "rb") as f:
                f.read(4)
                count = struct.unpack_from("<H", f.read(2))[0]
                entries = []
                for _ in range(count):
                    d = f.read(16)
                    entries.append((
                        struct.unpack_from("B", d, 0)[0] or 256,
                        struct.unpack_from("<I", d, 12)[0],
                        struct.unpack_from("<I", d, 8)[0],
                    ))
                entries.sort(reverse=True)
                _, offset, length = entries[0]
                f.seek(offset)
                raw = f.read(length)
            if raw[:8] == b"\x89PNG\r\n\x1a\n":
                img = tk.PhotoImage(data=raw)
                factor = max(1, img.width() // size)
                return img.subsample(factor, factor)
        except Exception:
            pass
    return None


def styled_button(parent, text, command, *, primary=False, fg=None, font=F_BTN, flat=True):
    """Create a consistently-styled button. primary=pink filled; otherwise outlined."""
    if primary:
        opts = dict(bg=PINK, fg=FG, activebackground=PINK_ACT, activeforeground=FG)
    else:
        opts = dict(bg=SURFACE, fg=fg or FG_MUT,
                    activebackground=BORDER, activeforeground=fg or FG,
                    highlightthickness=1, highlightbackground=BORDER)
    return tk.Button(parent, text=text, command=command, font=font,
                     relief="flat", cursor="hand2", bd=0, **opts)


def divider(parent, pady=(8, 8), vertical=False):
    if vertical:
        return tk.Frame(parent, bg=BORDER, width=1)
    return tk.Frame(parent, bg=BORDER, height=1)


# ── Settings window ────────────────────────────────────────────────────────────
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Settings")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        try:
            self.iconbitmap(ICON_MAIN)
        except Exception:
            pass

        outer = tk.Frame(self, bg=BG, padx=20, pady=20)
        outer.pack(fill="both", expand=True)
        card = tk.Frame(outer, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER, padx=20, pady=20)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="SETTINGS", bg=CARD, fg=PINK,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 12))
        divider(card, pady=(0, 12)).pack(fill="x")

        tk.Label(card, text="get_iplayer EXECUTABLE", bg=CARD, fg=FG_HINT,
                 font=F_LABEL).pack(anchor="w")
        tk.Label(card, text="Path to get_iplayer.cmd / .bat / .exe", bg=CARD,
                 fg=FG_HINT, font=("Segoe UI", 8)).pack(anchor="w", pady=(1, 4))

        exe_row = tk.Frame(card, bg=CARD)
        exe_row.pack(fill="x", pady=(0, 4))
        self.exe_var = tk.StringVar(value=parent.exe_path)
        tk.Entry(exe_row, textvariable=self.exe_var, bg=INPUT_BG, fg=FG_MUT,
                 insertbackground=FG, relief="flat", font=F_MONO,
                 highlightthickness=1, highlightbackground=INPUT_BD,
                 highlightcolor=PINK).pack(side="left", fill="x", expand=True, ipady=7)
        styled_button(exe_row, "🔍 Browse", self._browse_exe, font=F_SMALL
                      ).pack(side="left", padx=(6, 0), ipady=7, ipadx=6)

        divider(card, pady=(16, 12)).pack(fill="x")

        btn_row = tk.Frame(card, bg=CARD)
        btn_row.pack(fill="x")
        styled_button(btn_row, "Save", self._save, primary=True
                      ).pack(side="left", fill="x", expand=True, ipady=7)
        divider(btn_row, vertical=True).pack(side="left", fill="y", padx=6)
        styled_button(btn_row, "Close", self.destroy
                      ).pack(side="left", fill="x", expand=True, ipady=7)

        self.update_idletasks()
        w = max(self.winfo_width(), 420)
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"{w}x{self.winfo_height()}+{x}+{y}")

    def _browse_exe(self):
        chosen = filedialog.askopenfilename(
            title="Locate get_iplayer executable",
            filetypes=[("Executables / Scripts", "*.cmd *.bat *.exe *.pl *"),
                       ("All files", "*.*")])
        if chosen:
            self.exe_var.set(os.path.normpath(chosen))

    def _save(self):
        exe = self.exe_var.get().strip()
        self.parent.exe_path = exe
        self.parent.settings["exe_path"] = exe
        save_settings(self.parent.settings)
        self.destroy()


# ── Main app ─────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("get_iplayer Downloader")
        self.configure(bg=BG)

        self.settings  = load_settings()
        self.save_base = self.settings.get("save_path", DEFAULT_SAVE_PATH)
        self.exe_path  = self.settings.get("exe_path", "") or find_get_iplayer() or ""
        self._proc     = None
        self._out_path = ""

        try:
            self.iconbitmap(ICON_MAIN)
        except Exception:
            pass

        self._build_ui()
        self._center()
        self._refresh_controls()

        if not self.exe_path:
            self.after(300, self._warn_no_exe)

    def _center(self, w=560, h=780):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── UI construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        PAD = 20
        outer = tk.Frame(self, bg=BG, padx=PAD)
        outer.pack(fill="both", expand=True, pady=(PAD, PAD))
        outer.pack_propagate(False)

        card = tk.Frame(outer, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER, padx=PAD)
        card.pack(fill="both", expand=True)

        self._build_header(card)
        divider(card, pady=(0, 10)).pack(fill="x")

        # Save location
        self._label(card, "SAVE LOCATION")
        save_row = tk.Frame(card, bg=CARD)
        save_row.pack(fill="x", pady=(3, 8))
        self.save_path_var = tk.StringVar(value=self.save_base)
        tk.Entry(save_row, textvariable=self.save_path_var, bg=INPUT_BG, fg=PINK,
                 insertbackground=FG, relief="flat", font=F_MONO,
                 highlightthickness=1, highlightbackground=INPUT_BD,
                 highlightcolor=PINK).pack(side="left", fill="x", expand=True, ipady=7)
        styled_button(save_row, "📁 Browse", self._browse_save_path, font=F_SMALL
                      ).pack(side="left", padx=(6, 0), ipady=7, ipadx=6)

        # Show name
        self._label(card, "SHOW NAME")
        self.show_name_var = tk.StringVar()
        self._entry(card, self.show_name_var, "e.g. Blue Planet")

        # Output path preview
        preview = tk.Frame(card, bg=SURFACE, highlightthickness=1,
                           highlightbackground=BORDER)
        preview.pack(fill="x", pady=(0, 8))
        tk.Label(preview, text="→", bg=SURFACE, fg=FG_HINT,
                 font=F_SUB).pack(side="left", padx=(10, 4), pady=6)
        self.output_path_var = tk.StringVar(value=self.save_base + "\\")
        tk.Label(preview, textvariable=self.output_path_var, bg=SURFACE, fg=PINK,
                 font=F_MONO, anchor="w", wraplength=390,
                 justify="left").pack(side="left", pady=6, padx=(0, 8))

        # Traces — registered now that output_path_var exists
        self.save_path_var.trace_add("write", self._on_save_path_changed)
        self.show_name_var.trace_add("write", self._update_output_path)

        # IDs
        self._label(card, "SHOW / SEASON / EPISODE IDs  (comma-separated)")
        self.ids_var = tk.StringVar()
        self._entry(card, self.ids_var, "e.g. b09w7fd3, p07qr8bz")

        # Start / Cancel
        action_row = tk.Frame(card, bg=CARD)
        action_row.pack(fill="x")
        self.dl_btn = styled_button(action_row, "⬇  Start", self._start_download,
                                    primary=True, font=F_BTN_BD)
        self.dl_btn.pack(side="left", fill="x", expand=True, ipady=8)
        divider(action_row, vertical=True).pack(side="left", fill="y", padx=4)
        self.cancel_btn = styled_button(action_row, "✖  Cancel", self._cancel_download,
                                        fg=ERROR_FG, font=F_BTN_BD)
        self.cancel_btn.pack(side="left", fill="x", expand=True, ipady=8)

        # Folder actions
        divider(card, pady=(8, 0)).pack(fill="x")
        self._label(card, "FOLDER ACTIONS")
        styled_button(card, "📂  Show folder", self._show_folder
                      ).pack(fill="x", pady=(6, 4), ipady=7)

        folder_row = tk.Frame(card, bg=CARD)
        folder_row.pack(fill="x")
        styled_button(folder_row, "🗑  Delete folder", self._delete_folder, fg=ERROR_FG
                      ).pack(side="left", fill="x", expand=True, ipady=7)
        divider(folder_row, vertical=True).pack(side="left", fill="y", padx=4)
        styled_button(folder_row, "🗂  Delete files only", self._delete_files, fg=WARN_FG
                      ).pack(side="left", fill="x", expand=True, ipady=7)

        # Reset
        divider(card, pady=(8, 0)).pack(fill="x")
        reset = styled_button(card, "↺   Download another show", self._reset)
        reset.configure(bg=CARD, activebackground=SURFACE, activeforeground=PINK)
        reset.pack(fill="x", ipady=7)

        divider(card).pack(fill="x")

        # Output log
        self._label(card, "OUTPUT")
        self.log = scrolledtext.ScrolledText(
            card, height=6, bg=LOG_BG, fg=FG_MUT, insertbackground=FG,
            relief="flat", font=F_MONO, wrap="word",
            highlightthickness=1, highlightbackground=BORDER, state="disabled")
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        for tag, colour in (("info", FG_MUT), ("cmd", PINK), ("success", SUCCESS_FG),
                            ("error", ERROR_FG), ("warning", WARN_FG)):
            self.log.tag_config(tag, foreground=colour)

    def _build_header(self, parent):
        hdr = tk.Frame(parent, bg=CARD)
        hdr.pack(fill="x", pady=(6, 0))

        gear = styled_button(hdr, "⚙", self._open_settings, font=("Segoe UI", 11))
        gear.configure(bg=CARD, highlightthickness=0, activebackground=SURFACE)
        gear.pack(side="right", pady=8)

        self._icon = load_icon(50)
        if self._icon:
            tk.Label(hdr, image=self._icon, bg=CARD, bd=0
                     ).pack(side="left", padx=(0, 10), pady=6)

        title = tk.Frame(hdr, bg=CARD)
        title.pack(side="left", anchor="center")
        tk.Label(title, text="get_iplayer", bg=CARD, fg=PINK,
                 font=F_TITLE).pack(side="left")
        tk.Label(title, text="  —  BBC iPlayer downloader", bg=CARD, fg=FG_HINT,
                 font=F_SUB).pack(side="left")

    # ── Small UI helpers ──────────────────────────────────────────────────────
    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=CARD, fg=FG_HINT, font=F_LABEL).pack(anchor="w")

    def _entry(self, parent, var, placeholder=""):
        e = tk.Entry(parent, textvariable=var, bg=INPUT_BG, fg=FG,
                     insertbackground=FG, relief="flat", font=F_ENTRY,
                     highlightthickness=1, highlightbackground=INPUT_BD,
                     highlightcolor=PINK)
        e.pack(fill="x", ipady=6, pady=(3, 8))
        if placeholder:
            def on_in(_):
                if e.get() == placeholder:
                    e.delete(0, "end")
                    e.config(fg=FG)
            def on_out(_):
                if not e.get():
                    e.insert(0, placeholder)
                    e.config(fg=FG_HINT)
            e.insert(0, placeholder)
            e.config(fg=FG_HINT)
            e.bind("<FocusIn>", on_in)
            e.bind("<FocusOut>", on_out)
            real_get = var.get
            var.get = lambda: "" if real_get() == placeholder else real_get()
        return e

    def _log(self, text, tag="info"):
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _refresh_controls(self):
        running = self._proc is not None
        self.dl_btn.configure(state="disabled" if running else "normal")
        self.cancel_btn.configure(state="normal" if running else "disabled")

    # ── Events ──────────────────────────────────────────────────────────────────
    def _open_settings(self):
        SettingsWindow(self)

    def _on_save_path_changed(self, *_):
        self.save_base = self.save_path_var.get()
        self._update_output_path()
        self.settings["save_path"] = self.save_base
        save_settings(self.settings)

    def _update_output_path(self, *_):
        self.output_path_var.set(self._folder_for(self.show_name_var.get()))

    def _browse_save_path(self):
        start = self.save_base if os.path.isdir(self.save_base) else "/"
        chosen = filedialog.askdirectory(title="Choose default save folder", initialdir=start)
        if chosen:
            self.save_path_var.set(os.path.normpath(chosen))

    def _warn_no_exe(self):
        self._log("⚠  get_iplayer not found automatically.\n"
                  "   Open Settings (⚙) to set the path to the executable.\n\n", "warning")

    def _reset(self):
        self.show_name_var.set("")
        self.ids_var.set("")
        self._out_path = ""
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._refresh_controls()

    # ── Download ──────────────────────────────────────────────────────────────
    def _folder_for(self, show_name):
        return self.save_base.rstrip("\\") + "\\" + sanitize(show_name)

    def _start_download(self):
        show_name = sanitize(self.show_name_var.get().strip())
        show_id = self.ids_var.get().strip()
        if not show_name:
            return self._log("⚠  Please enter a show name.\n", "warning")
        if not show_id:
            return self._log("⚠  Please enter at least one ID.\n", "warning")

        exe = self.exe_path or find_get_iplayer()
        if not exe:
            return self._log("✖  Cannot find get_iplayer.\n"
                             "   Open Settings (⚙) to set the path.\n", "error")

        self._out_path = self._folder_for(show_name)
        cmd = [exe, f"--pid={show_id}", "--force", "--pid-recursive",
               "--file-prefix=<senum> - <-episodeshort>", "-o", self._out_path]

        self._log("Command:\n", "info")
        self._log("  " + " ".join(f'"{c}"' if " " in c else c for c in cmd) + "\n\n", "cmd")
        self._refresh_controls()
        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()

    def _run(self, cmd):
        try:
            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True,
                                          bufsize=1, shell=False)
            for line in self._proc.stdout:
                self.after(0, self._log, line, "info")
            self._proc.wait()
            rc = self._proc.returncode
            if rc == 0:
                self.after(0, self._log, "\n✔  Done.\n", "success")
            elif rc in (-1, None):
                self.after(0, self._log, "\n⚠  Download cancelled.\n", "warning")
            else:
                self.after(0, self._log, f"\n✖  Exited with code {rc}\n", "error")
        except FileNotFoundError:
            self.after(0, self._log,
                       "\n✖  Executable not found — open Settings (⚙) to set the path.\n", "error")
        except Exception as e:
            self.after(0, self._log, f"\n✖  Error: {e}\n", "error")
        finally:
            self._proc = None
            self.after(0, self._refresh_controls)

    def _cancel_download(self):
        if not self._proc:
            return
        if not messagebox.askyesno("Cancel download",
                                   "Are you sure you want to cancel the download?",
                                   icon="warning"):
            return
        try:
            self._proc.terminate()
            self._log("\n⚠  Cancelling…\n", "warning")
        except Exception as e:
            self._log(f"⚠  Could not cancel: {e}\n", "warning")

    # ── Folder actions ──────────────────────────────────────────────────────────
    def _resolve_folder(self):
        path = self._out_path or (
            self._folder_for(self.show_name_var.get().strip())
            if self.show_name_var.get().strip() else "")
        if not path:
            messagebox.showwarning("No folder", "No output folder is set.")
            return None
        if not os.path.isdir(path):
            messagebox.showwarning("Folder not found", f"Folder does not exist:\n{path}")
            return None
        return path

    def _show_folder(self):
        path = self._resolve_folder()
        if path:
            try:
                subprocess.Popen(["explorer", path])
            except Exception as e:
                self._log(f"⚠  Could not open folder: {e}\n", "warning")

    def _delete_folder(self):
        path = self._resolve_folder()
        if not path or not messagebox.askyesno(
                "Are you sure?",
                f"Permanently delete this folder and ALL its contents?\n\n{path}",
                icon="warning"):
            return
        try:
            shutil.rmtree(path)
            self._out_path = ""
            self._log(f"🗑  Deleted folder: {path}\n", "warning")
        except Exception as e:
            self._log(f"✖  Could not delete folder: {e}\n", "error")

    def _delete_files(self):
        path = self._resolve_folder()
        if not path:
            return
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        if not files:
            return messagebox.showinfo("No files", f"No files found in:\n{path}")
        if not messagebox.askyesno(
                "Are you sure?",
                f"Delete {len(files)} file(s) inside:\n\n{path}\n\nThe folder itself will be kept.",
                icon="warning"):
            return
        errors = []
        for f in files:
            try:
                os.remove(os.path.join(path, f))
            except Exception as e:
                errors.append(f"{f}: {e}")
        if errors:
            self._log("⚠  Some files could not be deleted:\n  " + "\n  ".join(errors) + "\n", "warning")
        else:
            self._log(f"🗂  Deleted {len(files)} file(s) from: {path}\n", "warning")


if __name__ == "__main__":
    App().mainloop()