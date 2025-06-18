# EEG Signal Simulator

The EEG Signal Simulator generates realistic brain signals with P300 responses for testing the py300chess system without requiring actual EEG hardware.

## Overview

The simulator creates authentic EEG-like signals including:
- **Background brain rhythms** (alpha, beta, theta, gamma waves)
- **P300 event-related potentials** triggered by stimulus markers
- **Realistic artifacts** (eye blinks, muscle activity)
- **Configurable noise levels** and response parameters

## Key Components

### EEGSignalSimulator Class

The main simulator class that generates continuous EEG data with configurable parameters.

#### Initialization
```python
from config.config_loader import get_config
from src.eeg_processing.signal_simulator import EEGSignalSimulator

config = get_config()
simulator = EEGSignalSimulator(config)
```

#### Basic Usage
```python
# Generate baseline EEG (1 second at 250Hz)
data, times = simulator.generate_samples(250)
print(f"Generated {len(data)} samples: {data.shape}")
print(f"Signal range: {data.min():.2f} to {data.max():.2f} μV")

# Flash a chess square (target stimulus)
simulator.add_stimulus_marker(is_target=True)

# Generate more data to capture P300 response (2 seconds)
post_stimulus_data, post_times = simulator.generate_samples(500)
print(f"Post-stimulus data: {post_stimulus_data.shape}")
```

## Configuration Parameters

All simulation parameters are controlled through `config.yaml`:

### EEG Settings
```yaml
eeg:
  sampling_rate: 250        # Hz
  n_channels: 1            # Number of channels
  channel_names: ["Cz"]    # Electrode names
```

### Simulation Parameters
```yaml
simulation:
  noise_amplitude: 10.0     # Background noise (μV RMS)
  p300_amplitude: 5.0       # P300 response (μV)
  p300_latency: 300         # P300 delay (ms)
  p300_width: 100           # P300 duration (ms)
  p300_probability: 0.8     # Target response rate (0-1)
  add_artifacts: true       # Include eye blinks, muscle
  artifact_rate: 0.1        # Artifacts per second
```

## Signal Components

### Background EEG Rhythms

The simulator generates realistic brain wave patterns:

- **Alpha waves (8-12 Hz)**: Dominant resting rhythm (60% of noise amplitude)
- **Beta waves (13-30 Hz)**: Mental activity (30% of noise amplitude)  
- **Theta waves (4-8 Hz)**: Drowsiness/meditation (20% of noise amplitude)
- **Gamma waves (40+ Hz)**: High-frequency activity (10% of noise amplitude)

Each rhythm includes:
- Natural frequency drift
- Amplitude modulation
- Random phase offsets between channels

### P300 Event-Related Potentials

P300 responses are generated when:
1. `add_stimulus_marker(is_target=True)` is called
2. Random probability check passes (`p300_probability`)
3. Sufficient time has elapsed since stimulus

P300 characteristics:
- **Latency**: ~300ms after stimulus (configurable)
- **Waveform**: Gamma function shape (rapid rise, slow decay)
- **Amplitude**: Positive deflection (configurable)
- **Variability**: ±20ms latency jitter, ±20% amplitude variation

### Artifacts

When `add_artifacts=true`, the simulator includes:

**Eye Blinks**:
- Large amplitude deflections (~5x noise level)
- ~200ms duration with exponential decay
- Strongest in frontal electrodes (Fp1, Fp2, F3, F4)
- Configurable rate (default: 0.1/second)

**Muscle Artifacts**:
- High-frequency bursts (~50ms duration)
- 2x noise amplitude
- Random occurrence (50% of artifact rate)
- Affects all channels equally

## Advanced Features

### Focus Simulation
```python
# Simulate user attention state
simulator.set_target_focus(True)   # Increases P300 probability
simulator.set_target_focus(False)  # Decreases P300 probability
```

### Multi-Channel Support
```python
# Configure multiple channels in config.yaml
eeg:
  n_channels: 4
  channel_names: ["Cz", "C3", "C4", "Pz"]
```

P300 responses are weighted by electrode location:
- **Central/Parietal** (Cz, C3, C4, Pz): Full amplitude
- **Other locations**: 70% amplitude

### State Management
```python
# Get current simulation time
current_time = simulator.get_current_time()

# Reset simulator state
simulator.reset()
```

## Testing and Validation

### P300TestSignalGenerator

For debugging P300 detection algorithms, use the simplified test generator:

```python
from src.eeg_processing.signal_simulator import P300TestSignalGenerator

test_gen = P300TestSignalGenerator(sampling_rate=250, p300_amplitude=10.0)
clean_signal, times = test_gen.generate_clean_p300(duration=1.0, trigger_time=0.2)
print(f"Clean P300 peak: {clean_signal.max():.2f} μV")
```

This generates minimal-noise signals with clear P300 responses for algorithm development.

### Example Test Workflow

```python
# 1. Initialize simulator
config = get_config()
simulator = EEGSignalSimulator(config)

# 2. Generate baseline period
baseline_data, baseline_times = simulator.generate_samples(125)  # 0.5s

# 3. Present stimulus
simulator.add_stimulus_marker(is_target=True)
print(f"Stimulus presented at {simulator.get_current_time():.3f}s")

# 4. Capture response
response_data, response_times = simulator.generate_samples(250)  # 1.0s

# 5. Analyze combined signal
all_data = np.vstack([baseline_data, response_data])
all_times = baseline_times + response_times

print(f"Total signal: {len(all_data)} samples")
print(f"Amplitude range: {all_data.min():.2f} to {all_data.max():.2f} μV")
print(f"Standard deviation: {all_data.std():.2f} μV")
```

## Integration with Chess System

The simulator is designed to integrate with the chess flashing interface:

```python
# Chess square flashing sequence
squares_to_flash = ['e4', 'e5', 'd4', 'f4']  # Legal moves
target_square = 'e4'  # Square user is focusing on

for square in squares_to_flash:
    # Flash square visually (GUI code)
    flash_square(square)
    
    # Mark stimulus in EEG
    is_target = (square == target_square)
    simulator.add_stimulus_marker(is_target=is_target)
    
    # Generate EEG data during flash
    flash_data, flash_times = simulator.generate_samples(25)  # 100ms flash
    
    # Process data for P300 detection
    # ... (P300 detection code)
```

## Performance Considerations

- **Memory usage**: Simulator maintains minimal state (only recent P300 events)
- **Thread safety**: All methods are thread-safe for real-time applications
- **Computational cost**: ~0.1ms per sample on modern hardware
- **Real-time capability**: Can generate data faster than real-time

## Debugging and Monitoring

Enable debug logging to monitor simulator behavior:

```yaml
feedback:
  debug_mode: true
  log_level: "DEBUG"
```

Debug output includes:
- Stimulus marker timing
- P300 generation events
- Focus state changes
- Signal statistics

## Next Steps

With the signal simulator working, you can now:

1. **Implement LSL streaming** to feed simulated data into the processing pipeline
2. **Develop P300 detection** algorithms using the realistic test signals
3. **Create epoch extraction** to segment data around stimulus markers
4. **Test chess integration** by connecting stimulus markers to square flashing

The simulator provides a solid foundation for developing and testing the entire P300-based chess control system.