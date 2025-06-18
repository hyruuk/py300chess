"""
Configuration loader for py300chess.

This module handles loading and validating configuration from YAML files,
with support for environment variable overrides and default values.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class EEGConfig:
    """EEG system configuration."""
    sampling_rate: int = 250
    n_channels: int = 1
    channel_names: list = field(default_factory=lambda: ["Cz"])
    use_simulation: bool = True
    stream_name: str = "EEG_Stream"


@dataclass
class P300Config:
    """P300 detection configuration."""
    detection_window: list = field(default_factory=lambda: [250, 500])
    baseline_window: list = field(default_factory=lambda: [-200, 0])
    epoch_length: int = 800
    bandpass_filter: list = field(default_factory=lambda: [0.5, 30.0])
    detection_threshold: float = 2.0
    min_confidence: float = 0.6
    notch_filter: Optional[int] = 50


@dataclass
class StimulusConfig:
    """Stimulus presentation configuration."""
    flash_duration: int = 100
    inter_flash_interval: int = 200
    selection_pause: int = 1000
    flash_repetitions: int = 3
    flash_colors: dict = field(default_factory=lambda: {
        "normal": "#8B4513",
        "highlight": "#FFD700", 
        "flash": "#FF0000",
        "selected": "#00FF00"
    })


@dataclass
class ChessConfig:
    """Chess engine configuration."""
    engine_strength: int = 3
    time_limit: float = 2.0
    enable_castling: bool = True
    enable_en_passant: bool = True
    enable_promotion: bool = True
    starting_position: str = "startpos"


@dataclass
class GUIConfig:
    """GUI configuration."""
    window_size: list = field(default_factory=lambda: [800, 600])
    board_size: int = 480
    piece_style: str = "default"
    show_confidence: bool = True
    display_update_rate: int = 30
    font_size: int = 12


@dataclass
class FeedbackConfig:
    """Feedback and monitoring configuration."""
    confidence_display_time: int = 500
    debug_mode: bool = True
    log_level: str = "INFO"
    enable_signal_plots: bool = False


@dataclass
class SimulationConfig:
    """EEG simulation configuration."""
    noise_amplitude: float = 10.0
    p300_amplitude: float = 5.0
    p300_latency: int = 300
    p300_width: int = 100
    p300_probability: float = 0.8
    add_artifacts: bool = True
    artifact_rate: float = 0.1


@dataclass
class RecordingConfig:
    """Data recording configuration."""
    enable_recording: bool = False
    data_directory: str = "data/raw"
    file_format: str = "csv"
    record_raw_eeg: bool = True
    record_epochs: bool = True
    record_game_events: bool = True


@dataclass
class Config:
    """Main configuration class containing all sub-configurations."""
    eeg: EEGConfig = field(default_factory=EEGConfig)
    p300: P300Config = field(default_factory=P300Config)
    stimulus: StimulusConfig = field(default_factory=StimulusConfig)
    chess: ChessConfig = field(default_factory=ChessConfig)
    gui: GUIConfig = field(default_factory=GUIConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)


class ConfigLoader:
    """Configuration loader with validation and environment variable support."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_path: Path to configuration file. If None, looks for config.yaml
                        in the project root directory.
        """
        if config_path is None:
            # Find project root (directory containing this file's parent)
            current_dir = Path(__file__).parent
            project_root = current_dir.parent
            config_path = project_root / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config_data = None
        self._config = None
    
    def load(self) -> Config:
        """
        Load configuration from YAML file.
        
        Returns:
            Config: Loaded and validated configuration object.
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            yaml.YAMLError: If configuration file is invalid YAML.
            ValueError: If configuration validation fails.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        # Load YAML data
        with open(self.config_path, 'r') as f:
            self._config_data = yaml.safe_load(f)
        
        # Apply environment variable overrides
        self._apply_env_overrides()
        
        # Create configuration objects
        self._config = self._create_config_objects()
        
        # Validate configuration
        self._validate_config()
        
        return self._config
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Check for common environment variables
        env_overrides = {
            'PY300_SAMPLING_RATE': ('eeg', 'sampling_rate', int),
            'PY300_N_CHANNELS': ('eeg', 'n_channels', int),
            'PY300_USE_SIMULATION': ('eeg', 'use_simulation', lambda x: x.lower() == 'true'),
            'PY300_STREAM_NAME': ('eeg', 'stream_name', str),
            'PY300_DEBUG_MODE': ('feedback', 'debug_mode', lambda x: x.lower() == 'true'),
            'PY300_LOG_LEVEL': ('feedback', 'log_level', str),
        }
        
        for env_var, (section, key, converter) in env_overrides.items():
            if env_var in os.environ:
                value = converter(os.environ[env_var])
                if section not in self._config_data:
                    self._config_data[section] = {}
                self._config_data[section][key] = value
    
    def _create_config_objects(self) -> Config:
        """Create configuration objects from loaded data."""
        # Create individual config sections
        eeg_config = EEGConfig(**self._config_data.get('eeg', {}))
        p300_config = P300Config(**self._config_data.get('p300', {}))
        stimulus_config = StimulusConfig(**self._config_data.get('stimulus', {}))
        chess_config = ChessConfig(**self._config_data.get('chess', {}))
        gui_config = GUIConfig(**self._config_data.get('gui', {}))
        feedback_config = FeedbackConfig(**self._config_data.get('feedback', {}))
        simulation_config = SimulationConfig(**self._config_data.get('simulation', {}))
        recording_config = RecordingConfig(**self._config_data.get('recording', {}))
        
        # Create main config object
        return Config(
            eeg=eeg_config,
            p300=p300_config,
            stimulus=stimulus_config,
            chess=chess_config,
            gui=gui_config,
            feedback=feedback_config,
            simulation=simulation_config,
            recording=recording_config
        )
    
    def _validate_config(self):
        """Validate configuration values."""
        errors = []
        
        # Validate EEG settings
        if self._config.eeg.sampling_rate <= 0:
            errors.append("EEG sampling rate must be positive")
        
        if self._config.eeg.n_channels <= 0:
            errors.append("Number of EEG channels must be positive")
        
        if len(self._config.eeg.channel_names) != self._config.eeg.n_channels:
            errors.append("Number of channel names must match n_channels")
        
        # Validate P300 settings
        if self._config.p300.detection_window[0] >= self._config.p300.detection_window[1]:
            errors.append("P300 detection window start must be before end")
        
        if self._config.p300.baseline_window[0] >= self._config.p300.baseline_window[1]:
            errors.append("P300 baseline window start must be before end")
        
        if not (0.0 <= self._config.p300.min_confidence <= 1.0):
            errors.append("P300 minimum confidence must be between 0.0 and 1.0")
        
        # Validate stimulus settings
        if self._config.stimulus.flash_duration <= 0:
            errors.append("Flash duration must be positive")
        
        if self._config.stimulus.inter_flash_interval <= 0:
            errors.append("Inter-flash interval must be positive")
        
        if self._config.stimulus.flash_repetitions <= 0:
            errors.append("Flash repetitions must be positive")
        
        # Validate chess settings
        if not (1 <= self._config.chess.engine_strength <= 10):
            errors.append("Chess engine strength must be between 1 and 10")
        
        if self._config.chess.time_limit <= 0:
            errors.append("Chess time limit must be positive")
        
        # Validate GUI settings
        if len(self._config.gui.window_size) != 2:
            errors.append("GUI window size must be [width, height]")
        
        if any(size <= 0 for size in self._config.gui.window_size):
            errors.append("GUI window dimensions must be positive")
        
        if self._config.gui.board_size <= 0:
            errors.append("Chess board size must be positive")
        
        # Validate simulation settings
        if self._config.simulation.noise_amplitude < 0:
            errors.append("Simulation noise amplitude must be non-negative")
        
        if self._config.simulation.p300_amplitude < 0:
            errors.append("Simulation P300 amplitude must be non-negative")
        
        if not (0.0 <= self._config.simulation.p300_probability <= 1.0):
            errors.append("Simulation P300 probability must be between 0.0 and 1.0")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    def save(self, config: Config, path: Optional[Union[str, Path]] = None):
        """
        Save configuration to YAML file.
        
        Args:
            config: Configuration object to save.
            path: Path to save configuration. If None, uses original path.
        """
        if path is None:
            path = self.config_path
        else:
            path = Path(path)
        
        # Convert config object back to dictionary
        config_dict = self._config_to_dict(config)
        
        # Save to YAML file
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
    
    def _config_to_dict(self, config: Config) -> dict:
        """Convert configuration object to dictionary."""
        return {
            'eeg': {
                'sampling_rate': config.eeg.sampling_rate,
                'n_channels': config.eeg.n_channels,
                'channel_names': config.eeg.channel_names,
                'use_simulation': config.eeg.use_simulation,
                'stream_name': config.eeg.stream_name,
            },
            'p300': {
                'detection_window': config.p300.detection_window,
                'baseline_window': config.p300.baseline_window,
                'epoch_length': config.p300.epoch_length,
                'bandpass_filter': config.p300.bandpass_filter,
                'detection_threshold': config.p300.detection_threshold,
                'min_confidence': config.p300.min_confidence,
                'notch_filter': config.p300.notch_filter,
            },
            'stimulus': {
                'flash_duration': config.stimulus.flash_duration,
                'inter_flash_interval': config.stimulus.inter_flash_interval,
                'selection_pause': config.stimulus.selection_pause,
                'flash_repetitions': config.stimulus.flash_repetitions,
                'flash_colors': config.stimulus.flash_colors,
            },
            'chess': {
                'engine_strength': config.chess.engine_strength,
                'time_limit': config.chess.time_limit,
                'enable_castling': config.chess.enable_castling,
                'enable_en_passant': config.chess.enable_en_passant,
                'enable_promotion': config.chess.enable_promotion,
                'starting_position': config.chess.starting_position,
            },
            'gui': {
                'window_size': config.gui.window_size,
                'board_size': config.gui.board_size,
                'piece_style': config.gui.piece_style,
                'show_confidence': config.gui.show_confidence,
                'display_update_rate': config.gui.display_update_rate,
                'font_size': config.gui.font_size,
            },
            'feedback': {
                'confidence_display_time': config.feedback.confidence_display_time,
                'debug_mode': config.feedback.debug_mode,
                'log_level': config.feedback.log_level,
                'enable_signal_plots': config.feedback.enable_signal_plots,
            },
            'simulation': {
                'noise_amplitude': config.simulation.noise_amplitude,
                'p300_amplitude': config.simulation.p300_amplitude,
                'p300_latency': config.simulation.p300_latency,
                'p300_width': config.simulation.p300_width,
                'p300_probability': config.simulation.p300_probability,
                'add_artifacts': config.simulation.add_artifacts,
                'artifact_rate': config.simulation.artifact_rate,
            },
            'recording': {
                'enable_recording': config.recording.enable_recording,
                'data_directory': config.recording.data_directory,
                'file_format': config.recording.file_format,
                'record_raw_eeg': config.recording.record_raw_eeg,
                'record_epochs': config.recording.record_epochs,
                'record_game_events': config.recording.record_game_events,
            }
        }


# Global configuration instance
_config_instance = None


def get_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        config_path: Path to configuration file. Only used on first call.
        
    Returns:
        Config: Global configuration object.
    """
    global _config_instance
    
    if _config_instance is None:
        loader = ConfigLoader(config_path)
        _config_instance = loader.load()
    
    return _config_instance


def reload_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    Reload the global configuration.
    
    Args:
        config_path: Path to configuration file.
        
    Returns:
        Config: Reloaded configuration object.
    """
    global _config_instance
    
    loader = ConfigLoader(config_path)
    _config_instance = loader.load()
    
    return _config_instance


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = get_config()
        print("Configuration loaded successfully!")
        print(f"EEG sampling rate: {config.eeg.sampling_rate} Hz")
        print(f"Number of channels: {config.eeg.n_channels}")
        print(f"P300 detection window: {config.p300.detection_window} ms")
        print(f"Flash duration: {config.stimulus.flash_duration} ms")
    except Exception as e:
        print(f"Error loading configuration: {e}")