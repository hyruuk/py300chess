# py300chess

A chess game controlled by EEG signals using the P300 evoked response paradigm. Players select chess moves by focusing on specific squares while they flash, triggering detectable P300 responses in the EEG signal.

## Overview

This application uses the P300 speller approach adapted for chess:
1. Display legal chess moves by flashing possible squares
2. Detect P300 responses when the intended square is flashed
3. Use triangulation to identify the selected piece and destination
4. Execute the chess move and respond with an AI opponent

## Features

- **P300-based move selection**: Select chess pieces and destinations using EEG
- **Real-time EEG processing**: Process LSL streams with configurable parameters
- **Chess engine integration**: Play against an AI opponent
- **Visual feedback**: Real-time confidence indicators and system status
- **Simulation mode**: Test without EEG hardware using simulated signals
- **Flexible EEG setup**: Support for single or multi-channel configurations
- **Modular architecture**: Independent components that can be mixed and matched

## Requirements

- Python 3.8+
- EEG headset with LSL streaming capability (optional - simulation mode available)
- See `requirements.txt` for Python dependencies

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd py300chess
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Quick Start

### Using Simulated EEG (No Hardware Required)

1. **Start the simulated EEG streamer:**
```bash
cd src/eeg_processing
python signal_simulator.py
```

2. **Test P300 responses manually:**
```bash
# In another terminal - set target square:
python -c "import pylsl; outlet=pylsl.StreamOutlet(pylsl.StreamInfo('ChessTarget','Markers',1,pylsl.IRREGULAR_RATE,pylsl.cf_string)); outlet.push_sample(['set_target|square=e4'])"

# Flash the target square (should generate P300):
python -c "import pylsl; outlet=pylsl.StreamOutlet(pylsl.StreamInfo('ChessFlash','Markers',1,pylsl.IRREGULAR_RATE,pylsl.cf_string)); outlet.push_sample(['square_flash|square=e4'])"
```

3. **For clean EEG without P300 responses:**
```bash
python signal_simulator.py --standalone --no-p300
```

### Using Real EEG Hardware

1. **Connect your EEG device** and ensure it's streaming via LSL

2. **Start the real EEG handler:**
```bash
cd src/eeg_processing
python lsl_stream.py
```

3. **The system will discover and connect** to available EEG devices automatically

## Configuration

The system is configured via `config.yaml`. Key parameters:

### EEG Settings
```yaml
eeg:
  sampling_rate: 250        # EEG sampling frequency (Hz)
  n_channels: 1            # Number of EEG channels
  channel_names: ["Cz"]    # Electrode positions
  use_simulation: true     # Use simulated data vs real EEG
```

### P300 Detection
```yaml
p300:
  detection_window: [250, 500]  # P300 detection window (ms)
  baseline_window: [-200, 0]   # Baseline correction window (ms)
  detection_threshold: 2.0     # Amplitude threshold (μV)
  min_confidence: 0.6          # Minimum confidence for move execution
```

### Stimulus Presentation
```yaml
stimulus:
  flash_duration: 100          # Square flash duration (ms)
  inter_flash_interval: 200    # Pause between flashes (ms)
  flash_repetitions: 3         # Number of flashes per square
```

## System Architecture

The system uses a **modular, LSL-based architecture** with independent components:

### Core Components

- **`signal_simulator.py`**: Generates realistic EEG with P300 responses
- **`lsl_stream.py`**: Handles real EEG hardware connections  
- **`p300_detector.py`**: Detects P300 responses in EEG streams *(TODO)*
- **`chess_engine.py`**: Chess AI and game logic *(TODO)*
- **`chess_gui.py`**: Visual chess board and square flashing *(TODO)*

### LSL Data Flow

```
Chess Engine → ChessTarget → LSL → Signal Simulator
Chess GUI → ChessFlash → LSL → Signal Simulator
Signal Simulator → SimulatedEEG → LSL → P300 Detector
Real EEG → lsl_stream.py → ProcessedEEG → LSL → P300 Detector
P300 Detector → P300Response → LSL → Chess System
```

### Modular Usage

**For Testing:** `signal_simulator.py` + P300 detector  
**For Real BCI:** `lsl_stream.py` + P300 detector  
**For Development:** Mix and match components as needed  

## Development Status

### ✅ **Completed**
- **EEG Signal Simulation**: Realistic brain signals with P300 responses
- **LSL Streaming**: Continuous data streaming for both real and simulated EEG
- **Configuration System**: Comprehensive YAML-based configuration
- **Modular Architecture**: Independent components communicating via LSL

### 🔧 **In Progress**
- **P300 Detection**: Algorithm to detect P300 responses in EEG data
- **Chess Engine**: AI opponent and game logic
- **Chess GUI**: Visual board with square flashing interface

