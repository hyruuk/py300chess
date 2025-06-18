Key Configuration Sections:

EEG: Sampling rate, channels, simulation mode
P300: Detection windows, thresholds, filtering
Stimulus: Flash timing, colors, repetitions
Chess: Engine strength, time limits, rules
GUI: Window size, display settings
Feedback: Debug mode, confidence display
Simulation: P300 response parameters, noise levels
Recording: Data logging options

Usage Examples:
pythonfrom config.config_loader import get_config

# Load config (automatically finds config.yaml)
config = get_config()

# Access parameters
sampling_rate = config.eeg.sampling_rate
flash_duration = config.stimulus.flash_duration
p300_threshold = config.p300.detection_threshold
Environment variables can override any setting:
bashexport PY300_SAMPLING_RATE=500
export PY300_USE_SIMULATION=false
python src/main.py