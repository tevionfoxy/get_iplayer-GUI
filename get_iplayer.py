import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import re
import os

BASE_OUTPUT_DIR = r"P:\Rename\TV\Iplayer"

# BBC iPlayer official colour palette
# Source: BBC iPlayer styleguide
BG          = "#111111"   # dark-gray
CARD        = "#1a1a1a"   # darker-gray
SURFACE     = "#212020"   # another-gray
BORDER      = "#323232"   # battered-gray
INPUT_BG    = "#2E2E2E"   # carousel-gray
INPUT_BD    = "#404040"   # gray
FG          = "#ffffff"   # white
FG_MUT      = "#BDBDBD"   # silver
FG_HINT     = "#808080"   # definition-gray
PINK        = "#f54997"   # iplayer-pink
PINK_ACT    = "#cf3e80"   # not-quite-iplayer-pink
PINK_ON     = "#e92f83"   # onnow-pink
MONO_FG     = "#f54997"   # use pink for path highlight
SUCCESS_FG  = "#4caf79"
ERROR_FG    = "#f47a8a"
WARN_FG     = "#ff9600"   # tangerine

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_MAIN  = os.path.join(SCRIPT_DIR, "get_iplayer.ico")
ICON_PVR   = os.path.join(SCRIPT_DIR, "get_iplayer_pvr.ico")

