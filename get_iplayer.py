import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
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
    for name in ["get_iplayer.cmd", "get_iplayer.bat", "get_iplayer.exe", "get_iplayer.pl"]:
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


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Settings")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if os.path.exists(ICON_MAIN):
            try:
                self.iconbitmap(ICON_MAIN)
            except Exception:
                pass

        outer = tk.Frame(self, bg=BG, padx=20, pady=20)
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=CARD, bd=0,
                        highlightthickness=1, highlightbackground=BORDER,
                        padx=20, pady=20)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="SETTINGS", bg=CARD, fg=PINK,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 12))

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))

        # Exe path
        tk.Label(card, text="get_iplayer EXECUTABLE", bg=CARD, fg=FG_HINT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(card, text="Path to get_iplayer.cmd / .bat / .exe",
                 bg=CARD, fg=FG_HINT, font=("Segoe UI", 8)).pack(anchor="w", pady=(1, 4))

        exe_row = tk.Frame(card, bg=CARD)
        exe_row.pack(fill="x", pady=(0, 4))

        self.exe_var = tk.StringVar(value=parent.exe_path)
        tk.Entry(exe_row, textvariable=self.exe_var,
                 bg=INPUT_BG, fg=FG_MUT, insertbackground=FG,
                 relief="flat", font=("Consolas", 10),
                 highlightthickness=1, highlightbackground=INPUT_BD,
                 highlightcolor=PINK).pack(side="left", fill="x", expand=True, ipady=7)

        tk.Button(exe_row, text="🔍 Browse",
                  bg=SURFACE, fg=FG_MUT, font=("Segoe UI", 9),
                  relief="flat", cursor="hand2",
                  activebackground=BORDER, activeforeground=FG,
                  highlightthickness=1, highlightbackground=BORDER,
                  command=self._browse_exe
                  ).pack(side="left", padx=(6, 0), ipady=7, ipadx=6)

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=(16, 12))

        # Save / Close buttons
        btn_row = tk.Frame(card, bg=CARD)
        btn_row.pack(fill="x")

        tk.Button(btn_row, text="Save",
                  bg=PINK, fg=FG, font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  activebackground=PINK_ACT, activeforeground=FG,
                  command=self._save).pack(side="left", fill="x", expand=True, ipady=7)

        tk.Frame(btn_row, bg=BORDER, width=1).pack(side="left", fill="y", padx=6)

        tk.Button(btn_row, text="Close",
                  bg=SURFACE, fg=FG_MUT, font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  highlightthickness=1, highlightbackground=BORDER,
                  activebackground=BORDER, activeforeground=FG,
                  command=self.destroy).pack(side="left", fill="x", expand=True, ipady=7)

        self.update_idletasks()
        pw, ph = parent.winfo_x(), parent.winfo_y()
        pw2, ph2 = parent.winfo_width(), parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"{max(w,420)}x{h}+{pw + (pw2-max(w,420))//2}+{ph + (ph2-h)//2}")

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
        self.parent.exe_var_store = exe
        self.parent.settings["exe_path"] = exe
        save_settings(self.parent.settings)
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("get_iplayer Downloader")
        self.resizable(True, True)
        self.configure(bg=BG)

        self.settings    = load_settings()
        self.save_base   = self.settings.get("save_path", DEFAULT_SAVE_PATH)
        self.exe_path    = self.settings.get("exe_path", "") or find_get_iplayer() or ""
        self.exe_var_store = self.exe_path  # kept in sync by settings window

        self._proc     = None
        self._out_path = ""

        if os.path.exists(ICON_MAIN):
            try:
                self.iconbitmap(ICON_MAIN)
            except Exception:
                pass

        self._build_ui()
        self._center()
        self._refresh_controls()

        if not self.exe_path:
            self.after(300, self._warn_no_exe)

    def _center(self):
        self.update_idletasks()
        w, h = 560, 780
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        PAD = 20
        outer = tk.Frame(self, bg=BG, padx=PAD)
        outer.pack(fill="both", expand=True, padx=0, pady=(PAD, PAD))

        card = tk.Frame(outer, bg=CARD, bd=0,
                        highlightthickness=1, highlightbackground=BORDER,
                        padx=PAD)
        card.pack(fill="both", expand=True)
        card.columnconfigure(0, weight=1)

        self._build_header(card)
        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))

        # Save location
        self._label(card, "SAVE LOCATION")
        path_row = tk.Frame(card, bg=CARD)
        path_row.pack(fill="x", pady=(3, 8))
        self.save_path_var = tk.StringVar(value=self.save_base)
        tk.Entry(path_row, textvariable=self.save_path_var,
                 bg=INPUT_BG, fg=PINK, insertbackground=FG,
                 relief="flat", font=("Consolas", 10),
                 highlightthickness=1, highlightbackground=INPUT_BD,
                 highlightcolor=PINK).pack(side="left", fill="x", expand=True, ipady=7)
        self._small_btn(path_row, "📁 Browse", self._browse_save_path)

        # Show name
        self._label(card, "SHOW NAME")
        self.show_name_var = tk.StringVar()
        self._entry(card, self.show_name_var, "e.g. Blue Planet")

        # Output path preview
        preview = tk.Frame(card, bg=SURFACE,
                           highlightthickness=1, highlightbackground=BORDER)
        preview.pack(fill="x", pady=(0, 8))
        tk.Label(preview, text="→", bg=SURFACE, fg=FG_HINT,
                 font=("Segoe UI", 10)).pack(side="left", padx=(10, 4), pady=6)
        self.output_path_var = tk.StringVar(value=self.save_base + "\\")
        # Add all traces here, after output_path_var exists
        self.save_path_var.trace_add("write", self._on_save_path_changed)
        self.show_name_var.trace_add("write", self._update_output_path)
        tk.Label(preview, textvariable=self.output_path_var,
                 bg=SURFACE, fg=PINK, font=("Consolas", 10), anchor="w",
                 wraplength=390, justify="left").pack(side="left", pady=6, padx=(0, 8))

        # IDs
        self._label(card, "SHOW / SEASON / EPISODE IDs  (comma-separated)")
        self.ids_var = tk.StringVar()
        self._entry(card, self.ids_var, "e.g. b09w7fd3, p07qr8bz")

        # ── Start / Cancel ────────────────────────────────────────────────────
        action_row = tk.Frame(card, bg=CARD)
        action_row.pack(fill="x")

        self.dl_btn = tk.Button(
            action_row, text="⬇  Start",
            bg=PINK, fg=FG, font=("Segoe UI", 11, "bold"),
            relief="flat", cursor="hand2",
            activebackground=PINK_ACT, activeforeground=FG,
            command=self._start_download)
        self.dl_btn.pack(side="left", fill="x", expand=True, ipady=8)

        tk.Frame(action_row, bg=BORDER, width=1).pack(side="left", fill="y", padx=4)

        self.cancel_btn = tk.Button(
            action_row, text="✖  Cancel",
            bg=SURFACE, fg=ERROR_FG,
            font=("Segoe UI", 11, "bold"),
            relief="flat", cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER,
            activebackground=BORDER, activeforeground=ERROR_FG,
            command=self._cancel_download)
        self.cancel_btn.pack(side="left", fill="x", expand=True, ipady=8)

        # ── Folder actions ────────────────────────────────────────────────────
        self._sep_top(card)
        self._label(card, "FOLDER ACTIONS")

        tk.Button(
            card, text="📂  Show folder",
            bg=SURFACE, fg=FG_MUT, font=("Segoe UI", 10),
            relief="flat", cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER,
            activebackground=BORDER, activeforeground=FG,
            command=self._show_folder
        ).pack(fill="x", pady=(6, 4), ipady=7)

        folder_row = tk.Frame(card, bg=CARD)
        folder_row.pack(fill="x")

        self.del_folder_btn = tk.Button(
            folder_row, text="🗑  Delete folder",
            bg=SURFACE, fg=ERROR_FG, font=("Segoe UI", 10),
            relief="flat", cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER,
            activebackground=BORDER, activeforeground=ERROR_FG,
            command=self._delete_folder)
        self.del_folder_btn.pack(side="left", fill="x", expand=True, ipady=7)

        tk.Frame(folder_row, bg=BORDER, width=1).pack(side="left", fill="y", padx=4)

        self.del_files_btn = tk.Button(
            folder_row, text="🗂  Delete files only",
            bg=SURFACE, fg=WARN_FG, font=("Segoe UI", 10),
            relief="flat", cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER,
            activebackground=BORDER, activeforeground=WARN_FG,
            command=self._delete_files)
        self.del_files_btn.pack(side="left", fill="x", expand=True, ipady=7)

        # ── Reset ─────────────────────────────────────────────────────────────
        self._sep_top(card)
        tk.Button(
            card, text="↺   Download another show",
            bg=CARD, fg=FG_MUT, font=("Segoe UI", 10),
            relief="flat", cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER,
            activebackground=SURFACE, activeforeground=PINK,
            command=self._reset
        ).pack(fill="x", ipady=7)

        self._sep(card)

        # ── Output log ────────────────────────────────────────────────────────
        self._label(card, "OUTPUT")
        self.log = scrolledtext.ScrolledText(
            card, height=6, bg="#0d0d0d", fg=FG_MUT,
            insertbackground=FG, relief="flat",
            font=("Consolas", 10), wrap="word",
            highlightthickness=1, highlightbackground=BORDER,
            state="disabled")
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        outer.pack_propagate(False)
        self.log.tag_config("info",    foreground=FG_MUT)
        self.log.tag_config("cmd",     foreground=PINK)
        self.log.tag_config("success", foreground=SUCCESS_FG)
        self.log.tag_config("error",   foreground=ERROR_FG)
        self.log.tag_config("warning", foreground=WARN_FG)

    def _build_header(self, parent):
        hdr = tk.Frame(parent, bg=CARD)
        hdr.pack(fill="x", pady=(6, 0))

        # Gear — right side
        tk.Button(hdr, text="⚙",
                  bg=CARD, fg=FG_HINT, font=("Segoe UI", 11),
                  relief="flat", cursor="hand2", bd=0,
                  activebackground=SURFACE, activeforeground=FG,
                  command=self._open_settings
                  ).pack(side="right", pady=8)

        # .ico icon — try PIL first, then tkinter's native BitmapImage on Windows
        self._pvr_img = None
        for ico_path in [ICON_MAIN, ICON_PVR]:
            if not os.path.exists(ico_path):
                continue
            # Method 1: PIL/Pillow
            try:
                from PIL import Image, ImageTk
                ico = Image.open(ico_path)
                best = None
                for frame in range(getattr(ico, 'n_frames', 1)):
                    ico.seek(frame)
                    if best is None or ico.size[0] > best.size[0]:
                        best = ico.copy()
                img = best.resize((50, 50), Image.LANCZOS).convert("RGBA")
                self._pvr_img = ImageTk.PhotoImage(img)
                break
            except Exception:
                pass
            # Method 2: extract PNG from ico using struct (no deps)
            try:
                import struct, io
                with open(ico_path, 'rb') as f:
                    f.read(4)  # reserved + type
                    count = struct.unpack_from('<H', f.read(2))[0]
                    entries = []
                    for _ in range(count):
                        data = f.read(16)
                        w = struct.unpack_from('B', data, 0)[0] or 256
                        offset = struct.unpack_from('<I', data, 12)[0]
                        size   = struct.unpack_from('<I', data, 8)[0]
                        entries.append((w, offset, size))
                    entries.sort(key=lambda x: x[0], reverse=True)
                    w, offset, size = entries[0]
                    f.seek(offset)
                    raw = f.read(size)
                # PNG frames start with PNG magic bytes
                if raw[:8] == b'\x89PNG\r\n\x1a\n':
                    self._pvr_img = tk.PhotoImage(data=raw)
                    # Scale down to ~50px using subsample
                    s = max(1, self._pvr_img.width() // 50)
                    self._pvr_img = self._pvr_img.subsample(s, s)
                    break
            except Exception:
                pass

        if self._pvr_img:
            tk.Label(hdr, image=self._pvr_img, bg=CARD, bd=0
                     ).pack(side="left", padx=(0, 10), pady=6)

        # Single-line title centred on icon
        text_frame = tk.Frame(hdr, bg=CARD)
        text_frame.pack(side="left", anchor="center")
        title = tk.Frame(text_frame, bg=CARD)
        title.pack(anchor="w")
        tk.Label(title, text="get_iplayer",
                 bg=CARD, fg=PINK,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(title, text="  —  BBC iPlayer downloader",
                 bg=CARD, fg=FG_HINT,
                 font=("Segoe UI", 10)).pack(side="left")

    # ── Widget helpers ────────────────────────────────────────────────────────

    def _sep(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(8, 8))

    def _sep_top(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(8, 0))

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=CARD, fg=FG_HINT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

    def _small_btn(self, parent, text, cmd):
        tk.Button(parent, text=text, bg=SURFACE, fg=FG_MUT,
                  font=("Segoe UI", 9), relief="flat", cursor="hand2",
                  activebackground=BORDER, activeforeground=FG,
                  highlightthickness=1, highlightbackground=BORDER,
                  command=cmd).pack(side="left", padx=(6, 0), ipady=7, ipadx=6)

    def _entry(self, parent, var, placeholder=""):
        e = tk.Entry(parent, textvariable=var,
                     bg=INPUT_BG, fg=FG, insertbackground=FG,
                     relief="flat", font=("Segoe UI", 11),
                     highlightthickness=1, highlightbackground=INPUT_BD,
                     highlightcolor=PINK)
        e.pack(fill="x", ipady=6, pady=(3, 8))
        if placeholder:
            def _fi(ev, e=e, ph=placeholder):
                if e.get() == ph:
                    e.delete(0, "end"); e.config(fg=FG)
            def _fo(ev, e=e, ph=placeholder):
                if not e.get():
                    e.insert(0, ph); e.config(fg=FG_HINT)
            e.insert(0, placeholder); e.config(fg=FG_HINT)
            e.bind("<FocusIn>", _fi); e.bind("<FocusOut>", _fo)
            orig = var.get
            var.get = lambda ph=placeholder, orig=orig: ("" if orig() == ph else orig())
        return e

    def _log(self, text, tag="info"):
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    # ── Control state ─────────────────────────────────────────────────────────

    def _refresh_controls(self):
        running = self._proc is not None
        self.dl_btn.configure(state="disabled" if running else "normal")
        self.cancel_btn.configure(state="normal" if running else "disabled")

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsWindow(self)

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_save_path_changed(self, *_):
        self.save_base = self.save_path_var.get()
        self._update_output_path()
        self.settings["save_path"] = self.save_base
        save_settings(self.settings)

    def _update_output_path(self, *_):
        clean = sanitize(self.show_name_var.get())
        self.output_path_var.set(self.save_base.rstrip("\\") + "\\" + clean)

    def _browse_save_path(self):
        chosen = filedialog.askdirectory(
            title="Choose default save folder",
            initialdir=self.save_base if os.path.isdir(self.save_base) else "/")
        if chosen:
            self.save_path_var.set(os.path.normpath(chosen))

    def _warn_no_exe(self):
        self._log(
            "⚠  get_iplayer not found automatically.\n"
            "   Open Settings (⚙) to set the path to the executable.\n\n",
            "warning")

    def _reset(self):
        self.show_name_var.set("")
        self.ids_var.set("")
        self._out_path = ""
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._refresh_controls()

    # ── Download ──────────────────────────────────────────────────────────────

    def _start_download(self):
        show_name = sanitize(self.show_name_var.get().strip())
        show_id   = self.ids_var.get().strip()

        if not show_name:
            self._log("⚠  Please enter a show name.\n", "warning"); return
        if not show_id:
            self._log("⚠  Please enter at least one ID.\n", "warning"); return

        exe = self.exe_path or self.exe_var_store or find_get_iplayer()
        if not exe:
            self._log("✖  Cannot find get_iplayer.\n"
                      "   Open Settings (⚙) to set the path.\n", "error"); return

        self._out_path = self.save_base.rstrip("\\") + "\\" + show_name
        cmd = [exe, f"--pid={show_id}", "--force", "--pid-recursive",
               "--file-prefix=<senum> - <-episodeshort>", "-o", self._out_path]

        self._log("Command:\n", "info")
        self._log("  " + " ".join(f'"{c}"' if " " in c else c for c in cmd) + "\n\n", "cmd")
        self._refresh_controls()

        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()

    def _run(self, cmd):
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, shell=False)
            for line in self._proc.stdout:
                self.after(0, self._log, line, "info")
            self._proc.wait()
            rc = self._proc.returncode
            if rc == 0:
                self.after(0, self._log, "\n✔  Done.\n", "success")
            elif rc == -1 or rc is None:
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

    # ── Cancel ────────────────────────────────────────────────────────────────

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

    # ── Folder actions ────────────────────────────────────────────────────────

    def _resolve_folder(self):
        path = self._out_path
        if not path:
            name = sanitize(self.show_name_var.get().strip())
            path = self.save_base.rstrip("\\") + "\\" + name if name else ""
        if not path:
            messagebox.showwarning("No folder", "No output folder is set.")
            return None
        if not os.path.isdir(path):
            messagebox.showwarning("Folder not found", f"Folder does not exist:\n{path}")
            return None
        return path

    def _show_folder(self):
        path = self._resolve_folder()
        if not path:
            return
        try:
            subprocess.Popen(["explorer", path])
        except Exception as e:
            self._log(f"⚠  Could not open folder: {e}\n", "warning")

    def _delete_folder(self):
        path = self._resolve_folder()
        if not path:
            return
        if not messagebox.askyesno("Are you sure?",
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
            messagebox.showinfo("No files", f"No files found in:\n{path}")
            return
        if not messagebox.askyesno("Are you sure?",
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
            self._log("⚠  Some files could not be deleted:\n  " +
                      "\n  ".join(errors) + "\n", "warning")
        else:
            self._log(f"🗂  Deleted {len(files)} file(s) from: {path}\n", "warning")


if __name__ == "__main__":
    app = App()
    app.mainloop()