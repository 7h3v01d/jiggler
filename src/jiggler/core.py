import threading
import time
from typing import Optional, List, Dict, Callable
import os
from .logger import Logger
from .config import ConfigManager
from .backends import build_mouse_backend, build_keyboard_backend
from .simulators import MouseSimulator, KeyboardSimulator, InputRecorder, validate_keys

class InputJiggler:
    def __init__(self, config_file="jiggler_patterns.json", silent=False, log_file: Optional[str]=None,
                 keep_raw_events=False, max_events=1000):
        self.log = Logger(log_file, silent)
        self.cfg = ConfigManager(config_file)
        self.stats_lock = threading.Lock()
        config = self.cfg.load()
        self.pattern_stats = config.get('pattern_stats', {})
        settings = config.get('settings', {})
        self.intensity = settings.get('intensity', 1.0)
        self.random_mode = settings.get('random_mode', False)
        self.custom_keys = settings.get('custom_keys', ['space'])
        self.mouse_backend = build_mouse_backend(self.log)
        self.keyboard_backend = build_keyboard_backend(self.log)
        self.recorder = InputRecorder(self.log, self.cfg, self.mouse_backend, self.keyboard_backend,
                                      keep_raw_events=keep_raw_events, max_events=max_events, stats_lock=self.stats_lock)
        self.running = threading.Event()
        self.paused = threading.Event()
        self._unhook_hotkeys: Optional[Callable[[], None]] = None
        self._last_hotkey_time = {'esc': 0, 'p': 0, 'f8': 0, 'f12': 0}  # Debounce tracking
        self._hotkey_debounce_ms = 500  # 500ms debounce window

    def set_intensity(self, label: str):
        mapping = {'low': 0.5, 'medium': 1.0, 'high': 2.0}
        self.intensity = mapping.get(label.lower(), 1.0)
        self.log.info(f"Intensity set to {label} ({self.intensity})")
        self._save_settings()

    def set_custom_keys(self, keys: List[str]):
        validated = validate_keys(keys, self.log)
        self.custom_keys = validated
        self.log.info(f"Custom keys: {self.custom_keys}")
        self._save_settings()

    def _save_settings(self):
        settings = {
            'intensity': self.intensity,
            'random_mode': self.random_mode,
            'custom_keys': self.custom_keys
        }
        try:
            self.cfg.save({'settings': settings})
        except Exception as e:
            self.log.error(f"Failed to save settings: {e}")

    def record_input(self, duration: Optional[int] = None):
        stop = threading.Event()
        self.recorder.record(duration=duration, stop_event=stop)
        self.pattern_stats = self.recorder.pattern_stats

    def _install_hotkeys(self):
        if self.keyboard_backend.hotkeys_supported():
            def debounce_hotkey(key: str, callback: Callable[[], None]):
                def wrapped():
                    current_time = time.time() * 1000  # Convert to milliseconds
                    if current_time - self._last_hotkey_time[key] > self._hotkey_debounce_ms:
                        self._last_hotkey_time[key] = current_time
                        callback()
                return wrapped

            def on_esc():
                self.running.clear()
                self.log.info("Stop hotkey received")

            def on_p():
                if self.paused.is_set():
                    self.paused.clear()
                    self.log.info("Resumed")
                else:
                    self.paused.set()
                    self.log.info("Paused")

            def on_hide():
                self.log.info("Boss key (hide) pressed")
                self.running.clear()
                try:
                    import tkinter as tk
                    if tk._default_root is not None:
                        tk._default_root.withdraw()
                except Exception:
                    pass

            def on_kill():
                self.log.info("Boss key (kill) pressed – exiting")
                self.running.clear()
                self._uninstall_hotkeys()
                try:
                    import tkinter as tk
                    if tk._default_root is not None:
                        tk._default_root.destroy()
                except Exception:
                    pass
                os._exit(0)

            try:
                self._unhook_hotkeys = self.keyboard_backend.install_hotkeys({
                    'esc': debounce_hotkey('esc', on_esc),
                    'p': debounce_hotkey('p', on_p),
                    'f8': debounce_hotkey('f8', on_hide),
                    'f12': debounce_hotkey('f12', on_kill),
                })
            except Exception as e:
                self.log.warning(f"Failed to install hotkeys: {e}")
                self._unhook_hotkeys = None

    def _uninstall_hotkeys(self):
        if self._unhook_hotkeys:
            try:
                self._unhook_hotkeys()
            except Exception:
                pass
            self._unhook_hotkeys = None

    def start_simulation(self, simulate_mouse=True, simulate_keyboard=True, from_gui=False):
        if not self.random_mode and not self.pattern_stats.get('move_freq_mean'):
            self.log.error("No patterns recorded. Record first or use --random.")
            return
        self.log.info(f"Starting simulation (Mouse={simulate_mouse}, Keyboard={simulate_keyboard}, Random={self.random_mode})")
        self.running.set()
        self.paused.clear()
        self._install_hotkeys()
        threads = []
        if simulate_mouse:
            m = MouseSimulator(self.log, self.mouse_backend, self.pattern_stats, self.intensity, self.random_mode, self.stats_lock)
            t = threading.Thread(target=m.run, args=(self.running, self.paused), daemon=True)
            threads.append(t)
            t.start()
        if simulate_keyboard:
            k = KeyboardSimulator(self.log, self.keyboard_backend, self.pattern_stats, self.intensity, self.random_mode, self.custom_keys, self.stats_lock)
            t = threading.Thread(target=k.run, args=(self.running, self.paused), daemon=True)
            threads.append(t)
            t.start()
        if from_gui:
            return
        try:
            while self.running.is_set():
                time.sleep(0.1)
        finally:
            self.running.clear()  # Ensure running is cleared
            self._uninstall_hotkeys()
            # Wait for threads to terminate with a timeout
            for t in threads:
                t.join(timeout=2.0)  # 2-second timeout
                if t.is_alive():
                    self.log.warning(f"Thread {t.name} did not terminate cleanly")
            self.log.info("Simulation stopped.")