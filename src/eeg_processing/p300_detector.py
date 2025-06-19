"""
Real-time P300 detection for py300chess.

This module processes continuous EEG streams and detects P300 responses
triggered by chess square flashing. It uses template matching and
confidence scoring to identify user intentions.
"""

import numpy as np
import time
import threading
from typing import Optional, List, Dict, Callable
import logging
from collections import deque
from scipy import signal
import pylsl as lsl


class P300Detector:
    """
    Real-time P300 detection from EEG streams.
    
    Processes continuous EEG data and identifies P300 responses
    when target squares are flashed during chess gameplay.
    """
    
    def __init__(self, config):
        """
        Initialize P300 detector.
        
        Args:
            config: Configuration object with P300 parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # EEG parameters
        self.sampling_rate = config.eeg.sampling_rate
        self.n_channels = config.eeg.n_channels
        
        # P300 detection parameters
        self.detection_window = config.p300.detection_window  # [250, 500] ms
        self.baseline_window = config.p300.baseline_window    # [-200, 0] ms
        self.epoch_length = config.p300.epoch_length         # 800 ms
        self.detection_threshold = config.p300.detection_threshold  # 2.0 μV
        self.min_confidence = config.p300.min_confidence     # 0.6
        
        # Convert time windows to samples
        self.detection_samples = [
            int(w * self.sampling_rate / 1000) for w in self.detection_window
        ]
        self.baseline_samples = [
            int(w * self.sampling_rate / 1000) for w in self.baseline_window
        ]
        self.epoch_samples = int(self.epoch_length * self.sampling_rate / 1000)
        
        # LSL components
        self.eeg_inlet = None
        self.flash_inlet = None
        self.response_outlet = None
        
        # Data buffers
        self.eeg_buffer = deque(maxlen=self.sampling_rate * 5)  # 5 seconds
        self.flash_events = deque(maxlen=100)  # Recent flash events
        
        # Threading
        self.processing_thread = None
        self.is_running = False
        
        # P300 template (will be computed from config)
        self.p300_template = self._create_p300_template()
        
        # Filtering
        self.bandpass_filter = self._design_bandpass_filter()
        
    def start(self):
        """Start P300 detection."""
        if self.is_running:
            self.logger.warning("P300 detector already running")
            return
        
        try:
            # Connect to LSL streams
            self._connect_to_streams()
            
            # Start processing thread
            self.is_running = True
            self.processing_thread = threading.Thread(
                target=self._processing_loop,
                name="P300Detector",
                daemon=True
            )
            self.processing_thread.start()
            
            self.logger.info("✅ P300 detector started")
            
        except Exception as e:
            self.logger.error(f"Failed to start P300 detector: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop P300 detection."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        # Clean up LSL connections
        if self.eeg_inlet:
            del self.eeg_inlet
        if self.flash_inlet:
            del self.flash_inlet
        if self.response_outlet:
            del self.response_outlet
        
        self.logger.info("✅ P300 detector stopped")
    
    def _connect_to_streams(self):
        """Connect to required LSL streams."""
        # Connect to EEG stream (from signal simulator or real EEG)
        try:
            eeg_streams = lsl.resolve_streams()
            eeg_stream = None
            
            # Look for SimulatedEEG or ProcessedEEG
            for stream in eeg_streams:
                if stream.name() in ['SimulatedEEG', 'ProcessedEEG']:
                    eeg_stream = stream
                    break
            
            if not eeg_stream:
                raise RuntimeError("No EEG stream found (SimulatedEEG or ProcessedEEG)")
            
            self.eeg_inlet = lsl.StreamInlet(eeg_stream)
            self.logger.info(f"✅ Connected to EEG stream: {eeg_stream.name()}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to EEG stream: {e}")
            raise
        
        # Connect to flash events
        try:
            flash_streams = lsl.resolve_streams()
            flash_stream = None
            
            for stream in flash_streams:
                if stream.name() == 'ChessFlash':
                    flash_stream = stream
                    break
            
            if flash_stream:
                self.flash_inlet = lsl.StreamInlet(flash_stream)
                self.logger.info("✅ Connected to ChessFlash stream")
            else:
                self.logger.warning("⚠️ No ChessFlash stream found (GUI not running)")
                
        except Exception as e:
            self.logger.warning(f"Could not connect to ChessFlash: {e}")
        
        # Create P300 response output stream
        response_info = lsl.StreamInfo(
            name="P300Detection",
            type="Markers",
            channel_count=1,
            nominal_srate=lsl.IRREGULAR_RATE,
            channel_format=lsl.cf_string,
            source_id="py300chess_p300_detector"
        )
        self.response_outlet = lsl.StreamOutlet(response_info)
        self.logger.info("✅ Created P300Detection output stream")
    
    def _processing_loop(self):
        """Main P300 detection processing loop."""
        self.logger.info("Starting P300 detection processing")
        
        last_status_time = time.time()
        processed_epochs = 0
        
        try:
            while self.is_running:
                # Pull new EEG data
                self._update_eeg_buffer()
                
                # Check for new flash events
                self._check_flash_events()
                
                # Process pending epochs
                epochs_processed = self._process_pending_epochs()
                processed_epochs += epochs_processed
                
                # Periodic status updates
                if time.time() - last_status_time > 10.0:
                    self.logger.info(f"📊 P300 Detector: {processed_epochs} epochs processed")
                    last_status_time = time.time()
                
                # Small delay to prevent busy waiting
                time.sleep(0.01)
        
        except Exception as e:
            self.logger.error(f"P300 processing error: {e}")
        finally:
            self.logger.info("P300 processing loop ended")
    
    def _update_eeg_buffer(self):
        """Update EEG data buffer with new samples."""
        if not self.eeg_inlet:
            return
        
        # Pull available samples (non-blocking)
        while True:
            try:
                sample, timestamp = self.eeg_inlet.pull_sample(timeout=0.0)
                if sample is None:
                    break
                
                # Add to buffer with timestamp
                self.eeg_buffer.append((sample, timestamp))
                
            except Exception as e:
                self.logger.warning(f"EEG data pull error: {e}")
                break
    
    def _check_flash_events(self):
        """Check for new flash events and queue epochs."""
        if not self.flash_inlet:
            return
        
        while True:
            try:
                marker, timestamp = self.flash_inlet.pull_sample(timeout=0.0)
                if marker is None:
                    break
                
                # Parse flash marker: "square_flash|square=e4"
                flash_info = self._parse_flash_marker(marker[0])
                if flash_info:
                    flash_info['timestamp'] = timestamp
                    self.flash_events.append(flash_info)
                    
                    self.logger.debug(f"Flash event: {flash_info['square']} at {timestamp:.3f}s")
            
            except Exception as e:
                self.logger.warning(f"Flash event error: {e}")
                break
    
    def _process_pending_epochs(self) -> int:
        """Process flash events that have enough data available."""
        processed_count = 0
        current_time = time.time()
        
        # Process events that have enough post-stimulus data
        events_to_remove = []
        
        for i, flash_event in enumerate(self.flash_events):
            stimulus_time = flash_event['timestamp']
            
            # Check if we have enough data after stimulus
            required_duration = self.epoch_length / 1000.0  # Convert to seconds
            if current_time - stimulus_time >= required_duration:
                
                # Extract epoch and detect P300
                epoch_data = self._extract_epoch(stimulus_time)
                if epoch_data is not None:
                    confidence = self._detect_p300(epoch_data)
                    
                    # Send response if above threshold
                    if confidence >= self.min_confidence:
                        self._send_p300_response(flash_event['square'], confidence)
                        self.logger.info(f"🧠 P300 detected: {flash_event['square']} (confidence: {confidence:.2f})")
                    else:
                        self.logger.debug(f"Low confidence: {flash_event['square']} ({confidence:.2f})")
                    
                    processed_count += 1
                
                events_to_remove.append(i)
        
        # Remove processed events
        for i in reversed(events_to_remove):
            del self.flash_events[i]
        
        return processed_count
    
    def _extract_epoch(self, stimulus_time: float) -> Optional[np.ndarray]:
        """Extract EEG epoch around stimulus time."""
        if len(self.eeg_buffer) < self.epoch_samples:
            return None
        
        # Find samples within epoch window
        epoch_start = stimulus_time - (self.epoch_length / 2000.0)  # Half epoch before
        epoch_end = stimulus_time + (self.epoch_length / 2000.0)    # Half epoch after
        
        epoch_samples = []
        for sample, timestamp in self.eeg_buffer:
            if epoch_start <= timestamp <= epoch_end:
                epoch_samples.append(sample)
        
        if len(epoch_samples) < self.epoch_samples * 0.8:  # Need at least 80% of samples
            self.logger.warning(f"Insufficient data for epoch: {len(epoch_samples)}/{self.epoch_samples}")
            return None
        
        # Convert to numpy array
        epoch_data = np.array(epoch_samples)
        
        # Apply bandpass filtering
        if self.bandpass_filter:
            for ch in range(epoch_data.shape[1]):
                epoch_data[:, ch] = signal.sosfiltfilt(self.bandpass_filter, epoch_data[:, ch])
        
        return epoch_data
    
    def _detect_p300(self, epoch_data: np.ndarray) -> float:
        """
        Detect P300 in epoch data and return confidence score.
        
        Args:
            epoch_data: EEG epoch (samples x channels)
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Apply baseline correction
        baseline_end = len(epoch_data) // 2  # Stimulus at middle
        baseline_start = baseline_end + self.baseline_samples[0]
        baseline_end_idx = baseline_end + self.baseline_samples[1]
        
        if baseline_start >= 0 and baseline_end_idx <= len(epoch_data):
            baseline_mean = np.mean(epoch_data[baseline_start:baseline_end_idx, :], axis=0)
            epoch_data = epoch_data - baseline_mean
        
        # Extract P300 detection window
        detection_start = len(epoch_data) // 2 + self.detection_samples[0]
        detection_end = len(epoch_data) // 2 + self.detection_samples[1]
        
        if detection_start < 0 or detection_end > len(epoch_data):
            return 0.0
        
        detection_window = epoch_data[detection_start:detection_end, :]
        
        # Simple amplitude-based detection
        # Look for positive peak in detection window
        max_amplitude = np.max(detection_window, axis=0)
        mean_amplitude = np.mean(max_amplitude)
        
        # Template matching (optional enhancement)
        if self.p300_template is not None:
            template_correlation = self._template_match(detection_window)
            combined_score = 0.7 * (mean_amplitude / self.detection_threshold) + 0.3 * template_correlation
        else:
            combined_score = mean_amplitude / self.detection_threshold
        
        # Convert to confidence (0-1 range)
        confidence = np.clip(combined_score, 0.0, 1.0)
        
        return confidence
    
    def _template_match(self, detection_window: np.ndarray) -> float:
        """Match detection window against P300 template."""
        if self.p300_template is None:
            return 0.0
        
        # Resize template to match detection window
        template_length = len(self.p300_template)
        window_length = len(detection_window)
        
        if template_length != window_length:
            # Simple interpolation
            x_old = np.linspace(0, 1, template_length)
            x_new = np.linspace(0, 1, window_length)
            template_resized = np.interp(x_new, x_old, self.p300_template)
        else:
            template_resized = self.p300_template
        
        # Calculate correlation for each channel
        correlations = []
        for ch in range(detection_window.shape[1]):
            channel_data = detection_window[:, ch]
            correlation = np.corrcoef(channel_data, template_resized)[0, 1]
            if not np.isnan(correlation):
                correlations.append(correlation)
        
        if correlations:
            return np.mean(correlations)
        else:
            return 0.0
    
    def _create_p300_template(self) -> Optional[np.ndarray]:
        """Create P300 template for matching."""
        # Create idealized P300 waveform
        template_duration = 0.4  # 400ms
        template_samples = int(template_duration * self.sampling_rate)
        
        # Time array centered at P300 peak
        t = np.linspace(-0.2, 0.2, template_samples)
        
        # Gaussian-like P300 shape
        p300_latency_sec = self.config.simulation.p300_latency / 1000.0 - 0.2  # Relative to window start
        p300_width_sec = self.config.simulation.p300_width / 1000.0
        
        template = self.config.simulation.p300_amplitude * np.exp(-(t - p300_latency_sec)**2 / (2 * (p300_width_sec/3)**2))
        
        return template
    
    def _design_bandpass_filter(self):
        """Design bandpass filter for EEG preprocessing."""
        if not hasattr(self.config.p300, 'bandpass_filter'):
            return None
        
        low_freq, high_freq = self.config.p300.bandpass_filter
        nyquist = self.sampling_rate / 2
        
        if low_freq >= nyquist or high_freq >= nyquist:
            self.logger.warning("Filter frequencies exceed Nyquist frequency")
            return None
        
        # Design Butterworth bandpass filter
        sos = signal.butter(4, [low_freq, high_freq], btype='band', fs=self.sampling_rate, output='sos')
        return sos
    
    def _parse_flash_marker(self, marker: str) -> Optional[Dict]:
        """Parse flash marker string."""
        try:
            # Expected format: "square_flash|square=e4"
            if marker.startswith("square_flash|"):
                parts = marker.split('|')
                if len(parts) >= 2 and parts[1].startswith('square='):
                    square = parts[1].split('=')[1]
                    return {'square': square, 'type': 'flash'}
        except Exception as e:
            self.logger.warning(f"Failed to parse flash marker: {marker} - {e}")
        
        return None
    
    def _send_p300_response(self, square: str, confidence: float):
        """Send P300 detection response via LSL."""
        if self.response_outlet:
            response = f"p300_detected|square={square}|confidence={confidence:.3f}"
            self.response_outlet.push_sample([response])
    
    def get_status(self) -> Dict:
        """Get detector status."""
        return {
            'is_running': self.is_running,
            'eeg_connected': self.eeg_inlet is not None,
            'flash_connected': self.flash_inlet is not None,
            'buffer_size': len(self.eeg_buffer),
            'pending_events': len(self.flash_events),
            'detection_threshold': self.detection_threshold,
            'min_confidence': self.min_confidence
        }


