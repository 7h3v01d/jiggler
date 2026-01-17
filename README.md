# Input Jiggler

Input Jiggler is a Python application that simulates mouse and keyboard inputs to keep your computer active, useful for preventing screen locks or simulating user activity. It supports random or recorded input patterns, a graphical user interface (GUI), and a command-line interface (CLI). The project includes hotkey support for controlling the simulation and a robust test suite.

## Features
- **Mouse and Keyboard Simulation**: Simulates mouse movements, clicks, and key presses (e.g., `space`, `enter`).
- **Random Mode**: Generates random input patterns for realistic activity.
- **Recorded Patterns**: Records user inputs to replay custom patterns.
- **Hotkey Controls**:
  - `ESC`: Stop the simulation.
  - `P`: Pause/resume the simulation.
  - `F8`: Hide the GUI (if running).
  - `F12`: Terminate the application.
- **GUI**: Intuitive interface to configure intensity, keys, and random mode.
- **CLI**: Command-line support for scripting and automation.
- **Configuration**: Saves settings and patterns in `jiggler_patterns.json`.
- **Cross-Platform**: Primarily designed for Windows, with potential Linux support (via `pynput`).

## Installation

1. **Clone the Repository** (if applicable):
   ```bash
   git clone <repository-url>
   cd jiggler/src
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Required packages (listed in `requirements.txt`):
   - `pywin32==311`
   - `keyboard==0.13.5`
   - `pyautogui==0.9.54`
   - `pynput==1.8.1`
   - `numpy==2.3.2`

## Usage

### GUI Mode
Run the application with the GUI:
```bash
python jiggler_v1.1.py --gui
```
- Configure intensity (`low`, `medium`, `high`), custom keys (e.g., `space,enter`), and random mode.
- Click "Start Simulation" to begin, "Record" to capture inputs, or use hotkeys (`ESC`, `P`, `F8`, `F12`).

### CLI Mode
Run simulations or recordings via the command line:
- **Random Simulation**:
  ```bash
  python jiggler_v1.1.py --random --keys "space,enter" --config medium
  ```
- **Record Inputs** (e.g., 10 seconds):
  ```bash
  python jiggler_v1.1.py --record 10
  ```
- **Simulation with Log File**:
  ```bash
  python jiggler_v1.1.py --random --log-file jiggler.log
  ```

### Hotkeys
- `ESC`: Stop the simulation.
- `P`: Pause or resume the simulation.
- `F8`: Hide the GUI window.
- `F12`: Exit the application.

## Project Structure
```
jiggler/
├── src/
│   ├── jiggler/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── config.py
│   │   ├── backends.py
│   │   ├── simulators.py
│   │   ├── core.py
│   │   ├── gui.py
│   │   ├── cli.py
│   ├── tests/
│   │   ├── test_jiggler.py
│   ├── jiggler_v1.1.py
│   ├── requirements.txt
│   ├── pytest.ini
```

- `jiggler_v1.1.py`: Main entry point for CLI and GUI.
- `jiggler/`: Package containing core logic, GUI, and CLI.
- `tests/`: Unit tests for the application.
- `pytest.ini`: Configuration for pytest.

## Testing
The project includes a test suite to ensure reliability.

1. **Install Testing Dependencies**:
   ```bash
   pip install pytest pytest-mock
   ```

2. **Run Tests**:
   ```bash
   cd src
   pytest tests/test_jiggler.py -v
   ```
   Tests cover:
   - Logger initialization and silent mode.
   - Configuration saving/loading.
   - InputJiggler initialization, intensity, and custom keys.
   - Simulation behavior (random mode and no patterns).
   - Hotkey installation and GUI setup.

## Troubleshooting
- **Hotkey Issues**: If `F8` spams logs or `ESC` doesn’t stop the simulation, ensure `keyboard==0.13.5` and check logs in `jiggler.log`.
- **ModuleNotFoundError**: Verify `pytest.ini` exists with `python_paths = .` and run tests from `src/`.
- **Simulation Speed**: Use `--config low` to reduce intensity if the simulation feels too fast.
- **Logs**: Use `--log-file jiggler.log` to debug issues.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## Future Enhancements
- Add a stats chart (e.g., mouse movement frequency) using Chart.js.
- Implement a plugin system for custom input patterns.
- Expand test coverage for `simulators.py` and `cli.py`.
- Support additional platforms (e.g., Linux via `pynput`).

## License
This project is licensed under the MIT License.
