import time
import random
import numpy as np
from typing import Optional, List, Dict, Deque, Tuple
from collections import deque
from .logger import Logger
from .config import ConfigManager
from .backends import MouseBackend, KeyboardBackend, pynput_keyboard, pynput_mouse, kb_lib
from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Listener as MouseListener
import threading

SAFE_DEFAULT_KEYS = [
    'space', 'enter', 'tab',
    'left', 'right', 'up', 'down',
    'a','b','c','d','e','f','g','h','i','j','k','l','m',
    'n','o','p','q','r','s','t','u','v','w','x','y','z',
    '0','1','2','3','4','5','6','7','8','9',
    'f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12'
]

DANGEROUS_KEYS = {
    'ctrl+alt+del', 'alt+f4', 'win', 'cmd', 'super'
}

def validate_keys(candidate: List[str], logger: Logger) -> List[str]:
    valid = []
    for key in candidate:
        k = key.strip().lower()
        if not k:
            continue
        if any(d in k for d in DANGEROUS_KEYS):
            logger.warning(f"Blocked dangerous key: {k}")
            continue
        if k in SAFE_DEFAULT_KEYS or (k.startswith('f') and k[1:].isdigit() and 1 <= int(k[1:]) <= 24):
            valid.append(k)
        elif len(k) == 1 and k.isprintable():
            valid.append(k)
        else:
            if k in {'shift','ctrl','alt'}:
                valid.append(k)
            else:
                logger.warning(f"Ignoring unrecognized/unsafe key: {k}")
    seen = set()
    filtered = []
    for k in valid:
        if k not in seen:
            filtered.append(k); seen.add(k)
    return filtered or ['space']

class MouseSimulator:
    def __init__(self, logger: Logger, backend: MouseBackend, pattern_stats: Dict, intensity: float, random_mode: bool, stats_lock: threading.Lock):
        self.log = logger
        self.bk = backend
        self.stats = pattern_stats
        self.intensity = max(0.1, float(intensity))
        self.random_mode = random_mode
        self.stats_lock = stats_lock
        self.sw, self.sh = self.bk.screen_size()

    def _params(self) -> Tuple[float, float, float]:
        with self.stats_lock:
            if self.random_mode:
                return (
                    random.uniform(0.5, 2.0) / self.intensity,
                    random.uniform(20, 100) * self.intensity,
                    random.uniform(0, 2*np.pi)
                )
            return (
                max(0.1, np.random.normal(self.stats.get('move_freq_mean', 1.0),
                                          self.stats.get('move_freq_std', 0.5))) / self.intensity,
                max(10, np.random.normal(self.stats.get('move_dist_mean', 50.0),
                                         self.stats.get('move_dist_std', 20.0))) * self.intensity,
                np.random.normal(self.stats.get('move_angles_mean', 0.0),
                                 self.stats.get('move_angles_std', np.pi))
            )

    def run(self, running: threading.Event, paused: threading.Event):
        while running.is_set():
            if paused.is_set():
                time.sleep(0.1); continue
            try:
                delay, dist, angle = self._params()
                time.sleep(delay)
                dx = int(dist * np.cos(angle))
                dy = int(dist * np.sin(angle))
                x, y = self.bk.get_pos()
                nx = max(0, min(x + dx, self.sw - 1))
                ny = max(0, min(y + dy, self.sh - 1))
                self.bk.set_pos(nx, ny)
                self.bk.move_rel(dx, dy)
                self.log.debug(f"Mouse to ({nx},{ny}) dx={dx} dy={dy}")
                if random.random() < 0.1 * self.intensity:
                    steps = random.choice([-1, 0, 1])
                    if steps:
                        self.bk.scroll(steps)
                        self.log.debug(f"Scrolled {steps}")
            except Exception as e:
                self.log.error(f"Mouse simulation error: {e}")
                time.sleep(1)

class KeyboardSimulator:
    def __init__(self, logger: Logger, backend: KeyboardBackend, pattern_stats: Dict, intensity: float, random_mode: bool, keys: List[str], stats_lock: threading.Lock):
        self.log = logger
        self.bk = backend
        self.stats = pattern_stats
        self.intensity = max(0.1, float(intensity))
        self.random_mode = random_mode
        self.keys = keys or ['space']
        self.stats_lock = stats_lock

    def _delay(self) -> float:
        with self.stats_lock:
            if self.random_mode:
                return random.uniform(1.0, 5.0) / self.intensity
            return max(0.5, np.random.normal(self.stats.get('key_freq_mean', 5.0),
                                             self.stats.get('key_freq_std', 2.0))) / self.intensity

    def run(self, running: threading.Event, paused: threading.Event):
        while running.is_set():
            if paused.is_set():
                time.sleep(0.1); continue
            try:
                time.sleep(self._delay())
                if random.random() < 0.5 * self.intensity:
                    key = random.choice(self.keys)
                    self.log.debug(f"Key press: {key}")
                    self.bk.press(key)
                    time.sleep(random.uniform(0.05, 0.15))
                    self.bk.release(key)
            except Exception as e:
                self.log.error(f"Keyboard simulation error: {e}")
                time.sleep(1)

