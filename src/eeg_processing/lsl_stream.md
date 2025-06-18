# LSL Stream Module

The LSL (Lab Streaming Layer) module provides continuous EEG data streaming with P300 response generation for the py300chess system.

## Overview

This module handles real-time EEG data streaming and communicates with the chess system via LSL markers. It runs as a **server process** that continuously streams EEG data and responds to chess game events with perfect P300 responses.

## Components

### LSLEEGStreamer
Main class for continuous EEG data streaming via LSL.

**Features:**
- Continuous EEG simulation at configured sample rate (default 250Hz)
- Real-time LSL streaming with 40ms chunks for smooth data flow
- Perfect P300 generation when target squares are flashed
- Support for both simulated and real EEG devices

### LSLMarkerStream
Generic LSL marker sender for event communication.

**Usage:**
- Send chess game events (flashes, moves, etc.)
- Timestamp synchronization
- Multiple marker types support

### LSLMarkerListener  
Generic LSL marker receiver for event communication.

**Usage:**
- Listen for chess commands and stimuli
- Threaded operation for real-time response
- Configurable callback functions

## Data Flow

```
Chess Engine → ChessTarget → LSL → P300 System
Chess GUI → ChessFlash → LSL → P300 System  
P300 System → P300Response → LSL → Chess System
```

## LSL Stream Channels

### Input Streams (P300 System Listens)

**ChessTarget**
- **Purpose**: Chess engine tells P300 system which square to focus on
- **Format**: `set_target|square=e4`
- **Example**: When chess engine decides to move to e4

**ChessFlash** 
- **Purpose**: GUI announces when squares are flashed
- **Format**: `square_flash|square=e4`
- **Example**: When e4 square lights up during move selection

### Output Streams (P300 System Sends)

**SimulatedEEG**
- **Purpose**: Continuous EEG data stream
- **Format**: Multi-channel float32 samples at configured rate
- **Channels**: Configurable (default: Cz)
- **Sample Rate**: Configurable (default: 250Hz)

**P300Response**
- **Purpose**: P300 detection results
- **Format**: `p300_detected|square=e4|confidence=1.0`
- **Example**: When target square flashes and P300 is detected

## Running the System

### Continuous Server Mode

```bash
cd src/eeg_processing
python lsl_stream.py
```

**Output:**
```
🧠 Starting P300 EEG System...
==================================================
Starting EEG streaming...
Connecting to chess communication channels...
✅ Listening for target commands on 'ChessTarget'
⚠️  No chess flash stream found (GUI not running)

🎮 P300 System Ready!
Waiting for chess system commands...
📊 Streaming: 45.2s | Target: None
```

The system will:
- ✅ **Stream continuously** until Ctrl+C
- ✅ **Listen for chess commands** (target setting, square flashes)
- ✅ **Generate perfect P300 responses** when target matches flash
- ✅ **Show real-time status** updates

### Manual Testing

Test the system manually from another terminal:

#### Set Target Square
```bash
python -c "
import pylsl
outlet = pylsl.StreamOutlet(pylsl.StreamInfo('ChessTarget','Markers',1,pylsl.IRREGULAR_RATE,pylsl.cf_string))
outlet.push_sample(['set_target|square=e4'])
"
```

#### Flash Target Square (Should Trigger P300)
```bash
python -c "
import pylsl
outlet = pylsl.StreamOutlet(pylsl.StreamInfo('ChessFlash','Markers',1,pylsl.IRREGULAR_RATE,pylsl.cf_string))
outlet.push_sample(['square_flash|square=e4'])
"
```

#### Flash Non-Target Square (Should Not Trigger P300)
```bash
python -c "
import pylsl
outlet = pylsl.StreamOutlet(pylsl.StreamInfo('ChessFlash','Markers',1,pylsl.IRREGULAR_RATE,pylsl.cf_string))
outlet.push_sample(['square_flash|square=d4'])
"
```

### Expected Behavior

When target square flashes:
```
🎯 Target set to: e4
⚡ TARGET FLASH: e4 - generating P300!
```

When non-target square flashes:
```
   Non-target flash: d4
```

## Configuration

All parameters are controlled via `config.yaml`:

```yaml
eeg:
  sampling_rate: 250        # EEG sample rate (Hz)
  n_channels: 1            # Number of channels
  channel_names: ["Cz"]    # Electrode names
  use_simulation: true     # Use simulation vs real EEG

simulation:
  p300_amplitude: 5.0      # P300 response amplitude (μV)
  p300_latency: 300        # P300 delay after stimulus (ms)
  noise_amplitude: 10.0    # Background EEG noise (μV)
  p300_probability: 1.0    # Perfect responses (1.0 = 100%)
```

## Integration with Chess System

### Chess Engine Integration
The chess engine should:
1. **Send target commands** when deciding on a move
2. **Listen for P300 responses** to detect selected moves

```python
# Chess engine sends target
target_stream.send_marker("set_target|square=e4")

# Chess engine waits for P300 response
# Response: "p300_detected|square=e4|confidence=1.0"
```

### GUI Integration
The chess GUI should:
1. **Send flash markers** when squares light up
2. **Coordinate timing** with P300 detection

```python
# GUI flashes square
flash_stream.send_marker("square_flash|square=e4")
time.sleep(0.1)  # Flash duration

# GUI waits for P300 response before next flash
```

## Debugging

### Check LSL Streams
View all active LSL streams:
```bash
python -c "import pylsl; print([s.name() for s in pylsl.resolve_streams()])"
```

### Monitor EEG Data
Connect to EEG stream and view data:
```python
import pylsl
import numpy as np

# Connect to EEG stream
streams = pylsl.resolve_stream('name', 'SimulatedEEG')
inlet = pylsl.StreamInlet(streams[0])

# Read samples
for i in range(100):
    sample, timestamp = inlet.pull_sample()
    print(f"Sample {i}: {sample} at {timestamp:.3f}s")
```

### Troubleshooting

**No chess streams found:**
- Chess engine/GUI not running
- Stream names don't match
- LSL networking issues

**P300 not generated:**
- Target not set (`set_target` command not sent)
- Square names don't match exactly
- Simulation disabled in config

**Streaming performance issues:**
- Reduce chunk size in config
- Check system CPU usage
- Verify LSL installation

## Performance

- **Latency**: < 50ms from stimulus to P300 marker
- **Throughput**: 250 samples/sec × 4 bytes × channels
- **Memory**: < 10MB typical usage
- **CPU**: < 5% on modern systems

## Next Steps

This module provides the foundation for:
1. **P300 Detection** (`src/eeg_processing/p300_detector.py`)
2. **Chess GUI** (`src/gui/p300_interface.py`) 
3. **Chess Engine** (`src/chess_game/chess_engine.py`)
4. **Complete System** (`main.py`)

The LSL streaming system is ready to integrate with these components as they're developed.