def sanitize(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("get_iplayer Downloader")
        self.resizable(False, False)
        self.configure(bg=BG)

        # Window icon
        if os.path.exists(ICON_MAIN):
            try:
                self.iconbitmap(ICON_MAIN)
            except Exception:
                pass

        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        PAD = 20

        outer = tk.Frame(self, bg=BG, padx=PAD, pady=PAD)
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=CARD, bd=0,
                        highlightthickness=1, highlightbackground=BORDER,
                        padx=PAD, pady=PAD)
        card.pack(fill="both", expand=True)

        # ── Header ──────────────────────────────────────────────
        hdr = tk.Frame(card, bg=CARD)
        hdr.pack(fill="x", pady=(0, 14))

        # Try to show PVR icon in header
        self._pvr_img = None
        if os.path.exists(ICON_PVR):
            try:
                from PIL import Image, ImageTk
                img = Image.open(ICON_PVR).resize((32, 32), Image.LANCZOS)
                self._pvr_img = ImageTk.PhotoImage(img)
                lbl_icon = tk.Label(hdr, image=self._pvr_img, bg=CARD)
                lbl_icon.pack(side="left", padx=(0, 10))
            except Exception:
                self._pvr_img = None

        if self._pvr_img is None:
            # Fallback: pink play triangle block
            icon_box = tk.Label(hdr, text="▶", bg=PINK, fg=FG,
                                font=("Segoe UI", 13, "bold"),
                                width=3, pady=5)
            icon_box.pack(side="left", padx=(0, 10))

        title_frame = tk.Frame(hdr, bg=CARD)
        title_frame.pack(side="left", anchor="w")
        tk.Label(title_frame, text="get_iplayer", bg=CARD, fg=PINK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(title_frame, text="BBC iPlayer downloader", bg=CARD, fg=FG_HINT,
                 font=("Segoe UI", 9)).pack(anchor="w")

        self._sep(card)

        # ── Show name ───────────────────────────────────────────
        self._label(card, "SHOW NAME")
        self.show_name_var = tk.StringVar()
        self.show_name_var.trace_add("write", self._update_path)
        self._entry(card, self.show_name_var, "e.g. Blue Planet")

        # ── Path display ────────────────────────────────────────
        path_frame = tk.Frame(card, bg=SURFACE,
                              highlightthickness=1, highlightbackground=BORDER)
        path_frame.pack(fill="x", pady=(4, 14))

        tk.Label(path_frame, text="📁", bg=SURFACE, fg=PINK,
                 font=("Segoe UI", 10)).pack(side="left", padx=(8, 4), pady=7)

        self.path_var = tk.StringVar(value=BASE_OUTPUT_DIR + "\\")
        tk.Label(path_frame, textvariable=self.path_var,
                 bg=SURFACE, fg=PINK,
                 font=("Consolas", 10), anchor="w",
                 wraplength=420, justify="left").pack(
                     side="left", pady=7, padx=(0, 8))

        # ── IDs ─────────────────────────────────────────────────
        self._label(card, "SHOW / SEASON / EPISODE IDs  (comma-separated)")
        self.ids_var = tk.StringVar()
        self._entry(card, self.ids_var, "e.g. b09w7fd3, p07qr8bz")

        tk.Frame(card, bg=CARD, height=6).pack()

        # ── Download button ─────────────────────────────────────
        self.dl_btn = tk.Button(
            card, text="⬇  Start download",
            bg=PINK, fg=FG,
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            activebackground=PINK_ACT, activeforeground=FG,
            command=self._start_download
        )
        self.dl_btn.pack(fill="x", ipady=9)

        # ── Reset button ────────────────────────────────────────
        reset_btn = tk.Button(
            card, text="↺   Download another show",
            bg=CARD, fg=FG_MUT,
            font=("Segoe UI", 10),
            relief="flat", cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER,
            activebackground=SURFACE, activeforeground=PINK,
            command=self._reset
        )
        reset_btn.pack(fill="x", ipady=7, pady=(8, 0))

        self._sep(card)

        # ── Output log ──────────────────────────────────────────
        self._label(card, "OUTPUT")

        self.log = scrolledtext.ScrolledText(
            card, height=13, bg="#0d0d0d", fg=FG_MUT,
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

    # ── Helpers ──────────────────────────────────────────────────

    def _sep(self, parent):
        f = tk.Frame(parent, bg=BORDER, height=1)
        f.pack(fill="x", pady=(0, 14))

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

        # Placeholder
        if placeholder:
            def _on_focus_in(event, e=e, ph=placeholder):
                if e.get() == ph:
                    e.delete(0, "end")
                    e.config(fg=FG)
            def _on_focus_out(event, e=e, ph=placeholder, var=var):
                if not e.get():
                    e.insert(0, ph)
                    e.config(fg=FG_HINT)

            e.insert(0, placeholder)
            e.config(fg=FG_HINT)
            e.bind("<FocusIn>",  _on_focus_in)
            e.bind("<FocusOut>", _on_focus_out)

            # Prevent placeholder from being read by var
            orig_get = var.get
            def guarded_get():
                val = orig_get()
                return "" if val == placeholder else val
            var.get = guarded_get

        return e

    def _update_path(self, *_):
        clean = sanitize(self.show_name_var.get())
        self.path_var.set(BASE_OUTPUT_DIR + "\\" + clean)

    def _log(self, text, tag="info"):
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _reset(self):
        self.show_name_var.set("")
        self.ids_var.set("")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.dl_btn.configure(state="normal")

    def _start_download(self):
        show_name = sanitize(self.show_name_var.get().strip())
        show_id   = self.ids_var.get().strip()

        if not show_name:
            self._log("⚠  Please enter a show name.\n", "warning"); return
        if not show_id:
            self._log("⚠  Please enter at least one ID.\n", "warning"); return

        out_path = BASE_OUTPUT_DIR + "\\" + show_name
        cmd = [
            "get_iplayer",
            f"--pid={show_id}",
            "--force",
            "--pid-recursive",
            "--file-prefix=<senum> - <-episodeshort>",
            "-o", out_path,
        ]

        self._log("Command:\n", "info")
        self._log("  " + " ".join(cmd) + "\n\n", "cmd")
        self.dl_btn.configure(state="disabled")

        thread = threading.Thread(target=self._run, args=(cmd,), daemon=True)
        thread.start()

    def _run(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
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
                       "\n✖  get_iplayer not found — check it's on your PATH.\n",
                       "error")
        except Exception as e:
            self.after(0, self._log, f"\n✖  Error: {e}\n", "error")
        finally:
            self.after(0, self.dl_btn.configure, {"state": "normal"})

if __name__ == "__main__":
    app = App()
    app.mainloop()
