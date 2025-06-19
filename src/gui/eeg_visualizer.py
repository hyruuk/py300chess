"""
Real-time EEG signal visualization for py300chess.

This module provides live plotting of EEG signals with event markers
for debugging and monitoring the P300 detection pipeline.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle
import time
import threading
from typing import Optional, List, Dict, Tuple
import logging
from collections import deque
import pylsl as lsl


class EEGVisualizer:
    """
    Real-time EEG signal visualizer with event markers.
    
    Displays continuous EEG data with overlays for:
    - Flash events (vertical lines)
    - P300 detections (colored markers)
    - Confidence scores (text overlay)
    - Signal quality indicators
    """
    
    def __init__(self, config):
        """Initialize the EEG visualizer."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Visualization parameters
        self.time_window = 10.0  # Display last 10 seconds
        self.sampling_rate = config.eeg.sampling_rate
        self.n_channels = config.eeg.n_channels
        self.channel_names = config.eeg.channel_names
        
        # Data buffers
        self.buffer_size = int(self.time_window * self.sampling_rate)
        self.eeg_buffer = deque(maxlen=self.buffer_size)
        self.time_buffer = deque(maxlen=self.buffer_size)
        
        # Event tracking
        self.flash_events = []  # [(time, square_name, color)]
        self.p300_events = []  # [(time, square_name, confidence)]
        self.target_square = None
        
        # LSL connections
        self.eeg_inlet = None
        self.flash_inlet = None
        self.p300_inlet = None
        self.target_inlet = None
        
        # Threading
        self.data_thread = None
        self.is_running = False
        self.data_lock = threading.Lock()
        
        # Matplotlib components
        self.fig = None
        self.axes = []
        self.lines = []
        self.animation = None
        
        # Display settings
        self.y_scale = 50.0  # μV range for display
        self.colors = {
            'eeg': '#1f77b4',
            'flash': '#ff7f0e', 
            'p300_detected': '#2ca02c',
            'p300_missed': '#d62728',
            'target_flash': '#ff1493'
        }
        
    def start(self):
        """Start the EEG visualizer."""
        if self.is_running:
            self.logger.warning("EEG visualizer already running")
            return
        
        try:
            # Connect to LSL streams
            self._connect_to_streams()
            
            # Setup matplotlib
            self._setup_plot()
            
            # Start data collection thread
            self.is_running = True
            self.data_thread = threading.Thread(
                target=self._data_collection_loop,
                name="EEGVisualizerData",
                daemon=True
            )
            self.data_thread.start()
            
            # Start animation
            self.animation = animation.FuncAnimation(
                self.fig, self._update_plot, interval=50, blit=False
            )
            
            self.logger.info("✅ EEG visualizer started")
            
            # Show the plot (blocking call)
            plt.show()
            
        except Exception as e:
            self.logger.error(f"Failed to start EEG visualizer: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the EEG visualizer."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop animation
        if self.animation:
            self.animation.event_source.stop()
        
        # Close plot
        if self.fig:
            plt.close(self.fig)
        
        # Wait for data thread
        if self.data_thread:
            self.data_thread.join(timeout=2.0)
        
        # Clean up LSL
        for inlet in [self.eeg_inlet, self.flash_inlet, self.p300_inlet, self.target_inlet]:
            if inlet:
                del inlet
        
        self.logger.info("✅ EEG visualizer stopped")
    
    def _connect_to_streams(self):
        """Connect to required LSL streams."""
        self.logger.info("Connecting to LSL streams...")
        
        # Connect to EEG stream
        try:
            streams = lsl.resolve_streams()
            eeg_stream = None
            
            for stream in streams:
                if stream.name() in ['SimulatedEEG', 'ProcessedEEG']:
                    eeg_stream = stream
                    break
            
            if not eeg_stream:
                raise RuntimeError("No EEG stream found")
            
            self.eeg_inlet = lsl.StreamInlet(eeg_stream)
            self.logger.info(f"✅ Connected to EEG: {eeg_stream.name()}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to EEG stream: {e}")
            raise
        
        # Connect to event streams (optional)
        try:
            for stream in streams:
                if stream.name() == 'ChessFlash':
                    self.flash_inlet = lsl.StreamInlet(stream)
                    self.logger.info("✅ Connected to ChessFlash")
                elif stream.name() == 'P300Detection':
                    self.p300_inlet = lsl.StreamInlet(stream)
                    self.logger.info("✅ Connected to P300Detection")
                elif stream.name() == 'ChessTarget':
                    self.target_inlet = lsl.StreamInlet(stream)
                    self.logger.info("✅ Connected to ChessTarget")
        except Exception as e:
            self.logger.warning(f"Could not connect to all event streams: {e}")
    
    def _setup_plot(self):
        """Setup matplotlib figure and axes."""
        # Create figure with subplots for each channel
        self.fig, self.axes = plt.subplots(
            self.n_channels, 1, 
            figsize=(12, 2 + 2 * self.n_channels),
            sharex=True
        )
        
        # Handle single channel case
        if self.n_channels == 1:
            self.axes = [self.axes]
        
        # Setup each subplot
        for i, ax in enumerate(self.axes):
            # Initialize empty line
            line, = ax.plot([], [], color=self.colors['eeg'], linewidth=1)
            self.lines.append(line)
            
            # Configure axis
            ax.set_ylabel(f'{self.channel_names[i]}\n(μV)', fontsize=10)
            ax.set_ylim(-self.y_scale, self.y_scale)
            ax.grid(True, alpha=0.3)
            ax.set_facecolor('#f8f8f8')
        
        # Configure bottom axis
        self.axes[-1].set_xlabel('Time (seconds)', fontsize=10)
        
        # Set title with system info
        self.fig.suptitle(
            f'py300chess - Real-Time EEG Monitor\n'
            f'Rate: {self.sampling_rate}Hz | Channels: {self.n_channels} | Window: {self.time_window}s',
            fontsize=12, fontweight='bold'
        )
        
        # Add status text area
        self.status_text = self.fig.text(
            0.02, 0.95, '', fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        )
        
        # Tight layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.85)
    
    def _data_collection_loop(self):
        """Main data collection loop."""
        self.logger.info("Starting data collection loop")
        
        try:
            while self.is_running:
                # Collect EEG data
                self._collect_eeg_data()
                
                # Collect event data
                self._collect_event_data()
                
                # Small delay to prevent busy waiting
                time.sleep(0.01)
        
        except Exception as e:
            self.logger.error(f"Data collection error: {e}")
        finally:
            self.logger.info("Data collection loop ended")
    
    def _collect_eeg_data(self):
        """Collect EEG samples from LSL stream."""
        if not self.eeg_inlet:
            return
        
        try:
            # Pull available samples
            while True:
                sample, timestamp = self.eeg_inlet.pull_sample(timeout=0.0)
                if sample is None:
                    break
                
                with self.data_lock:
                    self.eeg_buffer.append(sample)
                    self.time_buffer.append(timestamp)
        
        except Exception as e:
            self.logger.warning(f"EEG data collection error: {e}")
    
    def _collect_event_data(self):
        """Collect event markers from LSL streams."""
        current_time = time.time()
        
        # Collect flash events
        if self.flash_inlet:
            try:
                while True:
                    marker, timestamp = self.flash_inlet.pull_sample(timeout=0.0)
                    if marker is None:
                        break
                    
                    flash_info = self._parse_flash_marker(marker[0])
                    if flash_info:
                        color = self.colors['target_flash'] if flash_info['square'] == self.target_square else self.colors['flash']
                        
                        with self.data_lock:
                            self.flash_events.append((timestamp, flash_info['square'], color))
                            
                        self.logger.debug(f"Flash: {flash_info['square']} at {timestamp:.3f}s")
            except:
                pass
        
        # Collect P300 detections
        if self.p300_inlet:
            try:
                while True:
                    marker, timestamp = self.p300_inlet.pull_sample(timeout=0.0)
                    if marker is None:
                        break
                    
                    p300_info = self._parse_p300_marker(marker[0])
                    if p300_info:
                        with self.data_lock:
                            self.p300_events.append((timestamp, p300_info['square'], p300_info['confidence']))
                        
                        self.logger.info(f"P300: {p300_info['square']} confidence={p300_info['confidence']:.2f}")
            except:
                pass
        
        # Collect target updates
        if self.target_inlet:
            try:
                while True:
                    marker, timestamp = self.target_inlet.pull_sample(timeout=0.0)
                    if marker is None:
                        break
                    
                    target_info = self._parse_target_marker(marker[0])
                    if target_info:
                        with self.data_lock:
                            self.target_square = target_info['square']
                        
                        self.logger.info(f"Target: {target_info['square']}")
            except:
                pass
        
        # Clean old events (older than display window)
        cutoff_time = current_time - self.time_window
        with self.data_lock:
            self.flash_events = [(t, s, c) for t, s, c in self.flash_events if t > cutoff_time]
            self.p300_events = [(t, s, c) for t, s, c in self.p300_events if t > cutoff_time]
    
    def _update_plot(self, frame):
        """Update plot with new data (called by animation)."""
        if not self.is_running:
            return self.lines
        
        with self.data_lock:
            if len(self.eeg_buffer) < 2:
                return self.lines
            
            # Get current data
            eeg_data = np.array(list(self.eeg_buffer))
            time_data = np.array(list(self.time_buffer))
            
            # Calculate display time range
            current_time = time_data[-1] if len(time_data) > 0 else time.time()
            time_start = current_time - self.time_window
            
            # Update each channel
            for i, (line, ax) in enumerate(zip(self.lines, self.axes)):
                if i < eeg_data.shape[1]:
                    # Update line data
                    relative_time = time_data - time_start
                    line.set_data(relative_time, eeg_data[:, i])
                    
                    # Update x-axis
                    ax.set_xlim(0, self.time_window)
                    
                    # Clear old event markers
                    for patch in ax.patches[:]:
                        patch.remove()
                    for text in ax.texts[:]:
                        text.remove()
                    
                    # Draw flash events (only on first channel to avoid clutter)
                    if i == 0:
                        self._draw_events(ax, time_start, current_time)
            
            # Update status text
            self._update_status_text()
        
        return self.lines
    
    def _draw_events(self, ax, time_start, current_time):
        """Draw event markers on the plot."""
        y_min, y_max = ax.get_ylim()
        
        # Draw flash events
        for flash_time, square, color in self.flash_events:
            if time_start <= flash_time <= current_time:
                x_pos = flash_time - time_start
                
                # Vertical line for flash
                ax.axvline(x_pos, color=color, linestyle='--', alpha=0.7, linewidth=2)
                
                # Label
                ax.text(x_pos, y_max * 0.9, square, 
                       rotation=90, fontsize=8, ha='right', va='top',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor=color, alpha=0.7))
        
        # Draw P300 detections
        for p300_time, square, confidence in self.p300_events:
            if time_start <= p300_time <= current_time:
                x_pos = p300_time - time_start
                
                # Color based on confidence
                if confidence >= self.config.p300.min_confidence:
                    marker_color = self.colors['p300_detected']
                    marker = '^'  # Triangle up
                else:
                    marker_color = self.colors['p300_missed']
                    marker = 'v'  # Triangle down
                
                # Marker for P300
                ax.scatter(x_pos, y_max * 0.7, c=marker_color, 
                          marker=marker, s=100, alpha=0.8, 
                          edgecolors='black', linewidth=1)
                
                # Confidence text
                ax.text(x_pos, y_max * 0.6, f'{confidence:.2f}',
                       fontsize=8, ha='center', va='top',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor=marker_color, alpha=0.7))
    
    def _update_status_text(self):
        """Update status text display."""
        # Calculate stats
        buffer_duration = len(self.eeg_buffer) / self.sampling_rate if self.eeg_buffer else 0
        recent_flashes = len([t for t, _, _ in self.flash_events if t > time.time() - 10])
        recent_p300s = len([t for t, _, _ in self.p300_events if t > time.time() - 10])
        
        # Signal quality (simple RMS calculation)
        signal_quality = "Good"
        if self.eeg_buffer:
            latest_samples = list(self.eeg_buffer)[-100:]  # Last 100 samples
            if latest_samples:
                rms = np.sqrt(np.mean(np.array(latest_samples)**2))
                if rms > 100:
                    signal_quality = "High noise"
                elif rms < 1:
                    signal_quality = "Low signal"
        
        status_text = (
            f"Buffer: {buffer_duration:.1f}s | "
            f"Target: {self.target_square or 'None'} | "
            f"Flashes: {recent_flashes} | "
            f"P300s: {recent_p300s} | "
            f"Signal: {signal_quality}"
        )
        
        self.status_text.set_text(status_text)
    
    def _parse_flash_marker(self, marker: str) -> Optional[Dict]:
        """Parse flash marker string."""
        try:
            if marker.startswith("square_flash|"):
                parts = marker.split('|')
                if len(parts) >= 2 and parts[1].startswith('square='):
                    square = parts[1].split('=')[1]
                    return {'square': square}
        except Exception as e:
            self.logger.warning(f"Failed to parse flash marker: {marker} - {e}")
        return None
    
    def _parse_p300_marker(self, marker: str) -> Optional[Dict]:
        """Parse P300 detection marker string."""
        try:
            if marker.startswith("p300_detected|"):
                parts = marker.split('|')
                result = {}
                for part in parts[1:]:
                    if '=' in part:
                        key, value = part.split('=', 1)
                        if key == 'square':
                            result['square'] = value
                        elif key == 'confidence':
                            result['confidence'] = float(value)
                
                if 'square' in result and 'confidence' in result:
                    return result
        except Exception as e:
            self.logger.warning(f"Failed to parse P300 marker: {marker} - {e}")
        return None
    
    def _parse_target_marker(self, marker: str) -> Optional[Dict]:
        """Parse target setting marker string."""
        try:
            if marker.startswith("set_target|"):
                parts = marker.split('|')
                if len(parts) >= 2 and parts[1].startswith('square='):
                    square = parts[1].split('=')[1]
                    return {'square': square}
        except Exception as e:
            self.logger.warning(f"Failed to parse target marker: {marker} - {e}")
        return None
    
    def get_status(self) -> Dict:
        """Get visualizer status."""
        with self.data_lock:
            return {
                'is_running': self.is_running,
                'buffer_size': len(self.eeg_buffer),
                'target_square': self.target_square,
                'recent_flashes': len(self.flash_events),
                'recent_p300s': len(self.p300_events),
                'eeg_connected': self.eeg_inlet is not None,
                'events_connected': {
                    'flash': self.flash_inlet is not None,
                    'p300': self.p300_inlet is not None,
                    'target': self.target_inlet is not None
                }
            }


