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
python src/main.py
```

## Configuration

Key parameters can be adjusted in `config/settings.py`:

- `SAMPLING_RATE`: EEG sampling frequency (default: 250Hz)
- `N_CHANNELS`: Number of EEG channels (default: 1)
- `FLASH_DURATION`: Square flash duration (default: 100ms)
- `INTER_FLASH_INTERVAL`: Pause between flashes
- `P300_WINDOW`: Time window for P300 detection

## Usage

### Simulation Mode (Default)
The application starts in simulation mode, generating mock EEG data with realistic P300 responses.

### Real EEG Mode
Connect your EEG device and ensure it's streaming via LSL, then set `USE_SIMULATION = False` in settings.

### Playing Chess
1. The board displays with legal moves available
2. Squares flash in random order (100ms each)
3. Focus on your intended piece when it flashes
4. After piece selection, focus on your intended destination
5. The move executes automatically after detection
6. AI opponent responds with its move

## System Architecture

- **Chess Logic**: Handles game state, move validation, and AI opponent
- **EEG Processing**: Real-time signal processing and P300 detection
- **P300 Interface**: Manages flashing sequences and response detection
- **GUI**: Visual chess board and feedback displays

## Development

See `DEV_NOTES.md` for detailed development information and architecture notes.

## Future Enhancements

- Multi-player support
- Advanced chess engines
- Improved P300 detection algorithms
- Calibration routines for individual users
- Support for additional EEG systems

# EEG Chess P300 Project Structure

Create the following directory structure:

```
py300chess/
├── README.md
├── DEV_NOTES.md
├── requirements.txt
├── config/
│   ├── __init__.py
│   └── settings.py
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── chess_game/
│   │   ├── __init__.py
│   │   ├── chess_engine.py
│   │   ├── chess_board.py
│   │   └── move_validator.py
│   ├── eeg_processing/
│   │   ├── __init__.py
│   │   ├── lsl_stream.py
│   │   ├── signal_simulator.py
│   │   ├── epoch_extractor.py
│   │   └── p300_detector.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── chess_gui.py
│   │   ├── p300_interface.py
│   │   └── feedback_display.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── helpers.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── models/
├── tests/
│   ├── __init__.py
│   ├── test_chess.py
│   ├── test_eeg.py
│   └── test_p300.py
└── docs/
    ├── architecture.md
    └── p300_protocol.md
```

## Key Files Overview

### Core Application
- `src/main.py` - Main application entry point
- `config/settings.py` - Configuration parameters (sampling rate, channels, timing)

### Chess Module
- `chess_engine.py` - Chess logic and AI opponent
- `chess_board.py` - Board state management
- `move_validator.py` - Legal move validation

### EEG Processing Module
- `lsl_stream.py` - LSL stream handling (real and simulated)
- `signal_simulator.py` - Mock EEG data with P300 simulation
- `epoch_extractor.py` - Extract epochs based on flash markers
- `p300_detector.py` - P300 detection and confidence calculation

### GUI Module
- `chess_gui.py` - Chess board visualization
- `p300_interface.py` - P300 flashing interface
- `feedback_display.py` - Confidence and status display

### Supporting
- `utils/logger.py` - Logging system
- `utils/helpers.py` - Common utility functions