class InputRecorder:
    def __init__(self, logger: Logger, cfg: ConfigManager, mouse_backend: MouseBackend, keyboard_backend: KeyboardBackend,
                 keep_raw_events: bool = False, max_events: int = 1000, stats_lock: threading.Lock = None):
        self.log = logger
        self.cfg = cfg
        self.mouse = mouse_backend
        self.keyboard = keyboard_backend
        self.keep_raw = keep_raw_events
        self.max_events = max_events
        self.stats_lock = stats_lock or threading.Lock()
        self._key_listener = None
        self._mouse_listener = None
        self.mouse_events: Deque[Dict] = deque(maxlen=max_events if keep_raw_events else 0)
        self.key_events: Deque[Dict] = deque(maxlen=max_events if keep_raw_events else 0)
        self.pattern_stats: Dict = {'move_freq': [], 'key_freq': [], 'move_dist': [], 'move_angles': []}
        try:
            self.last_pos = self.mouse.get_pos()
        except Exception:
            self.last_pos = (0, 0)

    def record(self, duration: Optional[int] = None, stop_event: Optional[threading.Event] = None) -> None:
        self.log.info(f"Recording inputs... {'for %d seconds' % duration if duration else 'Press ESC to stop'}")
        start = time.time()
        last_move_t = start
        last_key_t = start

        unhook = None
        def on_esc():
            if stop_event: stop_event.set()
        try:
            if self.keyboard.hotkeys_supported():
                unhook = self.keyboard.install_hotkeys({'esc': on_esc})
        except Exception:
            unhook = None

        key_lock = threading.Lock()
        def on_key_press(key):
            nonlocal last_key_t
            try:
                key_name = str(key).strip("'").lower()
                if hasattr(key, 'char') and key.char:
                    key_name = key.char
                elif key_name.startswith('key.'):
                    key_name = key_name[4:]
                if key_name in SAFE_DEFAULT_KEYS or len(key_name) == 1:
                    with key_lock:
                        now = time.time()
                        self.pattern_stats['key_freq'].append(now - last_key_t)
                        last_key_t = now
                        if self.keep_raw:
                            self.key_events.append({'time': time.strftime("%Y-%m-%dT%H:%M:%S"), 'key': key_name})
            except Exception as e:
                self.log.error(f"Key recording error: {e}")

        def on_mouse_click(x, y, button, pressed):
            if pressed and self.keep_raw:
                self.mouse_events.append({
                    'time': time.strftime("%Y-%m-%dT%H:%M:%S"),
                    'type': 'click',
                    'pos': (x, y),
                    'button': str(button).split('.')[-1]
                })

        def on_mouse_scroll(x, y, dx, dy):
            if self.keep_raw:
                self.mouse_events.append({
                    'time': time.strftime("%Y-%m-%dT%H:%M:%S"),
                    'type': 'scroll',
                    'pos': (x, y),
                    'dy': dy
                })

        if pynput_keyboard:
            self._key_listener = KeyboardListener(on_press=on_key_press)
            self._key_listener.start()
        elif kb_lib:
            self.log.warning("pynput not available; falling back to limited key polling with keyboard library")
            pressed_state = set()
            def poll_keys():
                for k in ['space', 'enter', 'tab', 'left', 'right', 'up', 'down']:
                    try:
                        if kb_lib.is_pressed(k) and k not in pressed_state:
                            pressed_state.add(k)
                            on_key_press(k)
                        elif not kb_lib.is_pressed(k) and k in pressed_state:
                            pressed_state.remove(k)
                    except Exception:
                        pass
        else:
            self.log.warning("No keyboard recording backend available; key events will not be recorded")

        if pynput_mouse:
            self._mouse_listener = MouseListener(on_click=on_mouse_click, on_scroll=on_mouse_scroll)
            self._mouse_listener.start()

        try:
            while True:
                if stop_event and stop_event.is_set():
                    break
                if duration and (time.time() - start) > duration:
                    break
                try:
                    cur = self.mouse.get_pos()
                except Exception:
                    cur = self.last_pos
                if cur != self.last_pos:
                    dx = cur[0] - self.last_pos[0]
                    dy = cur[1] - self.last_pos[1]
                    dist = (dx*dx + dy*dy) ** 0.5
                    angle = np.arctan2(dy, dx)
                    now = time.time()
                    self.pattern_stats['move_freq'].append(now - last_move_t)
                    self.pattern_stats['move_dist'].append(dist)
                    self.pattern_stats['move_angles'].append(angle)
                    last_move_t = now
                    if self.keep_raw:
                        self.mouse_events.append({
                            'time': time.strftime("%Y-%m-%dT%H:%M:%S"),
                            'pos': cur, 'dist': dist, 'angle': float(angle)
                        })
                    self.last_pos = cur
                if kb_lib and not pynput_keyboard:
                    poll_keys()
                time.sleep(0.01)
        except Exception as e:
            self.log.error(f"Recording error: {e}")
        finally:
            if self._key_listener:
                try:
                    self._key_listener.stop()
                except Exception:
                    pass
                self._key_listener = None
            if self._mouse_listener:
                try:
                    self._mouse_listener.stop()
                except Exception:
                    pass
                self._mouse_listener = None
            if unhook:
                try: unhook()
                except Exception: pass
            self._analyze()
            self._save()

    def _analyze(self) -> None:
        defaults = {
            'move_freq': (1.0, 0.5),
            'key_freq': (5.0, 2.0),
            'move_dist': (50.0, 20.0),
            'move_angles': (0.0, np.pi)
        }
        with self.stats_lock:
            for key, (dmean, dstd) in defaults.items():
                arr = self.pattern_stats[key]
                self.pattern_stats[f'{key}_mean'] = float(np.mean(arr)) if arr else float(dmean)
                self.pattern_stats[f'{key}_std'] = float(np.std(arr)) if arr else float(dstd)

    def _save(self) -> None:
        data = {'pattern_stats': self.pattern_stats}
        if self.keep_raw:
            data['mouse_events'] = list(self.mouse_events)
            data['key_events'] = list(self.key_events)
        try:
            self.cfg.save(data)
        except Exception as e:
            self.log.error(f"Failed to save patterns: {e}")