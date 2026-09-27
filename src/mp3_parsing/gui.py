"""
gui.py - the desktop window (tkinter): pick one or more files, convert
them one at a time with a live progress bar, stop immediately at the
first error rather than skipping past it silently.

tkinter is only imported inside launch_gui(), never at module load time.
That matters: this project's own test suite (and this bridge sandbox)
runs on a machine with ffmpeg but no tkinter installed, and importing
tkinter at the top of this file would make `import mp3_parsing` itself
fail there, breaking every test regardless of whether the GUI is ever
opened. Keeping the import inside the function means this module only
needs tkinter at the moment someone actually calls launch_gui().
"""
import os

from .config import OUTPUT_DIR
from .converter import convert_to_mp3
from .progress import format_duration


def launch_gui() -> None:
    """
    Small desktop window (tkinter, ships with Python - nothing extra to
    install) for picking one or more files and converting them without
    touching the command line. Errors stop the whole batch at the file
    that failed rather than skipping past it, so a bad file doesn't get
    silently ignored while the rest run - the same "stop on first error"
    behavior as the CLI path (a raised RuntimeError there also aborts
    immediately, it just does so via sys.exit instead of a dialog).

    A determinate progress bar plus a label showing percent, ffmpeg's
    encode speed, elapsed time, and estimated time remaining (ETA) update
    live while each file converts, driven by convert_to_mp3()'s
    progress_callback.
    """
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    root = tk.Tk()
    root.title("mp3_parsing - Convert video/audio to MP3")
    root.geometry("560x480")
    root.resizable(False, False)

    selected_files: list = []

    tk.Label(
        root,
        text="Choose one or more video/audio files (.mp4, .wav), then click Convert.",
        wraplength=520, justify="left",
    ).pack(padx=12, pady=(12, 4), anchor="w")

    files_frame = tk.Frame(root)
    files_frame.pack(padx=12, pady=4, fill="both", expand=False)
    files_listbox = tk.Listbox(files_frame, height=6)
    files_listbox.pack(side="left", fill="both", expand=True)
    files_scrollbar = tk.Scrollbar(files_frame, command=files_listbox.yview)
    files_scrollbar.pack(side="right", fill="y")
    files_listbox.config(yscrollcommand=files_scrollbar.set)

    button_row = tk.Frame(root)
    button_row.pack(padx=12, pady=6, fill="x")

    status_var = tk.StringVar(value=f"Output folder: {OUTPUT_DIR}")
    status_label = tk.Label(root, textvariable=status_var, anchor="w", fg="#555555")
    status_label.pack(padx=12, pady=(0, 4), fill="x")

    progress_bar = ttk.Progressbar(root, orient="horizontal", mode="determinate", maximum=100)
    progress_bar.pack(padx=12, pady=(0, 2), fill="x")

    progress_label_var = tk.StringVar(value="")
    progress_label = tk.Label(root, textvariable=progress_label_var, anchor="w", fg="#555555")
    progress_label.pack(padx=12, pady=(0, 4), fill="x")

    log_box = scrolledtext.ScrolledText(root, height=9, state="normal")
    log_box.pack(padx=12, pady=(0, 12), fill="both", expand=True)

    def choose_files() -> None:
        paths = filedialog.askopenfilenames(
            title="Choose video/audio files",
            filetypes=[("Video/Audio", "*.mp4 *.wav"), ("All files", "*.*")],
        )
        if not paths:
            return
        selected_files.clear()
        selected_files.extend(paths)
        files_listbox.delete(0, tk.END)
        for path in paths:
            files_listbox.insert(tk.END, os.path.basename(path))
        status_var.set(f"Selected {len(paths)} file(s). Output folder: {OUTPUT_DIR}")

    def make_progress_callback(filename: str):
        def _callback(percent: float, speed: str, elapsed: float, eta) -> None:
            progress_bar["value"] = percent
            progress_label_var.set(
                f"{filename}: {percent:.1f}% ({speed} speed) - "
                f"elapsed {format_duration(elapsed)}, ETA {format_duration(eta)}"
            )
            root.update_idletasks()
        return _callback

    def convert_selected() -> None:
        if not selected_files:
            messagebox.showwarning("No files selected", "Please choose at least one video/audio file first.")
            return

        convert_button.config(state=tk.DISABLED)
        choose_button.config(state=tk.DISABLED)
        log_box.delete("1.0", tk.END)

        converted = 0
        for path in selected_files:
            filename = os.path.basename(path)
            log_box.insert(tk.END, f"Converting: {filename}...\n")
            log_box.see(tk.END)
            progress_bar["value"] = 0
            progress_label_var.set(f"{filename}: 0.0% - elapsed 0:00, ETA --:--")
            root.update_idletasks()
            try:
                output_path = convert_to_mp3(path, progress_callback=make_progress_callback(filename))
            except RuntimeError as exc:
                log_box.insert(tk.END, f"  -> Error: {exc}\n")
                log_box.insert(tk.END, "Stopped due to an error (remaining files were not processed).\n")
                log_box.see(tk.END)
                messagebox.showerror("Conversion error", f"{filename}:\n{exc}")
                convert_button.config(state=tk.NORMAL)
                choose_button.config(state=tk.NORMAL)
                return
            log_box.insert(tk.END, f"  -> Done: {output_path}\n")
            log_box.see(tk.END)
            converted += 1

        progress_bar["value"] = 100
        progress_label_var.set("")
        log_box.insert(tk.END, f"\nFinished: {converted}/{len(selected_files)} file(s).\n")
        messagebox.showinfo("Finished", f"Converted {converted} file(s).\nSaved to: {OUTPUT_DIR}")
        convert_button.config(state=tk.NORMAL)
        choose_button.config(state=tk.NORMAL)

    choose_button = tk.Button(button_row, text="Choose files...", command=choose_files)
    choose_button.pack(side="left")
    convert_button = tk.Button(button_row, text="Convert", command=convert_selected)
    convert_button.pack(side="left", padx=8)

    root.mainloop()
