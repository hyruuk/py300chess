# Development Notes - py300chess

## Project Architecture Overview

This project implements a P300-based Brain-Computer Interface (BCI) for playing chess. The P300 is an event-related potential (ERP) that occurs ~300ms after a rare or significant stimulus.

### Core Concept
- Flash legal chess squares in random order
- User focuses on intended square
- P300 response occurs when target square flashes
- Detect P300 to identify user's intention
- Execute chess move based on detected selection

## Technical Implementation

### 1. EEG Signal Flow
```
LSL Stream → Epoch Extraction → P300 Detection → Move Selection → Chess Update
```

### 2. P300 Detection Pipeline
- **Epoching**: Extract 800ms windows around each flash marker
- **Preprocessing**: Bandpass filter (0.5-30 Hz), baseline correction
- **Feature extraction**: Average amplitude in P300 window (250-500ms)
- **Classification**: Template matching or simple threshold detection

### 3. Chess Integration
- Use `python-chess` library for game logic
- Legal move generation determines which squares to flash
- Two-phase selection: piece selection → destination selection

## Key Components

### EEG Processing (`src/eeg_processing/`)

#### `lsl_stream.py`
- Handles both real LSL streams and simulated data
- Configurable sampling rate and channel count
- Sends markers for flash events
- Multi-channel averaging when specified

#### `signal_simulator.py`
- Generates realistic EEG background noise
- Injects P300 responses at target flash events
- Configurable P300 amplitude and latency
- Simulates realistic signal-to-noise ratios

#### `epoch_extractor.py`
- Real-time epoch extraction based on markers
- Sliding buffer management
- Preprocessing (filtering, baseline correction)
- Handles multiple simultaneous epochs

#### `p300_detector.py`
- P300 detection algorithms
- Confidence calculation (amplitude, SNR, classification probability)
- Template matching against known P300 waveforms
- Real-time processing with minimal latency

### Chess Engine (`src/chess_game/`)

#### `chess_engine.py`
- Wraps chess AI (initially simple, extensible for stronger engines)
- Move generation and evaluation
- Game state management
- Future: Support for multiple engine backends

#### `chess_board.py`
- Board representation and visualization data
- Legal move calculation
- Game history tracking
- Integration with GUI display

#### `move_validator.py`
- Validates P300-detected moves against chess rules
- Handles edge cases (castling, en passant, promotion)
- Move disambiguation when multiple pieces can reach same square

### GUI System (`src/gui/`)

#### `chess_gui.py`
- Visual chess board using pygame/tkinter
- Piece rendering and board updates
- Flash animation system
- Move highlighting and selection feedback

#### `p300_interface.py`
- Manages flashing sequences
- Random flash order generation
- Timing control (100ms flashes, configurable intervals)
- Visual feedback for selected squares

#### `feedback_display.py`
- Real-time confidence indicators
- P300 amplitude visualization
- System status display
- Debug information panel

## Configuration System (`config/settings.py`)

### EEG Parameters
- `SAMPLING_RATE`: Default 250Hz, adjustable for different systems
- `N_CHANNELS`: Default 1, can average multiple channels
- `CHANNEL_NAMES`: Electrode labels for multi-channel setups

### P300 Detection
- `P300_WINDOW`: Time window for P300 detection (250-500ms typical)
- `BASELINE_WINDOW`: Pre-stimulus baseline (-200 to 0ms)
- `DETECTION_THRESHOLD`: Amplitude threshold for P300 detection
- `MIN_CONFIDENCE`: Minimum confidence for move execution

### Timing Parameters
- `FLASH_DURATION`: 100ms flash duration
- `INTER_FLASH_INTERVAL`: Pause between flashes
- `SELECTION_PAUSE`: Pause between piece and destination selection
- `FEEDBACK_DISPLAY_TIME`: How long to show confidence feedback

### Chess Configuration
- `ENGINE_STRENGTH`: AI difficulty level
- `TIME_CONTROL`: Move time limits
- `PIECE_STYLE`: Visual piece representation

## Development Workflow

### Phase 1: Core Infrastructure
1. Set up LSL streaming and simulation
2. Implement basic chess board and legal moves
3. Create flashing interface
4. Basic P300 detection with simulated data

### Phase 2: P300 Refinement
1. Improve P300 detection accuracy
2. Add confidence metrics
3. Optimize real-time performance
4. Calibration routines

### Phase 3: Chess Enhancement
1. Better chess engine integration
2. Move disambiguation
3. Game history and analysis
4. Multiple difficulty levels

### Phase 4: User Experience
1. Calibration wizard
2. Training modes
3. Performance monitoring
4. Error handling and recovery

## Testing Strategy

### Unit Tests
- Chess logic validation
- EEG signal processing accuracy
- P300 detection with known signals
- GUI component functionality

### Integration Tests
- End-to-end move selection
- Real-time performance benchmarks
- Multi-channel EEG processing
- Chess engine communication

### User Testing
- P300 detection accuracy with real users
- System usability and learning curve
- Performance with different EEG systems
- Fatigue and attention span considerations

## Performance Considerations

### Real-time Requirements
- P300 detection must complete within 1-2 seconds
- GUI updates should be smooth (30+ FPS)
- EEG processing can't introduce significant latency
- Memory usage should remain bounded

### Optimization Strategies
- Efficient epoching with circular buffers
- Pre-computed filter coefficients
- Minimal GUI redraws during flashing
- Batch processing where possible

## Future Extensions

### Multiple EEG Systems
- Muse headset integration (4 channels, 256Hz)
- DSI-24 support (24 channels, 1000Hz)
- Generic LSL stream compatibility
- Auto-detection of connected devices

### Advanced Features
- Multi-player EEG chess
- Tournament mode
- Move prediction and pre-computation
- Adaptive P300 detection thresholds
- Online learning and personalization

### Research Applications
- P300 latency and amplitude analysis
- Attention and fatigue monitoring
- BCI performance metrics
- Data collection for algorithm improvement

## Common Issues and Solutions

### Low P300 Detection Accuracy
- Check electrode placement and signal quality
- Adjust detection thresholds
- Increase flash duration or contrast
- Implement user-specific calibration

### Real-time Performance Issues
- Optimize signal processing pipeline
- Reduce GUI update frequency during flashing
- Use multiprocessing for CPU-intensive tasks
- Profile and identify bottlenecks

### Chess Engine Integration
- Ensure proper move notation conversion
- Handle special moves (castling, promotion)
- Validate all engine responses
- Implement fallback for engine failures

## Dependencies and Requirements

### Core Libraries
- `pylsl`: Lab Streaming Layer integration
- `python-chess`: Chess game logic
- `numpy`: Signal processing
- `scipy`: Digital filtering
- `pygame`: GUI and graphics
- `threading`: Real-time processing

### Optional Enhancements
- `sklearn`: Advanced P300 classification
- `mne`: Professional EEG analysis
- `matplotlib`: Signal visualization
- `psychopy`: Stimulus presentation

## Getting Started for New Developers

1. **Understand P300**: Read about event-related potentials and BCI
2. **Test simulation mode**: Run with mock EEG data first
3. **Study chess integration**: Understand legal move generation
4. **Examine flashing logic**: How squares are selected and timed
5. **Debug with confidence metrics**: Monitor system performance
6. **Iterate on detection**: Improve P300 accuracy gradually

## Code Style and Standards

- Follow PEP 8 for Python code formatting
- Use type hints for function signatures
- Document all public methods and classes
- Include unit tests for new functionality
- Log important events and errors
- Handle exceptions gracefully

This architecture provides a solid foundation for P300-based chess control while remaining extensible for future enhancements and different EEG systems.