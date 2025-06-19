# Development Notes - py300chess

## Current Status

### ✅ **What Currently Works and is Tested**
- **Main Application**: Complete component management with multi-terminal support
- **EEG Signal Simulation**: Realistic brain signals with perfect P300 responses
- **LSL Streaming**: Continuous data streaming for both real and simulated EEG
- **Real EEG Hardware**: Auto-discovery and connection to LSL-compatible devices
- **P300 Detection Algorithm**: Template matching with confidence scoring (CODE COMPLETE)
- **Configuration System**: Comprehensive YAML-based configuration with hot-reload
- **Interactive CLI**: Built-in testing, monitoring, and configuration commands
- **Real-time EEG Visualization**: Live signal plotting with event markers ✅ **NEW**

### ⚠️ **Known Issues or Blockers**
- **P300 Detection Performance**: Algorithm implemented but **NOT YET VALIDATED** - needs actual testing
- **Chess Components Missing**: Chess engine and GUI not yet implemented
- **Visualization Dependencies**: Requires matplotlib (graceful fallback if missing)

### 🎯 **Immediate Next Steps**
1. **Test P300 detection with visualization** - Use new EEG visualizer to validate algorithm performance
2. **Measure actual performance metrics** - Latency, accuracy, reliability with visual feedback
3. **Implement chess square flashing interface** - Build GUI component for move selection
4. **Complete chess engine integration** - Add game logic and AI opponent

### 📋 **Important Context for Resuming Work**
- **Visualization system complete** - Real-time EEG plotting with event markers ready for validation
- **Debug mode enhanced** - Now spawns 4 terminals including EEG visualizer
- **Performance validation tools ready** - Can now see P300 detection in real-time
- **Next priority**: Validate P300 detection algorithm using the new visualization

---

## Project Architecture Overview

This project implements a P300-based Brain-Computer Interface (BCI) for playing chess. The P300 is an event-related potential (ERP) that occurs ~300ms after a rare or significant stimulus.

### Core Concept
- Flash legal chess squares in random order
- User focuses on intended square
- P300 response occurs when target square flashes
- Detect P300 to identify user's intention
- Execute chess move based on detected selection

## Technical Implementation

### 1. **Main Application Architecture**

The main.py file provides comprehensive component management with two distinct operating modes:

#### **Single Terminal Mode (Default)**
```
┌─────────────────────────────────────────────────────────┐
│                   Main Terminal                         │
│                                                         │
│  🎮 py300chess Interactive Mode                        │
│  Commands: status, config, test, reload, quit          │
│                                                         │
│  py300chess> test                                       │
│  py300chess> status                                     │
│                                                         │
│  [All components run in same process]                   │
│  [Clean CLI interface for end users]                    │
└─────────────────────────────────────────────────────────┘
```

#### **Multi-Terminal Debug Mode (`--debug`)** ✅ **ENHANCED**
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Main Terminal │  │  EEG Simulator  │  │ P300 Detector   │  │ EEG Visualizer  │
│                 │  │                 │  │                 │  │                 │
│ py300chess>     │  │ 📊 Streaming    │  │ 🧠 Detecting    │  │ 📈 Live Plot    │
│ Interactive CLI │  │ EEG: 250Hz      │  │ Confidence: 0.85│  │ Flash markers   │
│                 │  │ P300: Generated │  │ Target: e4      │  │ P300 events     │
│ Commands:       │  │ Target: e4      │  │ LSL: Connected  │  │ Signal quality  │
│ - status        │  │ LSL: Streaming  │  │ Epochs: 15      │  │ Real-time data  │
│ - test          │  │ Time: 45.2s     │  │ Detections: 3   │  │                 │
│ - config        │  │                 │  │                 │  │ [Scrolling EEG] │
│ - quit          │  │ Real-time logs  │  │ Real-time logs  │  │ [Event markers] │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 2. **LSL-Based Architecture**

The modular LSL architecture includes proper component management:

```
┌─────────────────────────────────────────────────────────────┐
│                      Main Application                      │
│                        (main.py)                           │
│                                                             │
│  ✅ Component Lifecycle Management                         │
│  ✅ Health Monitoring & Status Reporting                   │
│  ✅ Interactive CLI (status, test, config, reload)         │
│  ✅ Multi-Terminal Debug Mode                              │
│  ✅ Graceful Startup/Shutdown                              │
│  ✅ Cross-Platform Terminal Spawning                       │
│  ✅ Real-time EEG Visualization (NEW)                      │
└─────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chess Engine  │    │   Chess GUI     │    │ EEG Components  │
│                 │    │                 │    │                 │
│ - Game logic    │    │ - Square flash  │    │ - Signal sim    │
│ - AI opponent   │    │ - Visual board  │    │ - Real EEG      │
│ - Move planning │    │ - User feedback │    │ - P300 detect   │
└─────────────────┘    └─────────────────┘    │ - Visualization │
         │                       │            └─────────────────┘
         └───────────────────────┼───────────────────────┘
                                 │
                         ┌───────▼────────┐
                         │  LSL Streaming │
                         │                │
                         │ - ChessTarget  │
                         │ - ChessFlash   │
                         │ - SimulatedEEG │
                         │ - ProcessedEEG │
                         │ - P300Detection│
                         └────────────────┘
```

