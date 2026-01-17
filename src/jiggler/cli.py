import argparse
import logging
from .core import InputJiggler
from .gui import JigglerGUI

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Professional-grade Keyboard & Mouse Jiggler (v1.1)\n\n"
            "Simulates mouse and keyboard activity to prevent idle timeouts.\n"
            "Hotkeys: ESC (stop), P (pause/resume), F8 (hide GUI), F12 (exit).\n"
            "Safe keys: space, enter, tab, left, right, up, down, a-z, 0-9, f1-f12."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--keyboard', action='store_true', help="Simulate keyboard only")
    mode.add_argument('--mouse', action='store_true', help="Simulate mouse only")
    mode.add_argument('--both', action='store_true', help="Simulate both (default)")
    parser.add_argument('--record', type=int, help="Record inputs for N seconds")
    parser.add_argument('--config', choices=['low','medium','high'], default='medium', help="Intensity")
    parser.add_argument('--silent', action='store_true', help="No console logs")
    parser.add_argument('--random', action='store_true', help="Use random patterns (no recording needed)")
    parser.add_argument('--keys', type=str, help="Comma-separated list of keys (e.g. 'a,b,space,left')")
    parser.add_argument('--log-file', type=str, help="Log file path")
    parser.add_argument('--gui', action='store_true', help="Launch GUI")
    parser.add_argument('--config-file', type=str, default='jiggler_patterns.json', help="Stats/config file")
    parser.add_argument('--raw-events', action='store_true', help="Also save capped raw events")
    parser.add_argument('--max-events', type=int, default=1000, help="Max raw events to keep if --raw-events is set")
    args = parser.parse_args()
    try:
        j = InputJiggler(config_file=args.config_file, silent=args.silent, log_file=args.log_file,
                         keep_raw_events=args.raw_events, max_events=args.max_events)
        j.set_intensity(args.config)
        j.random_mode = args.random
        if args.keys:
            j.set_custom_keys(args.keys.split(','))
        if args.gui:
            gui = JigglerGUI(j)
            gui.var_intensity.set({0.5: 'low', 1.0: 'medium', 2.0: 'high'}.get(j.intensity, 'medium'))
            gui.var_random.set(j.random_mode)
            gui.ent_keys.delete(0, 'end')
            gui.ent_keys.insert(0, ",".join(j.custom_keys))
            gui.run()
            return
        if args.record:
            j.record_input(duration=args.record)
            return
        simulate_mouse = True
        simulate_keyboard = True
        if args.keyboard and not args.mouse:
            simulate_mouse = False
        elif args.mouse and not args.keyboard:
            simulate_keyboard = False
        j.start_simulation(simulate_mouse, simulate_keyboard, from_gui=False)
    except Exception as e:
        logging.basicConfig(level=logging.ERROR, format='[%(asctime)s] %(levelname)s: %(message)s')
        logging.error(f"Application error: {e}")
        raise