# Standalone execution for testing
if __name__ == "__main__":
    import sys
    import os
    import argparse
    
    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    sys.path.insert(0, project_root)
    
    from config.config_loader import get_config
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='EEG Real-Time Visualizer')
    parser.add_argument('--time-window', type=float, default=10.0,
                       help='Time window to display (seconds)')
    parser.add_argument('--y-scale', type=float, default=50.0,
                       help='Y-axis scale (microvolts)')
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("📊 py300chess - Real-Time EEG Visualizer")
    print("=" * 50)
    print("Features:")
    print("  📈 Real-time EEG signal display")
    print("  ⚡ Flash event markers")
    print("  🧠 P300 detection indicators") 
    print("  🎯 Target square highlighting")
    print("  📊 Signal quality monitoring")
    print("")
    print("Usage:")
    print("  - Flash events: Orange vertical lines")
    print("  - Target flashes: Pink vertical lines")
    print("  - P300 detected: Green triangles (up)")
    print("  - P300 missed: Red triangles (down)")
    print("  - Confidence scores shown as numbers")
    print("")
    print("Close the plot window to stop.")
    print("=" * 50)
    
    try:
        # Load configuration
        config = get_config()
        
        # Create and start visualizer
        visualizer = EEGVisualizer(config)
        
        # Override display parameters if specified
        if args.time_window:
            visualizer.time_window = args.time_window
            visualizer.buffer_size = int(visualizer.time_window * visualizer.sampling_rate)
            visualizer.eeg_buffer = deque(maxlen=visualizer.buffer_size)
            visualizer.time_buffer = deque(maxlen=visualizer.buffer_size)
        
        if args.y_scale:
            visualizer.y_scale = args.y_scale
        
        # Start visualization (blocking)
        visualizer.start()
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping EEG visualizer...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'visualizer' in locals():
            visualizer.stop()
        print("✅ EEG visualizer stopped")