# Standalone execution for testing
if __name__ == "__main__":
    import sys
    import os
    
    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    sys.path.insert(0, project_root)
    
    from config.config_loader import get_config
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🧠 P300 Detector - Real-time EEG Processing")
    print("=" * 50)
    
    # Load configuration
    config = get_config()
    
    # Enable debug mode for testing
    config.feedback.debug_mode = True
    
    # Create and start detector
    detector = P300Detector(config)
    
    try:
        detector.start()
        
        print("\n✅ P300 detector running!")
        print("This component:")
        print("  🔌 Connects to EEG streams (SimulatedEEG or ProcessedEEG)")
        print("  ⚡ Listens for ChessFlash events")
        print("  🧠 Detects P300 responses in real-time")
        print("  📊 Outputs confidence scores via P300Detection stream")
        
        print("\nTo test:")
        print("  1. Start signal simulator: python signal_simulator.py")
        print("  2. Send test commands from another terminal")
        print("  3. Watch for P300 detections here")
        
        print(f"\nAvailable LSL streams: {[s.name() for s in lsl.resolve_streams()]}")
        print("\nPress Ctrl+C to stop...")
        
        # Show status updates
        while True:
            time.sleep(5.0)
            status = detector.get_status()
            print(f"📊 Buffer: {status['buffer_size']} samples | "
                  f"Events: {status['pending_events']} | "
                  f"EEG: {'✅' if status['eeg_connected'] else '❌'} | "
                  f"Flash: {'✅' if status['flash_connected'] else '❌'}")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping P300 detector...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        detector.stop()
        print("✅ P300 detector stopped")