### 📋 **Planned**
- **Complete Integration**: Full P300-controlled chess gameplay
- **Calibration System**: User-specific P300 detection tuning
- **Performance Analysis**: BCI accuracy and timing metrics
- **Multi-player Support**: P300 vs P300 chess matches

## Usage Examples

### Standalone EEG Streaming
```bash
# Clean EEG signals without chess integration
python signal_simulator.py --standalone

# EEG with verbose output
python signal_simulator.py --standalone --verbose

# Pure background EEG (no P300 responses)
python signal_simulator.py --standalone --no-p300
```

### Real EEG Device Discovery
```bash
# Scan for and test EEG hardware
python lsl_stream.py
```

### Manual Testing
```bash
# Start simulator
python signal_simulator.py

# Set target and test P300 generation
python -c "import pylsl; outlet=pylsl.StreamOutlet(pylsl.StreamInfo('ChessTarget','Markers',1,pylsl.IRREGULAR_RATE,pylsl.cf_string)); outlet.push_sample(['set_target|square=e4'])"
python -c "import pylsl; outlet=pylsl.StreamOutlet(pylsl.StreamInfo('ChessFlash','Markers',1,pylsl.IRREGULAR_RATE,pylsl.cf_string)); outlet.push_sample(['square_flash|square=e4'])"
```

## Project Structure

```
py300chess/
├── README.md                    # This file
├── DEV_NOTES.md                # Development documentation
├── logbook.md                  # Development progress log
├── config.yaml                 # Main configuration file
├── requirements.txt            # Python dependencies
├── main.py                     # Main application entry point
├── src/
│   ├── eeg_processing/
│   │   ├── signal_simulator.py    # ✅ Simulated EEG with P300
│   │   ├── lsl_stream.py          # ✅ Real EEG hardware interface
│   │   ├── p300_detector.py       # 🔧 P300 detection algorithms
│   │   └── epoch_extractor.py     # 🔧 EEG epoch extraction
│   ├── chess_game/
│   │   ├── chess_engine.py        # 🔧 Chess AI and game logic
│   │   ├── chess_board.py         # 🔧 Board representation
│   │   └── move_validator.py      # 🔧 Move validation
│   ├── gui/
│   │   ├── chess_gui.py           # 🔧 Visual chess board
│   │   ├── p300_interface.py      # 🔧 Square flashing interface
│   │   └── feedback_display.py    # 🔧 Real-time feedback
│   └── utils/
│       ├── logger.py              # 🔧 Logging system
│       └── helpers.py             # 🔧 Utility functions
├── config/
│   └── config_loader.py           # ✅ Configuration management
├── data/
│   ├── raw/                       # Raw EEG recordings
│   ├── processed/                 # Processed data
│   └── models/                    # Trained models
└── tests/                         # Unit tests
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature-name`
3. **Make your changes** following the existing code style
4. **Add tests** for new functionality
5. **Submit a pull request**

## Development Workflow

### Phase 1: Core Infrastructure ✅
- [x] EEG signal simulation with P300 responses
- [x] LSL streaming for real and simulated data
- [x] Configuration system and project structure
- [x] Modular architecture design

### Phase 2: P300 Processing 🔧
- [ ] P300 detection algorithms
- [ ] Real-time signal processing
- [ ] Confidence metrics and validation
- [ ] Performance optimization

### Phase 3: Chess Integration 📋
- [ ] Chess engine and game logic
- [ ] Visual interface with square flashing
- [ ] Move selection and validation
- [ ] Complete P300-to-chess pipeline

### Phase 4: Enhancement 📋
- [ ] User calibration routines
- [ ] Performance monitoring
- [ ] Multi-player capabilities
- [ ] Advanced analytics

## Troubleshooting

### EEG Streaming Issues
- **No EEG data**: Check LSL connections and device status
- **High latency**: Reduce chunk size in configuration
- **Connection errors**: Verify device is streaming via LSL

### P300 Detection Problems
- **Low accuracy**: Adjust detection thresholds in config
- **No responses**: Check electrode placement and signal quality
- **False positives**: Increase minimum confidence threshold

### Performance Issues
- **Memory usage**: Monitor for data buffer overflow
- **CPU usage**: Optimize real-time processing chunks
- **Network issues**: Check LSL stream networking

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Future Enhancements

- **Multiple EEG Systems**: Support for various EEG devices (Muse, OpenBCI, DSI)
- **Advanced P300 Detection**: Machine learning-based classification
- **Online Learning**: Adaptive algorithms that improve with use
- **Tournament Mode**: Competitive P300 chess gameplay
- **Research Tools**: Data collection and analysis for BCI research

## Acknowledgments

- **Lab Streaming Layer (LSL)**: Real-time data streaming
- **python-chess**: Chess game logic and validation
- **NumPy/SciPy**: Signal processing and mathematics
- **PyGame**: GUI and visualization

For detailed development information, see [DEV_NOTES.md](DEV_NOTES.md).  
For daily progress updates, see [logbook.md](logbook.md).