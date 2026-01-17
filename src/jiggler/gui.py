import tkinter as tk
from tkinter import ttk, messagebox
from typing import Tuple, Optional
import logging
from .logger import Logger
from .core import InputJiggler
import time
import threading

class JigglerGUI:
    def __init__(self, jiggler: InputJiggler):
        self.j = jiggler
        # Find any FileHandler to get log file path
        log_file = None
        for handler in self.j.log.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                log_file = handler.baseFilename
                break
        # Reinitialize Logger with GUI callback, preserving existing log file and silent setting
        self.j.log = Logger(log_file=log_file,
                            silent=not any(isinstance(h, logging.StreamHandler) for h in self.j.log.logger.handlers),
                            gui_log_callback=self._update_log)
        self.root = tk.Tk()
        self.root.title("Input Jiggler v1.1")
        self.root.geometry("440x600")
        self.root.resizable(False, False)
        self._build()
        self._tick()

    def _build(self):
        pad = {"padx": 10, "pady": 6}
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Input Jiggler Control", font=("Segoe UI", 14, "bold")).pack(**pad)
        self.var_mouse = tk.BooleanVar(value=True)
        self.var_keyboard = tk.BooleanVar(value=True)
        self.var_random = tk.BooleanVar(value=self.j.random_mode)
        row1 = ttk.Frame(frame); row1.pack(anchor="w", **pad)
        ttk.Checkbutton(row1, text="Simulate Mouse", variable=self.var_mouse).pack(side="left", padx=6)
        ttk.Checkbutton(row1, text="Simulate Keyboard", variable=self.var_keyboard).pack(side="left", padx=6)
        ttk.Checkbutton(row1, text="Random Mode", variable=self.var_random).pack(side="left", padx=6)
        row2 = ttk.Frame(frame); row2.pack(anchor="w", **pad)
        ttk.Label(row2, text="Intensity:").pack(side="left")
        self.var_intensity = tk.StringVar(value="medium")
        ttk.OptionMenu(row2, self.var_intensity, "medium", "low", "medium", "high").pack(side="left", padx=6)
        row3 = ttk.Frame(frame); row3.pack(anchor="w", **pad)
        ttk.Label(row3, text="Custom Keys (,):").pack(side="left")
        self.ent_keys = ttk.Entry(row3, width=28)
        self.ent_keys.insert(0, ",".join(self.j.custom_keys))
        self.ent_keys.pack(side="left", padx=6)
        row4 = ttk.Frame(frame); row4.pack(anchor="w", **pad)
        ttk.Label(row4, text="Record Duration (s, optional):").pack(side="left")
        self.var_dur = tk.StringVar(value="")
        ttk.Entry(row4, textvariable=self.var_dur, width=10).pack(side="left", padx=6)
        ttk.Button(frame, text="Start Recording", command=self._start_recording).pack(fill="x", **pad)
        ttk.Button(frame, text="Start Simulation", command=self._start_sim).pack(fill="x", **pad)
        ttk.Button(frame, text="Pause/Resume", command=self._toggle_pause).pack(fill="x", **pad)
        ttk.Button(frame, text="Stop Simulation", command=self._stop_sim).pack(fill="x", **pad)
        ttk.Button(frame, text="Help", command=self._show_help).pack(fill="x", **pad)
        self.lbl_status = ttk.Label(frame, text="Status: Idle")
        self.lbl_status.pack(**pad)
        self.lbl_stats = ttk.Label(frame, text="Stats: No activity")
        self.lbl_stats.pack(**pad)
        ttk.Label(frame, text="Recent Logs:").pack(anchor="w", **pad)
        self.log_text = tk.Text(frame, height=8, width=50, state='disabled')
        self.log_text.pack(fill="x", **pad)
        self.log_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        self.log_text['yscrollcommand'] = self.log_scroll.set
        self.log_scroll.pack(side="right", fill="y")
        backend_info = f"Mouse: {type(self.j.mouse_backend).__name__} | Keyboard: {type(self.j.keyboard_backend).__name__}"
        ttk.Label(frame, text=backend_info).pack(**pad)

    def _update_log(self, msg: str):
        self.root.after(0, lambda: self._do_update_log(msg))

    def _do_update_log(self, msg: str):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')}: {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def _update_stats(self, mouse_pos: Tuple[int, int] = None, last_key: str = None):
        stats = []
        if mouse_pos:
            stats.append(f"Mouse: {mouse_pos}")
        if last_key:
            stats.append(f"Last Key: {last_key}")
        if self.j.pattern_stats.get('move_freq_mean'):
            stats.append(f"Move Freq: {self.j.pattern_stats['move_freq_mean']:.2f}s")
        stats_str = " | ".join(stats) if stats else "Stats: No activity"
        self.root.after(0, lambda: self.lbl_stats.config(text=stats_str))

    def _show_help(self):
        help_text = (
            "Input Jiggler v1.1\n\n"
            "Simulates mouse and keyboard activity to prevent idle timeouts.\n\n"
            "Controls:\n"
            "- Start Recording: Record mouse/keyboard inputs (ESC to stop if no duration).\n"
            "- Start Simulation: Begin simulating based on recorded patterns or random mode.\n"
            "- Pause/Resume: Toggle simulation pause (hotkey: P).\n"
            "- Stop Simulation: Stop simulation (hotkey: ESC).\n"
            "- Hotkeys: ESC (stop), P (pause/resume), F8 (hide GUI), F12 (exit program).\n\n"
            "Safe Keys: space, enter, tab, left, right, up, down, a-z, 0-9, f1-f12.\n"
            "Custom Keys: Enter comma-separated keys (e.g., 'space,enter,a').\n"
            "Intensity: Low (slower), Medium, High (faster).\n"
            "Random Mode: Ignore recorded patterns, use random behavior."
        )
        messagebox.showinfo("Help", help_text)

    def _tick(self):
        try:
            mouse_pos = self.j.mouse_backend.get_pos()
            last_key = self.j.recorder.key_events[-1]['key'] if self.j.recorder.key_events else None
            self._update_stats(mouse_pos, last_key)
        except Exception:
            pass
        self.root.after(500, self._tick)

    def _start_recording(self):
        dur_s = self.var_dur.get().strip()
        try:
            dur = int(dur_s) if dur_s else None
        except ValueError:
            messagebox.showerror("Error", "Invalid duration; enter seconds or leave blank.")
            return
        self._set_status("Recording...")
        threading.Thread(target=self._record_thread, args=(dur,), daemon=True).start()

    def _record_thread(self, dur: Optional[int]):
        try:
            self.j.record_input(duration=dur)
            self._set_status("Recording finished.")
        except Exception as e:
            self._set_status(f"Recording error: {e}")

    def _start_sim(self):
        self.j.random_mode = self.var_random.get()
        self.j.set_intensity(self.var_intensity.get())
        keys_raw = [k.strip() for k in self.ent_keys.get().split(",") if k.strip()]
        self.j.set_custom_keys(keys_raw or ['space'])
        self._set_status("Simulating...")
        threading.Thread(
            target=self.j.start_simulation,
            kwargs={
                "simulate_mouse": self.var_mouse.get(),
                "simulate_keyboard": self.var_keyboard.get(),
                "from_gui": True
            },
            daemon=True
        ).start()

    def _toggle_pause(self):
        if self.j.running.is_set():
            if self.j.paused.is_set():
                self.j.paused.clear()
                self._set_status("Simulating (resumed)")
            else:
                self.j.paused.set()
                self._set_status("Simulating (paused)")
        else:
            self._set_status("Idle")

    def _stop_sim(self):
        self.j.running.clear()
        self.j._uninstall_hotkeys()
        self._set_status("Stopped")

    def _set_status(self, text: str):
        self.root.after(0, lambda: self.lbl_status.config(text=f"Status: {text}"))

    def run(self):
        self.root.mainloop()