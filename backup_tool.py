import os
import queue
import threading
import zipfile
import time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

IGNORED = {".git", "node_modules", "__pycache__", ".venv"}
MAX_BACKUPS = 3   


def get_all_files(src):
    out = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in IGNORED]
        for f in files:
            out.append(os.path.join(root, f))
    return out


def check_path(child, parent):
    child = os.path.abspath(child)
    parent = os.path.abspath(parent)
    try:
        return os.path.commonpath([child, parent]) == parent
    except:
        return False


def backup_worker(src, dest, q):
    print("DEBUG: backup started ->", src)  
    try:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_path = os.path.join(dest, f"backup_{ts}.zip")
        skipped = 0

        q.put(("log", f"Scanning: {src}"))
        files = get_all_files(src)
        total = len(files)

        if total == 0:
            q.put(("err", "Folder is empty, nothing to backup"))
            return

        q.put(("log", f"Found {total} files, zipping..."))

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, f in enumerate(files, 1):
                try:
                    rel = os.path.relpath(f, src)
                    zf.write(f, rel)
                except:
                    skipped += 1
                q.put(("prog", i, total))

        q.put(("log", "Verifying archive..."))
        with zipfile.ZipFile(zip_path) as zf:
            bad = zf.testzip()
        if bad:
            q.put(("err", f"Corrupt entry in zip: {bad}"))
            return

        q.put(("log", f"Done -> {zip_path}"))

        cleanup(dest, q)

        q.put(("finish", zip_path, total - skipped, skipped))

    except Exception as e:
        q.put(("err", str(e)))


def cleanup(dest, q):
    try:
        baks = sorted([f for f in os.listdir(dest)
                       if f.startswith("backup_") and f.endswith(".zip")])
    except:
        return

    if len(baks) <= MAX_BACKUPS:
        return

    for name in baks[:-MAX_BACKUPS]:
        try:
            os.remove(os.path.join(dest, name))
            q.put(("log", f"Removed old: {name}"))
        except:
            pass   


