import logging
from typing import Optional, Callable

class Logger:
    def __init__(self, log_file: Optional[str] = None, silent: bool = False, gui_log_callback: Optional[Callable[[str], None]] = None):
        self.logger = logging.getLogger("InputJiggler")
        self.logger.setLevel(logging.DEBUG)
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
        self.gui_log_callback = gui_log_callback

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        if not silent:
            ch = logging.StreamHandler()
            ch.setFormatter(fmt)
            self.logger.addHandler(ch)

        if log_file:
            fh = logging.FileHandler(log_file)
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)

    def info(self, msg: str):
        self.logger.info(msg)
        if self.gui_log_callback:
            self.gui_log_callback(f"INFO: {msg}")

    def debug(self, msg: str):
        self.logger.debug(msg)
        if self.gui_log_callback:
            self.gui_log_callback(f"DEBUG: {msg}")

    def error(self, msg: str):
        self.logger.error(msg)
        if self.gui_log_callback:
            self.gui_log_callback(f"ERROR: {msg}")

    def warning(self, msg: str):
        self.logger.warning(msg)
        if self.gui_log_callback:
            self.gui_log_callback(f"WARNING: {msg}")