### 3. **Component Management Features**

#### **Main Application Features**
- **Intelligent Startup**: Components start in correct dependency order
- **Health Monitoring**: Real-time status tracking with `status` command
- **Graceful Shutdown**: Clean termination of all components on Ctrl+C
- **Error Resilience**: System continues even if individual components fail
- **Hot Configuration Reload**: Update settings without restart using `reload`
- **Built-in Testing**: Automated P300 pipeline validation with `test`
- **Real-time Visualization**: Live EEG plotting with event markers ✅ **NEW**

#### **Multi-Platform Terminal Support**
- **Windows**: Uses `cmd` with `start` command
- **macOS**: Uses `osascript` to control Terminal app  
- **Linux**: Auto-detects terminals (gnome-terminal, konsole, xterm, alacritty, terminator)
- **Fallback**: Gracefully falls back to single-terminal mode if spawning fails

## Key Components (Current Implementation Status)

### ✅ **Main Application (`main.py`) - COMPLETED**

#### **Key Features**
- **Multi-Mode Operation**: `full`, `eeg_only`, `simulation`, `hardware`, `chess_only`
- **Interactive CLI**: Built-in commands for system management
- **Debug Mode**: `--debug` flag enables multi-terminal development mode + visualization
- **Component Health**: Real-time monitoring and status reporting
- **Cross-Platform**: Windows, macOS, and Linux terminal support
- **Graceful Error Handling**: Continues operation despite component failures

#### **Usage Examples**
```bash
# Clean single-terminal mode (default)
python main.py --mode eeg_only

# Multi-terminal debug mode with visualization
python main.py --mode eeg_only --debug

# Full system (when chess components ready)
python main.py --mode full --debug

# Headless operation
python main.py --mode eeg_only --headless --duration 300
```

#### **Interactive Commands**
- `status` - Detailed system and component health
- `config` - Current configuration display
- `test` - Automated P300 pipeline testing
- `reload` - Hot-reload configuration from file
- `quit` - Graceful system shutdown

### ✅ **EEG Processing (`src/eeg_processing/`) - COMPLETED**

#### `signal_simulator.py` - **PRODUCTION READY**
- **Purpose**: Generates realistic EEG signals with perfect P300 responses
- **Features**:
  - Continuous LSL streaming of simulated EEG data
  - Realistic background brain rhythms (alpha, beta, theta, gamma)
  - Perfect P300 generation when target squares flash
  - Configurable noise levels and P300 parameters
  - Standalone mode for pure EEG streaming
  - Integration with main application
- **Terminal Mode**: Shows real-time streaming status and P300 generation
- **LSL Streams**:
  - **Outputs**: `SimulatedEEG`, `P300Response`
  - **Inputs**: `ChessTarget`, `ChessFlash`

#### `lsl_stream.py` - **PRODUCTION READY**
- **Purpose**: Interface to real EEG hardware devices
- **Features**:
  - Auto-discovery of LSL-compatible EEG devices
  - Real-time data processing and filtering
  - Channel adaptation (handle different channel counts)
  - Connection testing and status monitoring
  - Device manager for scanning and testing connections
- **Supported Devices**: Any LSL-compatible EEG (Muse, OpenBCI, DSI, etc.)
- **Terminal Mode**: Shows device connection status and data quality
- **LSL Streams**:
  - **Outputs**: `ProcessedEEG`
  - **Inputs**: Hardware EEG device streams

#### `p300_detector.py` - **IMPLEMENTATION COMPLETE (TESTING NEEDED)**
- **Purpose**: Real-time P300 detection in EEG streams
- **Features**:
  - Template matching for P300 detection
  - Confidence calculation and thresholding
  - Real-time processing with designed low latency
  - Bandpass filtering and baseline correction
  - Configurable detection parameters
  - Integration with main application testing
- **Terminal Mode**: Shows real-time P300 detections with confidence scores
- **LSL Streams**:
  - **Inputs**: `SimulatedEEG` or `ProcessedEEG`, `ChessFlash`
  - **Outputs**: `P300Detection`
- **Status**: ⚠️ **ALGORITHM COMPLETE - PERFORMANCE VALIDATION NEEDED**

### ✅ **EEG Visualization (`src/gui/eeg_visualizer.py`) - COMPLETED** ✅ **NEW**

#### **Real-time EEG Visualization System**
- **Purpose**: Live EEG signal plotting with event markers for validation and debugging
- **Features**:
  - **Scrolling EEG Display**: Last 10 seconds of continuous signal
  - **Event Markers**: 
    - Flash events: Orange vertical lines
    - Target flashes: Pink vertical lines
    - P300 detections: Green triangles ↑ (detected) or red triangles ↓ (missed)
    - Confidence scores: Numerical values next to P300 markers