def restore_worker(zip_p, dest_p, q):
    print("DEBUG: restore started")   
    try:
        q.put(("log", f"Opening: {zip_p}"))
        with zipfile.ZipFile(zip_p) as zf:
            items = zf.namelist()
            total = len(items)
            if total == 0:
                q.put(("rerr", "Zip is empty!"))
                return

            dest_abs = os.path.abspath(dest_p)
            count = 0

            for i, item in enumerate(items, 1):
                target = os.path.join(dest_abs, item)
                if not check_path(target, dest_abs):
                    q.put(("log", f"Skipped unsafe: {item}"))
                    q.put(("prog", i, total))
                    continue
                zf.extract(item, dest_abs)
                count += 1
                q.put(("prog", i, total))

        q.put(("log", f"Restored to: {dest_p}"))
        q.put(("rfinish", dest_p, count))

    except Exception as e:
        q.put(("rerr", str(e)))


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.busy = False
        self.last_run = None   

        root.title("Backup Tool")
        root.geometry("600x650")  
        root.resizable(False, False)

        ttk.Style().theme_use("clam")

        main = ttk.Frame(root, padding="20")
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Backup Utility",
                  font=("Arial", 14, "bold")).pack(pady=(0, 5))
        ttk.Label(main, text="local project archiver",
                  font=("Arial", 9)).pack(pady=(0, 15))

        f1 = ttk.Frame(main)
        f1.pack(fill="x", pady=5)
        ttk.Label(f1, text="Source:").pack(anchor="w")
        r1 = ttk.Frame(f1)
        r1.pack(fill="x", pady=3)
        self.src_e = ttk.Entry(r1)
        self.src_e.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(r1, text="Browse",
                   command=lambda: self.pick_dir(self.src_e)).pack(side="right")

        f2 = ttk.Frame(main)
        f2.pack(fill="x", pady=5)
        ttk.Label(f2, text="Destination:").pack(anchor="w")
        r2 = ttk.Frame(f2)
        r2.pack(fill="x", pady=3)
        self.dst_e = ttk.Entry(r2)
        self.dst_e.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(r2, text="Browse",
                   command=lambda: self.pick_dir(self.dst_e)).pack(side="right")

        f3 = ttk.Frame(main)
        f3.pack(fill="x", pady=10)
        self.auto_v = tk.BooleanVar(value=False)
        ttk.Checkbutton(f3, text="Auto backup every",
                        variable=self.auto_v).pack(side="left")
        self.mins_v = tk.StringVar(value="30")
        ttk.Entry(f3, textvariable=self.mins_v, width=5).pack(side="left", padx=5)
        ttk.Label(f3, text="min (while app is open)").pack(side="left")

        f4 = ttk.Frame(main)
        f4.pack(fill="x", pady=10)
        self.b_back = ttk.Button(f4, text="Backup", command=self.do_backup)
        self.b_back.pack(side="left", fill="x", expand=True, padx=2)
        self.b_res = ttk.Button(f4, text="Restore...", command=self.do_restore)
        self.b_res.pack(side="right", fill="x", expand=True, padx=2)

        self.bar = ttk.Progressbar(main, orient="horizontal",
                                   length=100, mode="determinate")
        self.bar.pack(fill="x", pady=5)

        f5 = ttk.Frame(main)
        f5.pack(fill="both", expand=True, pady=5)
        ttk.Label(f5, text="Log:").pack(anchor="w")

        self.log = tk.Text(f5, height=8, bg="#2b2b2b", fg="#e0e0e0",
                           font=("Consolas", 9))
        self.log.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(f5, orient="vertical", command=self.log.yview)
        sb.pack(side="right", fill="y")
        self.log.config(yscrollcommand=sb.set)

        self.status = ttk.Label(main, text="Ready", font=("Arial", 9))
        self.status.pack(anchor="w", pady=5)

        self.root.after(1000, self.auto_loop)

    def pick_dir(self, e):
        d = filedialog.askdirectory()
        if d:
            e.delete(0, tk.END)
            e.insert(0, d)

    def add_log(self, txt):
        self.log.insert(tk.END, txt + "\n")
        self.log.see(tk.END)

    def lock_ui(self, lock):
        self.busy = lock
        s = "disabled" if lock else "normal"
        self.b_back.config(state=s)
        self.b_res.config(state=s)

    def do_backup(self):
        if self.busy:
            return
        src = self.src_e.get().strip()
        dst = self.dst_e.get().strip()

        if not src or not dst:
            messagebox.showerror("Error", "Pick both folders first!")
            return
        if not os.path.isdir(src) or not os.path.isdir(dst):
            messagebox.showerror("Error", "One of the paths doesn't exist!")
            return
        if check_path(dst, src):
            messagebox.showerror("Error", "Dest can't be inside source!")
            return

        self.log.delete("1.0", tk.END)
        self.lock_ui(True)
        self.bar["value"] = 0
        self.status.config(text="Backing up...")

        threading.Thread(target=backup_worker,
                         args=(src, dst, self.q), daemon=True).start()
        self.root.after(100, self.check_queue)

    def do_restore(self):
        if self.busy:
            return

        z = filedialog.askopenfilename(title="Pick a backup zip",
                                       filetypes=[("ZIP", "*.zip")])
        if not z:
            return

        d = filedialog.askdirectory(title="Where to restore?")
        if not d:
            return

        if not messagebox.askyesno("Confirm",
                f"Extract to:\n{d}\n\nExisting files may be overwritten. OK?"):
            return

        self.log.delete("1.0", tk.END)
        self.lock_ui(True)
        self.bar["value"] = 0
        self.status.config(text="Restoring...")

        threading.Thread(target=restore_worker,
                         args=(z, d, self.q), daemon=True).start()
        self.root.after(100, self.check_queue)

    def auto_loop(self):
        if self.auto_v.get() and not self.busy:
            s = self.src_e.get().strip()
            d = self.dst_e.get().strip()
            try:
                m = float(self.mins_v.get())
            except:
                m = 0

            ok = s and d and os.path.isdir(s) and os.path.isdir(d) and not check_path(d, s)
            if m > 0 and ok:
                due = self.last_run is None or (time.time() - self.last_run) >= (m * 60)
                if due:
                    self.add_log("Auto backup triggered...")
                    self.do_backup()

        self.root.after(1000, self.auto_loop)

    def check_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                t = msg[0]

                if t == "log":
                    self.add_log(msg[1])
                elif t == "prog":
                    _, cur, tot = msg
                    self.bar["value"] = (cur / tot) * 100
                    self.status.config(text=f"File {cur}/{tot}")
                elif t == "finish":
                    _, path, ok, sk = msg
                    self.last_run = time.time()
                    self.lock_ui(False)
                    self.add_log(f"Done. ok={ok}, skipped={sk}")
                    messagebox.showinfo("Done", f"Backup created:\n{path}")
                    return
                elif t == "rfinish":
                    _, path, n = msg
                    self.lock_ui(False)
                    self.add_log(f"Restore done. files={n}")
                    messagebox.showinfo("Done", f"Restored to:\n{path}")
                    return
                elif t in ("err", "rerr"):
                    self.lock_ui(False)
                    self.add_log(f"ERROR: {msg[1]}")
                    messagebox.showerror("Error", msg[1])
                    return
        except queue.Empty:
            pass

        self.root.after(100, self.check_queue)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()