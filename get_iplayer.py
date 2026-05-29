import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import re
import sys
import os

BASE_OUTPUT_DIR = r"P:\Rename\TV\Iplayer"

def sanitize(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("get_iplayer Downloader")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")
        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        PAD = 20
        BG        = "#1a1a2e"
        CARD      = "#16213e"
        ACCENT    = "#e94560"
        BORDER    = "#0f3460"
        FG        = "#e0e0e0"
        FG_MUT    = "#8892a4"
        MONO_FG   = "#4db8ff"
        INPUT_BG  = "#0f3460"
        INPUT_BD  = "#1a4a8a"

        outer = tk.Frame(self, bg=BG, padx=PAD, pady=PAD)
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=CARD, bd=0, highlightthickness=1,
                        highlightbackground=BORDER, padx=PAD, pady=PAD)
        card.pack(fill="both", expand=True)

        # --- Header ---
        hdr = tk.Frame(card, bg=CARD)
        hdr.pack(fill="x", pady=(0, 14))

        icon_box = tk.Label(hdr, text="▶", bg=ACCENT, fg="white",
                            font=("Segoe UI", 14, "bold"), width=3, pady=4)
        icon_box.pack(side="left", padx=(0, 12))

        tk.Label(hdr, text="get_iplayer Downloader", bg=CARD, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left", anchor="s")

        ttk.Separator(card, orient="horizontal").pack(fill="x", pady=(0, 16))

        # --- Show name ---
        tk.Label(card, text="SHOW NAME", bg=CARD, fg=FG_MUT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.show_name_var = tk.StringVar()
        self.show_name_var.trace_add("write", self._update_path)
        name_entry = tk.Entry(card, textvariable=self.show_name_var,
                              bg=INPUT_BG, fg=FG, insertbackground=FG,
                              relief="flat", font=("Segoe UI", 11),
                              highlightthickness=1, highlightbackground=INPUT_BD,
                              highlightcolor=ACCENT)
        name_entry.pack(fill="x", ipady=6, pady=(4, 12))

        # --- Path display ---
        path_frame = tk.Frame(card, bg="#0a1628", highlightthickness=1,
                              highlightbackground=BORDER)
        path_frame.pack(fill="x", pady=(0, 14))

        tk.Label(path_frame, text="📁", bg="#0a1628", fg=MONO_FG,
                 font=("Segoe UI", 10)).pack(side="left", padx=(8, 4), pady=6)

        self.path_var = tk.StringVar(value=BASE_OUTPUT_DIR + "\\")
        tk.Label(path_frame, textvariable=self.path_var, bg="#0a1628",
                 fg=MONO_FG, font=("Consolas", 10),
                 wraplength=420, justify="left").pack(
                     side="left", pady=6, padx=(0, 8))

        # --- IDs ---
        tk.Label(card, text="SHOW / SEASON / EPISODE IDs  (comma-separated)",
                 bg=CARD, fg=FG_MUT, font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.ids_var = tk.StringVar()
        ids_entry = tk.Entry(card, textvariable=self.ids_var,
                             bg=INPUT_BG, fg=FG, insertbackground=FG,
                             relief="flat", font=("Segoe UI", 11),
                             highlightthickness=1, highlightbackground=INPUT_BD,
                             highlightcolor=ACCENT)
        ids_entry.pack(fill="x", ipady=6, pady=(4, 16))

        # --- Download button ---
        self.dl_btn = tk.Button(card, text="⬇  Start download",
                                bg=ACCENT, fg="white",
                                font=("Segoe UI", 12, "bold"),
                                relief="flat", cursor="hand2",
                                activebackground="#c73652", activeforeground="white",
                                command=self._start_download)
        self.dl_btn.pack(fill="x", ipady=8)

        # --- Reset button ---
        reset_btn = tk.Button(card, text="↺   Download another show",
                              bg=CARD, fg=FG_MUT,
                              font=("Segoe UI", 10),
                              relief="flat", cursor="hand2",
                              highlightthickness=1, highlightbackground=BORDER,
                              activebackground=BORDER, activeforeground=MONO_FG,
                              command=self._reset)
        reset_btn.pack(fill="x", ipady=6, pady=(8, 0))

        ttk.Separator(card, orient="horizontal").pack(fill="x", pady=(16, 10))

        # --- Output log ---
        tk.Label(card, text="OUTPUT", bg=CARD, fg=FG_MUT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.log = scrolledtext.ScrolledText(
            card, height=12, bg="#0a1628", fg=MONO_FG,
            insertbackground=FG, relief="flat",
            font=("Consolas", 10), wrap="word",
            highlightthickness=1, highlightbackground=BORDER,
            state="disabled"
        )
        self.log.pack(fill="both", expand=True, pady=(4, 0))

        # Tag colours
        self.log.tag_config("info",    foreground=MONO_FG)
        self.log.tag_config("success", foreground="#4caf79")
        self.log.tag_config("error",   foreground="#f47a8a")
        self.log.tag_config("warning", foreground="#f4b84a")
        self.log.tag_config("cmd",     foreground="#c0a0ff")

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
            self._log("⚠  Please enter a show name.\n", "warning")
            return
        if not show_id:
            self._log("⚠  Please enter at least one ID.\n", "warning")
            return

        out_path = BASE_OUTPUT_DIR + "\\" + show_name
        cmd = [
            "get_iplayer",
            f"--pid={show_id}",
            "--force",
            "--pid-recursive",
            '--file-prefix=<senum> - <-episodeshort>',
            f"-o", out_path,
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
                       "\n✖  get_iplayer not found. Make sure it's on your PATH.\n",
                       "error")
        except Exception as e:
            self.after(0, self._log, f"\n✖  Error: {e}\n", "error")
        finally:
            self.after(0, self.dl_btn.configure, {"state": "normal"})

if __name__ == "__main__":
    app = App()
    app.mainloop()
