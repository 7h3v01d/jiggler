import platform
from typing import Tuple, Dict, Callable
from .logger import Logger

try:
    import win32api
    import win32con
except Exception:
    win32api = None
    win32con = None

try:
    import keyboard as kb_lib
except Exception:
    kb_lib = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None

try:
    from pynput import keyboard as pynput_keyboard
    from pynput import mouse as pynput_mouse
except Exception:
    pynput_keyboard = None
    pynput_mouse = None

class MouseBackend:
    def screen_size(self) -> Tuple[int, int]: raise NotImplementedError
    def get_pos(self) -> Tuple[int, int]: raise NotImplementedError
    def set_pos(self, x: int, y: int) -> None: raise NotImplementedError
    def move_rel(self, dx: int, dy: int) -> None: raise NotImplementedError
    def scroll(self, steps: int) -> None: raise NotImplementedError

class KeyboardBackend:
    def press(self, key: str) -> None: raise NotImplementedError
    def release(self, key: str) -> None: raise NotImplementedError
    def hotkeys_supported(self) -> bool: return False
    def install_hotkeys(self, mapping: Dict[str, Callable[[], None]]) -> Callable[[], None]:
        raise NotImplementedError
    def is_pressed(self, key: str) -> bool:
        return False

class Win32Mouse(MouseBackend):
    def __init__(self):
        if not win32api or not win32con:
            raise RuntimeError("win32api/win32con not available")
    def screen_size(self) -> Tuple[int, int]:
        return win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
    def get_pos(self) -> Tuple[int, int]:
        return win32api.GetCursorPos()
    def set_pos(self, x: int, y: int) -> None:
        win32api.SetCursorPos((x, y))
    def move_rel(self, dx: int, dy: int) -> None:
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy, 0, 0)
    def scroll(self, steps: int) -> None:
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, steps * 120, 0)

class PyAutoGuiMouse(MouseBackend):
    def __init__(self):
        if not pyautogui:
            raise RuntimeError("pyautogui backend not available")
    def screen_size(self) -> Tuple[int, int]:
        size = pyautogui.size()
        return size.width, size.height
    def get_pos(self) -> Tuple[int, int]:
        p = pyautogui.position()
        return p.x, p.y
    def set_pos(self, x: int, y: int) -> None:
        pyautogui.moveTo(x, y, duration=0)
    def move_rel(self, dx: int, dy: int) -> None:
        pyautogui.moveRel(dx, dy, duration=0)
    def scroll(self, steps: int) -> None:
        pyautogui.scroll(steps)

class KeyboardLib(KeyboardBackend):
    def __init__(self):
        if not kb_lib:
            raise RuntimeError("keyboard library not available")
    def press(self, key: str) -> None:
        kb_lib.press(key)
    def release(self, key: str) -> None:
        kb_lib.release(key)
    def hotkeys_supported(self) -> bool:
        return True
    def install_hotkeys(self, mapping: Dict[str, Callable[[], None]]) -> Callable[[], None]:
        hooks = []
        for k, fn in mapping.items():
            hooks.append(kb_lib.add_hotkey(k, fn))
        def unhook():
            for h in hooks: kb_lib.remove_hotkey(h)
        return unhook
    def is_pressed(self, key: str) -> bool:
        try:
            return kb_lib.is_pressed(key)
        except Exception:
            return False

class PynputKeyboard(KeyboardBackend):
    def __init__(self):
        if not pynput_keyboard:
            raise RuntimeError("pynput not available")
        self._controller = pynput_keyboard.Controller()
        self._listener = None

    def press(self, key: str) -> None:
        self._controller.press(self._to_key(key))

    def release(self, key: str) -> None:
        self._controller.release(self._to_key(key))

    def hotkeys_supported(self) -> bool:
        return True

    def install_hotkeys(self, mapping: Dict[str, Callable[[], None]]) -> Callable[[], None]:
        if not pynput_keyboard:
            raise RuntimeError("pynput not available")
        gh_mapping = {}
        for k, fn in mapping.items():
            k_norm = k.strip().lower()
            if len(k_norm) == 1:
                gh_mapping[f'<{k_norm}>'] = fn
            else:
                gh_mapping[f'<{k_norm}>'] = fn
        hotkeys = pynput_keyboard.GlobalHotKeys(gh_mapping)
        hotkeys.start()
        def unhook():
            try:
                hotkeys.stop()
            except Exception:
                pass
        return unhook

    def _to_key(self, key: str):
        key = key.strip().lower()
        special = {
            'esc': pynput_keyboard.Key.esc,
            'enter': pynput_keyboard.Key.enter,
            'space': pynput_keyboard.Key.space,
            'tab': pynput_keyboard.Key.tab,
            'shift': pynput_keyboard.Key.shift,
            'ctrl': pynput_keyboard.Key.ctrl,
            'alt': pynput_keyboard.Key.alt,
            'up': pynput_keyboard.Key.up,
            'down': pynput_keyboard.Key.down,
            'left': pynput_keyboard.Key.left,
            'right': pynput_keyboard.Key.right,
            'backspace': pynput_keyboard.Key.backspace,
            'delete': pynput_keyboard.Key.delete,
            'home': pynput_keyboard.Key.home,
            'end': pynput_keyboard.Key.end,
            'pageup': pynput_keyboard.Key.page_up,
            'pagedown': pynput_keyboard.Key.page_down,
        }
        if key in special:
            return special[key]
        if key.startswith('f') and key[1:].isdigit():
            fn_number = int(key[1:])
            return getattr(pynput_keyboard.Key, f'f{fn_number}', key)
        if len(key) == 1:
            return key
        return key

def build_mouse_backend(logger: Logger) -> MouseBackend:
    if win32api and win32con and platform.system().lower() == 'windows':
        logger.info("Using Win32 mouse backend")
        return Win32Mouse()
    if pyautogui:
        logger.info("Using PyAutoGUI mouse backend")
        return PyAutoGuiMouse()
    raise RuntimeError("No mouse backend available (need win32api or pyautogui)")

def build_keyboard_backend(logger: Logger) -> KeyboardBackend:
    if kb_lib:
        try:
            kb_lib.press('space'); kb_lib.release('space')
            logger.info("Using 'keyboard' library backend")
            return KeyboardLib()
        except Exception:
            logger.warning("'keyboard' library present but not fully functional. Falling back to pynput.")
    if pynput_keyboard:
        logger.info("Using pynput keyboard backend")
        return PynputKeyboard()
    raise RuntimeError("No keyboard backend available (need keyboard or pynput)")