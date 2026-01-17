import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import json
import os
from unittest.mock import Mock, patch
from jiggler.logger import Logger
from jiggler.config import ConfigManager
from jiggler.backends import build_mouse_backend, build_keyboard_backend
from jiggler.core import InputJiggler
from jiggler.gui import JigglerGUI

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config_file = tmp_path / "test_jiggler_patterns.json"
    return str(config_file)

@pytest.fixture
def logger():
    """Create a Logger instance with no file output."""
    return Logger(log_file=None, silent=True)

@pytest.fixture
def config_manager(temp_config_file):
    """Create a ConfigManager instance with a temp file."""
    return ConfigManager(temp_config_file)

@pytest.fixture
def input_jiggler(temp_config_file, logger):
    """Create an InputJiggler instance with mocked backends."""
    with patch("jiggler.core.build_mouse_backend") as mock_mouse, \
         patch("jiggler.core.build_keyboard_backend") as mock_keyboard:
        mock_mouse.return_value = Mock()
        mock_keyboard.return_value = Mock(hotkeys_supported=lambda: True, install_hotkeys=Mock(return_value=Mock()))
        jiggler = InputJiggler(config_file=temp_config_file, silent=True)
        return jiggler

def test_logger_initialization(tmp_path):
    """Test Logger initialization and logging."""
    log_file = tmp_path / "test.log"
    logger = Logger(log_file=str(log_file), silent=False)
    logger.info("Test message")
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        assert "Test message" in f.read()

def test_logger_silent_mode():
    """Test Logger in silent mode."""
    logger = Logger(log_file=None, silent=True)
    with patch("logging.StreamHandler") as mock_handler:
        logger.info("Silent message")
        mock_handler.assert_not_called()

def test_config_manager_save_load(temp_config_file):
    """Test ConfigManager save and load."""
    cm = ConfigManager(temp_config_file)
    data = {"settings": {"intensity": 1.0, "random_mode": False, "custom_keys": ["space"]}}
    cm.save(data)
    assert os.path.exists(temp_config_file)
    loaded = cm.load()
    assert loaded["settings"] == data["settings"]  # Compare only settings

def test_config_manager_empty_file(temp_config_file):
    """Test ConfigManager with empty file."""
    cm = ConfigManager(temp_config_file)
    assert cm.load() == {"settings": {}, "pattern_stats": {}}

def test_input_jiggler_initialization(input_jiggler):
    """Test InputJiggler initialization."""
    assert input_jiggler.intensity == 1.0
    assert input_jiggler.random_mode is False
    assert input_jiggler.custom_keys == ["space"]
    assert input_jiggler.running.is_set() is False
    assert input_jiggler.paused.is_set() is False

def test_input_jiggler_set_intensity(input_jiggler):
    """Test setting intensity."""
    input_jiggler.set_intensity("low")
    assert input_jiggler.intensity == 0.5
    input_jiggler.set_intensity("high")
    assert input_jiggler.intensity == 2.0
    input_jiggler.set_intensity("invalid")
    assert input_jiggler.intensity == 1.0  # Fallback to medium

def test_input_jiggler_set_custom_keys(input_jiggler):
    """Test setting custom keys."""
    input_jiggler.set_custom_keys(["space", "enter", "invalid"])
    assert input_jiggler.custom_keys == ["space", "enter"]
    input_jiggler.set_custom_keys([])
    assert input_jiggler.custom_keys == ["space"]  # Fallback to default

@patch("jiggler.core.threading.Thread")
@patch("jiggler.core.MouseSimulator")
@patch("jiggler.core.KeyboardSimulator")
def test_start_simulation_random(mock_keyboard_sim, mock_mouse_sim, mock_thread, input_jiggler):
    """Test start_simulation in random mode."""
    mock_thread.return_value = Mock(start=Mock(), is_alive=Mock(return_value=False))
    input_jiggler.random_mode = True
    input_jiggler.start_simulation(simulate_mouse=True, simulate_keyboard=True, from_gui=True)
    assert mock_mouse_sim.called
    assert mock_keyboard_sim.called
    assert input_jiggler.running.is_set()
    assert mock_thread.call_count == 2  # One for mouse, one for keyboard

@patch("jiggler.core.threading.Event")
def test_start_simulation_no_patterns(mock_event, input_jiggler):
    """Test start_simulation with no patterns and no random mode."""
    input_jiggler.random_mode = False
    input_jiggler.pattern_stats = {}
    with patch.object(input_jiggler.log, "error") as mock_error:
        input_jiggler.start_simulation()
        mock_error.assert_called_with("No patterns recorded. Record first or use --random.")

def test_install_hotkeys(input_jiggler):
    """Test hotkey installation with debouncing."""
    input_jiggler._install_hotkeys()
    assert input_jiggler.keyboard_backend.install_hotkeys.called
    assert input_jiggler._unhook_hotkeys is not None

@patch("tkinter.BooleanVar")
@patch("tkinter.StringVar")
@patch("tkinter.Tk")
def test_gui_initialization(mock_tk, mock_string_var, mock_boolean_var, input_jiggler):
    """Test JigglerGUI initialization."""
    mock_root = Mock(_last_child_ids={}, _w='.')
    mock_tk.return_value = mock_root
    mock_string_var.return_value = Mock(get=lambda: "medium")
    mock_boolean_var.return_value = Mock(get=lambda: False)
    gui = JigglerGUI(input_jiggler)
    assert mock_tk.called
    assert gui.j == input_jiggler
    assert gui.var_intensity.get() == "medium"
    assert gui.var_random.get() is False
    assert gui.ent_keys.get() == "space"