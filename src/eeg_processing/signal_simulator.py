"""
Standalone EEG Signal Simulator with LSL Streaming.

This module provides a complete simulated EEG system that:
- Generates realistic EEG signals with P300 responses
- Streams continuously via Lab Streaming Layer (LSL)
- Listens for chess game commands (target setting, square flashes)
- Generates perfect P300 responses when target squares flash
- Runs as an independent component for testing and development
"""

import numpy as np
import time
import threading
from typing import Optional, List, Tuple, Dict
import logging
import pylsl as lsl


class EEGSignalSimulator:
    """
    Simulates realistic EEG signals with P300 responses.
    
    This class generates continuous EEG-like signals with:
    - Realistic background noise (alpha, beta, gamma frequencies)
    - Simulated artifacts (eye blinks, muscle activity)
    - P300 event-related potentials triggered by markers
    """
    
    def __init__(self, config):
        """
        Initialize the EEG signal simulator.
        
        Args:
            config: Configuration object with simulation parameters
        """
        self.config = config
        self.sampling_rate = config.eeg.sampling_rate
        self.n_channels = config.eeg.n_channels
        
        # Simulation parameters
        self.noise_amplitude = config.simulation.noise_amplitude
        self.p300_amplitude = config.simulation.p300_amplitude
        self.p300_latency = config.simulation.p300_latency / 1000.0  # Convert to seconds
        self.p300_width = config.simulation.p300_width / 1000.0     # Convert to seconds
        self.p300_probability = config.simulation.p300_probability
        self.add_artifacts = config.simulation.add_artifacts
        self.artifact_rate = config.simulation.artifact_rate
        
        # Internal state
        self._time_offset = 0.0
        self._sample_count = 0
        self._lock = threading.Lock()
        
        # P300 event queue: list of (trigger_time, is_target)
        self._p300_events = []
        
        # Background noise generators
        self._noise_generators = self._initialize_noise_generators()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def _initialize_noise_generators(self) -> dict:
        """Initialize frequency-specific noise generators."""
        generators = {}
        
        # Alpha waves (8-12 Hz) - most prominent in resting EEG
        generators['alpha'] = {
            'frequency': 10.0,
            'amplitude': self.noise_amplitude * 0.6,
            'phase': np.random.uniform(0, 2*np.pi, self.n_channels)
        }
        
        # Beta waves (13-30 Hz) - mental activity
        generators['beta'] = {
            'frequency': 20.0,
            'amplitude': self.noise_amplitude * 0.3,
            'phase': np.random.uniform(0, 2*np.pi, self.n_channels)
        }
        
        # Theta waves (4-8 Hz) - drowsiness/meditation
        generators['theta'] = {
            'frequency': 6.0,
            'amplitude': self.noise_amplitude * 0.2,
            'phase': np.random.uniform(0, 2*np.pi, self.n_channels)
        }
        
        # High-frequency noise
        generators['gamma'] = {
            'frequency': 40.0,
            'amplitude': self.noise_amplitude * 0.1,
            'phase': np.random.uniform(0, 2*np.pi, self.n_channels)
        }
        
        return generators
    
    def add_stimulus_marker(self, is_target: bool = False):
        """
        Add a stimulus marker for P300 generation.
        
        Args:
            is_target: Whether this stimulus is the target the user is focusing on
        """
        with self._lock:
            current_time = self._sample_count / self.sampling_rate
            self._p300_events.append((current_time, is_target))
            
            if self.config.feedback.debug_mode:
                self.logger.debug(f"Added stimulus marker at {current_time:.3f}s, target={is_target}")
    
    def generate_samples(self, n_samples: int) -> Tuple[np.ndarray, List[float]]:
        """
        Generate n_samples of EEG data.
        
        Args:
            n_samples: Number of samples to generate
            
        Returns:
            Tuple of (eeg_data, timestamps)
            - eeg_data: Shape (n_samples, n_channels) in microvolts
            - timestamps: List of timestamps for each sample
        """
        with self._lock:
            # Generate time array for these samples
            start_time = self._sample_count / self.sampling_rate
            end_time = (self._sample_count + n_samples) / self.sampling_rate
            time_array = np.linspace(start_time, end_time, n_samples, endpoint=False)
            
            # Initialize output array
            eeg_data = np.zeros((n_samples, self.n_channels))
            
            # Generate background EEG activity
            eeg_data += self._generate_background_noise(time_array)
            
            # Add P300 responses for triggered events
            eeg_data += self._generate_p300_responses(time_array)
            
            # Add artifacts if enabled
            if self.add_artifacts:
                eeg_data += self._generate_artifacts(time_array)
            
            # Add white noise
            white_noise = np.random.normal(0, self.noise_amplitude * 0.1, 
                                         (n_samples, self.n_channels))
            eeg_data += white_noise
            
            # Update sample count
            self._sample_count += n_samples
            
            # Clean up old P300 events (older than 2 seconds)
            cutoff_time = start_time - 2.0
            self._p300_events = [(t, target) for t, target in self._p300_events if t > cutoff_time]
            
            return eeg_data, time_array.tolist()
    
    def _generate_background_noise(self, time_array: np.ndarray) -> np.ndarray:
        """Generate realistic background EEG rhythms."""
        n_samples = len(time_array)
        background = np.zeros((n_samples, self.n_channels))
        
        for wave_type, params in self._noise_generators.items():
            freq = params['frequency']
            amp = params['amplitude']
            phases = params['phase']
            
            # Generate sinusoidal components with slight frequency drift
            freq_drift = 1 + 0.1 * np.sin(2 * np.pi * time_array * 0.1)
            
            for ch in range(self.n_channels):
                wave = amp * np.sin(2 * np.pi * freq * freq_drift * time_array + phases[ch])
                
                # Add slight amplitude modulation
                amp_mod = 1 + 0.2 * np.sin(2 * np.pi * time_array * 0.05)
                wave *= amp_mod
                
                background[:, ch] += wave
        
        return background
    
    def _generate_p300_responses(self, time_array: np.ndarray) -> np.ndarray:
        """Generate P300 responses for triggered events."""
        n_samples = len(time_array)
        p300_signal = np.zeros((n_samples, self.n_channels))
        
        for trigger_time, is_target in self._p300_events:
            # Only generate P300 for target stimuli (with perfect probability in this module)
            if not is_target:
                continue
            
            # Calculate P300 timing
            p300_peak_time = trigger_time + self.p300_latency
            
            # Check if P300 overlaps with current time window
            if (p300_peak_time - self.p300_width < time_array[-1] and 
                p300_peak_time + self.p300_width > time_array[0]):
                
                # Generate P300 waveform (positive peak around 300ms)
                p300_component = self._create_p300_waveform(time_array, p300_peak_time)
                
                # Distribute across channels (strongest at central electrodes)
                for ch in range(self.n_channels):
                    # Simulate electrode distance from central sites
                    if self.config.eeg.channel_names[ch] in ['Cz', 'C3', 'C4', 'Pz']:
                        channel_weight = 1.0
                    else:
                        channel_weight = 0.7
                    
                    p300_signal[:, ch] += p300_component * channel_weight
        
        return p300_signal
    
    def _create_p300_waveform(self, time_array: np.ndarray, peak_time: float) -> np.ndarray:
        """Create a realistic P300 waveform."""
        # P300 is typically a positive deflection with specific time course
        time_relative = time_array - peak_time
        
        # Use a gamma function-like shape for realistic P300
        waveform = np.zeros_like(time_relative)
        
        # Only generate where we're close to the peak time
        mask = np.abs(time_relative) < (self.p300_width * 2)
        t_masked = time_relative[mask]
        
        if len(t_masked) > 0:
            # Gamma-like function: rapid rise, exponential decay
            alpha = 2.0  # Shape parameter
            beta = self.p300_width / 3  # Scale parameter
            
            # Shift time to make peak at t=0
            t_shifted = t_masked + self.p300_width/2
            
            # Only positive times for gamma function
            pos_mask = t_shifted > 0
            if np.any(pos_mask):
                gamma_vals = np.zeros_like(t_shifted)
                gamma_vals[pos_mask] = (
                    (t_shifted[pos_mask]/beta)**alpha * 
                    np.exp(-t_shifted[pos_mask]/beta)
                )
                
                # Normalize to desired amplitude
                if np.max(gamma_vals) > 0:
                    gamma_vals = gamma_vals / np.max(gamma_vals) * self.p300_amplitude
                
                waveform[mask] = gamma_vals
        
        return waveform
    
    def _generate_artifacts(self, time_array: np.ndarray) -> np.ndarray:
        """Generate realistic EEG artifacts (eye blinks, muscle activity)."""
        n_samples = len(time_array)
        artifacts = np.zeros((n_samples, self.n_channels))
        
        # Eye blinks (large, slow deflections)
        blink_probability = self.artifact_rate / self.sampling_rate
        for i, t in enumerate(time_array):
            if np.random.random() < blink_probability:
                # Generate eye blink (duration ~200ms)
                blink_duration = 0.2
                blink_start = max(0, i - int(blink_duration * self.sampling_rate // 2))
                blink_end = min(n_samples, i + int(blink_duration * self.sampling_rate // 2))
                
                # Blink amplitude (much larger than EEG)
                blink_amplitude = self.noise_amplitude * 5
                
                # Exponential decay shape
                blink_samples = blink_end - blink_start
                if blink_samples > 0:
                    blink_shape = np.exp(-np.linspace(0, 3, blink_samples))
                    
                    # Stronger in frontal channels
                    for ch in range(self.n_channels):
                        if self.config.eeg.channel_names[ch] in ['Fp1', 'Fp2', 'F3', 'F4']:
                            weight = 1.0
                        else:
                            weight = 0.3
                        
                        artifacts[blink_start:blink_end, ch] += (
                            blink_amplitude * blink_shape * weight
                        )
        
        # Muscle artifacts (high-frequency bursts)
        muscle_probability = self.artifact_rate * 0.5 / self.sampling_rate
        for i, t in enumerate(time_array):
            if np.random.random() < muscle_probability:
                # Short burst of high-frequency activity
                burst_duration = 0.05  # 50ms
                burst_start = i
                burst_end = min(n_samples, i + int(burst_duration * self.sampling_rate))
                
                burst_samples = burst_end - burst_start
                if burst_samples > 0:
                    # High-frequency noise
                    muscle_noise = np.random.normal(
                        0, self.noise_amplitude * 2, 
                        (burst_samples, self.n_channels)
                    )
                    artifacts[burst_start:burst_end, :] += muscle_noise
        
        return artifacts
    
    def reset(self):
        """Reset the simulator state."""
        with self._lock:
            self._time_offset = 0.0
            self._sample_count = 0
            self._p300_events.clear()
            
            # Reinitialize noise generators with new random phases
            self._noise_generators = self._initialize_noise_generators()
    
    def get_current_time(self) -> float:
        """Get the current simulation time in seconds."""
        with self._lock:
            return self._sample_count / self.sampling_rate


class SimulatedEEGStreamer:
    """
    Standalone simulated EEG streamer with chess game integration.
    
    This component:
    - Runs continuously streaming simulated EEG via LSL
    - Creates ChessTarget and ChessFlash streams for chess engine to use
    - Generates P300 responses when target squares flash
    - Starts immediately with clean EEG until chess engine connects
    """
    
    def __init__(self, config):
        """Initialize the simulated EEG streamer."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # EEG simulation
        self.simulator = EEGSignalSimulator(config)
        
        # LSL outlets (we create these)
        self.eeg_outlet = None
        self.response_outlet = None
        
        # LSL inlets (we create the streams, chess engine sends to them)
        self.target_inlet = None
        self.flash_inlet = None
        
        # We also create the target and flash outlets for chess engine to use
        self.target_outlet = None
        self.flash_outlet = None
        
        # Threading
        self.streaming_thread = None
        self.listener_thread = None
        self.is_running = False
        
        # Chess state
        self.current_target = None
        self.chess_engine_connected = False
        
    def start(self):
        """Start the simulated EEG streaming system."""
        if self.is_running:
            self.logger.warning("System already running")
            return
        
        try:
            # Create all LSL streams
            self._create_eeg_outlet()
            self._create_response_outlet()
            self._create_chess_streams()
            
            # Start threads
            self.is_running = True
            self._start_threads()
            
            self.logger.info("✅ Simulated EEG streaming started")
            self.logger.info("📡 Streaming clean EEG until chess engine connects...")
            
        except Exception as e:
            self.logger.error(f"Failed to start simulated EEG streaming: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the simulated EEG streaming system."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Wait for threads
        if self.streaming_thread:
            self.streaming_thread.join(timeout=2.0)
        if self.listener_thread:
            self.listener_thread.join(timeout=2.0)
        
        # Clean up all LSL streams
        for outlet in [self.eeg_outlet, self.response_outlet, self.target_outlet, self.flash_outlet]:
            if outlet:
                del outlet
        
        for inlet in [self.target_inlet, self.flash_inlet]:
            if inlet:
                del inlet
        
        # Reset outlets/inlets
        self.eeg_outlet = None
        self.response_outlet = None
        self.target_outlet = None
        self.flash_outlet = None
        self.target_inlet = None
        self.flash_inlet = None
        
        self.logger.info("✅ Simulated EEG streaming stopped")
    
    def _create_eeg_outlet(self):
        """Create LSL outlet for EEG data."""
        eeg_info = lsl.StreamInfo(
            name="SimulatedEEG",
            type="EEG",
            channel_count=self.config.eeg.n_channels,
            nominal_srate=self.config.eeg.sampling_rate,
            channel_format=lsl.cf_float32,
            source_id="py300chess_simulator"
        )
        
        # Add channel metadata
        channels = eeg_info.desc().append_child("channels")
        for name in self.config.eeg.channel_names:
            ch = channels.append_child("channel")
            ch.append_child_value("label", name)
            ch.append_child_value("unit", "microvolts")
            ch.append_child_value("type", "EEG")
        
        self.eeg_outlet = lsl.StreamOutlet(eeg_info)
        self.logger.info("✅ Created SimulatedEEG LSL outlet")
    
    def _create_response_outlet(self):
        """Create LSL outlet for P300 responses."""
        response_info = lsl.StreamInfo(
            name="P300Response",
            type="Markers", 
            channel_count=1,
            nominal_srate=lsl.IRREGULAR_RATE,
            channel_format=lsl.cf_string,
            source_id="py300chess_response"
        )
        
        self.response_outlet = lsl.StreamOutlet(response_info)
        self.logger.info("✅ Created P300Response LSL outlet")
    
    def _create_chess_streams(self):
        """Create chess command streams for engine to use."""
        # Create ChessTarget stream that chess engine will send to
        target_info = lsl.StreamInfo(
            name="ChessTarget",
            type="Markers",
            channel_count=1,
            nominal_srate=lsl.IRREGULAR_RATE,
            channel_format=lsl.cf_string,
            source_id="py300chess_target_input"
        )
        self.target_outlet = lsl.StreamOutlet(target_info)
        
        # Create ChessFlash stream that chess GUI will send to  
        flash_info = lsl.StreamInfo(
            name="ChessFlash",
            type="Markers",
            channel_count=1,
            nominal_srate=lsl.IRREGULAR_RATE,
            channel_format=lsl.cf_string,
            source_id="py300chess_flash_input"
        )
        self.flash_outlet = lsl.StreamOutlet(flash_info)
        
        # Now connect to these streams as inlets
        time.sleep(0.1)  # Give LSL a moment to register the streams
        
        try:
            target_streams = lsl.resolve_stream('name', 'ChessTarget')
            if target_streams:
                self.target_inlet = lsl.StreamInlet(target_streams[0])
                self.logger.info("✅ Created ChessTarget stream (ready for chess engine)")
        except Exception as e:
            self.logger.warning(f"Could not connect to ChessTarget inlet: {e}")
        
        try:
            flash_streams = lsl.resolve_stream('name', 'ChessFlash')
            if flash_streams:
                self.flash_inlet = lsl.StreamInlet(flash_streams[0])
                self.logger.info("✅ Created ChessFlash stream (ready for chess GUI)")
        except Exception as e:
            self.logger.warning(f"Could not connect to ChessFlash inlet: {e}")
    
    def _start_threads(self):
        """Start streaming and listening threads."""
        # EEG streaming thread
        self.streaming_thread = threading.Thread(
            target=self._streaming_loop,
            name="SimulatedEEGStream",
            daemon=True
        )
        self.streaming_thread.start()
        
        # Chess command listener thread
        self.listener_thread = threading.Thread(
            target=self._chess_listener_loop,
            name="ChessListener",
            daemon=True
        )
        self.listener_thread.start()
    
    def _streaming_loop(self):
        """Main EEG streaming loop."""
        chunk_size = max(1, int(self.config.eeg.sampling_rate * 0.04))  # 40ms chunks
        sample_count = 0
        
        self.logger.info(f"Starting EEG streaming loop ({chunk_size} samples/chunk)")
        
        try:
            while self.is_running:
                start_time = time.time()
                
                # Generate EEG chunk
                eeg_data, timestamps = self.simulator.generate_samples(chunk_size)
                sample_count += chunk_size
                
                # Stream via LSL
                if self.eeg_outlet:
                    for i in range(len(eeg_data)):
                        sample = eeg_data[i, :].tolist()
                        self.eeg_outlet.push_sample(sample)
                
                # Periodic verbose output
                if (self.config.feedback.debug_mode and 
                    sample_count % (chunk_size * 250) == 0):  # Every ~10 seconds
                    sim_time = self.simulator.get_current_time()
                    status = "🎯 Chess connected" if self.chess_engine_connected else "⏳ Waiting for chess engine"
                    self.logger.info(f"📊 Streaming: {sim_time:.1f}s | Target: {self.current_target} | {status}")
                
                # Maintain real-time rate
                elapsed = time.time() - start_time
                target_duration = chunk_size / self.config.eeg.sampling_rate
                sleep_time = target_duration - elapsed
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                elif sleep_time < -0.01:
                    self.logger.warning(f"Streaming {-sleep_time*1000:.1f}ms behind")
        
        except Exception as e:
            self.logger.error(f"Streaming loop error: {e}")
        finally:
            self.logger.info("EEG streaming loop ended")
    
    def _chess_listener_loop(self):
        """Listen for chess commands and generate responses."""
        self.logger.info("Starting chess command listener")
        
        try:
            while self.is_running:
                # Check for target commands
                if self.target_inlet:
                    try:
                        marker, timestamp = self.target_inlet.pull_sample(timeout=0.1)
                        if marker:
                            self._handle_target_command(marker[0])
                            if not self.chess_engine_connected:
                                self.chess_engine_connected = True
                                self.logger.info("🎮 Chess engine connected!")
                    except:
                        pass
                
                # Check for flash commands
                if self.flash_inlet:
                    try:
                        marker, timestamp = self.flash_inlet.pull_sample(timeout=0.1)
                        if marker:
                            self._handle_flash_command(marker[0])
                    except:
                        pass
                
                time.sleep(0.01)  # Small delay
        
        except Exception as e:
            self.logger.error(f"Chess listener error: {e}")
        finally:
            self.logger.info("Chess listener ended")
    
    def _handle_target_command(self, marker: str):
        """Handle target setting command."""
        try:
            # Parse: "set_target|square=e4"
            if marker.startswith("set_target|"):
                parts = marker.split('|')
                if len(parts) >= 2:
                    square_part = parts[1]
                    if square_part.startswith('square='):
                        self.current_target = square_part.split('=')[1]
                        self.logger.info(f"🎯 Target set to: {self.current_target}")
        except Exception as e:
            self.logger.error(f"Error handling target command: {e}")
    
    def _handle_flash_command(self, marker: str):
        """Handle square flash command."""
        try:
            # Parse: "square_flash|square=e4"
            if marker.startswith("square_flash|"):
                parts = marker.split('|')
                if len(parts) >= 2:
                    square_part = parts[1]
                    if square_part.startswith('square='):
                        flashed_square = square_part.split('=')[1]
                        
                        # Check if target match
                        is_target = (flashed_square == self.current_target)
                        
                        if is_target:
                            self.logger.info(f"⚡ TARGET FLASH: {flashed_square} - generating P300!")
                            
                            # Send P300 response
                            if self.response_outlet:
                                response = f"p300_detected|square={flashed_square}|confidence=1.0"
                                self.response_outlet.push_sample([response])
                        else:
                            self.logger.debug(f"Non-target flash: {flashed_square}")
                        
                        # Tell simulator to generate P300 if target
                        self.simulator.add_stimulus_marker(is_target=is_target)
        
        except Exception as e:
            self.logger.error(f"Error handling flash command: {e}")
    
    def get_status(self) -> Dict:
        """Get current system status."""
        return {
            'is_running': self.is_running,
            'current_target': self.current_target,
            'simulation_time': self.simulator.get_current_time(),
            'chess_engine_connected': self.chess_engine_connected,
            'streams_created': {
                'eeg_outlet': self.eeg_outlet is not None,
                'response_outlet': self.response_outlet is not None,
                'target_stream': self.target_outlet is not None,
                'flash_stream': self.flash_outlet is not None
            }
        }


# Standalone execution
if __name__ == "__main__":
    import sys
    import os
    import argparse
    
    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    sys.path.insert(0, project_root)
    
    from config.config_loader import get_config
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='EEG Signal Simulator')
    parser.add_argument('--standalone', action='store_true', 
                       help='Run in standalone mode (no chess integration, just EEG)')
    parser.add_argument('--no-p300', action='store_true',
                       help='Disable P300 responses (clean EEG only)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load config
    config = get_config()
    if args.verbose:
        config.feedback.debug_mode = True
    
    # Disable P300 if requested
    if args.no_p300:
        config.simulation.p300_amplitude = 0.0
        config.simulation.p300_probability = 0.0
    
    if args.standalone:
        # Standalone mode - just stream EEG without chess integration
        print("🧠 Starting Standalone EEG Signal Generator")
        print("=" * 60)
        print("Mode: Pure EEG streaming (no chess integration)")
        print(f"P300 responses: {'Disabled' if args.no_p300 else 'Enabled'}")
        print("=" * 60)
        
        # Create just the simulator and LSL outlet
        simulator = EEGSignalSimulator(config)
        
        # Create simple LSL outlet
        eeg_info = lsl.StreamInfo(
            name="StandaloneEEG",
            type="EEG",
            channel_count=config.eeg.n_channels,
            nominal_srate=config.eeg.sampling_rate,
            channel_format=lsl.cf_float32,
            source_id="py300chess_standalone"
        )
        
        # Add channel metadata
        channels = eeg_info.desc().append_child("channels")
        for name in config.eeg.channel_names:
            ch = channels.append_child("channel")
            ch.append_child_value("label", name)
            ch.append_child_value("unit", "microvolts")
            ch.append_child_value("type", "EEG")
        
        eeg_outlet = lsl.StreamOutlet(eeg_info)
        print("✅ Created StandaloneEEG LSL outlet")
        
        # Simple streaming loop
        chunk_size = max(1, int(config.eeg.sampling_rate * 0.04))  # 40ms chunks
        sample_count = 0
        
        print(f"📡 Streaming {config.eeg.sampling_rate}Hz EEG data...")
        print("   To view data, use any LSL viewer or:")
        print("   python -c \"import pylsl; inlet=pylsl.StreamInlet(pylsl.resolve_stream('name','StandaloneEEG')[0]); [print(inlet.pull_sample()) for _ in range(10)]\"")
        print("\nPress Ctrl+C to stop...")
        
        try:
            start_time = time.time()
            
            while True:
                loop_start = time.time()
                
                # Generate EEG chunk
                eeg_data, timestamps = simulator.generate_samples(chunk_size)
                sample_count += chunk_size
                
                # Stream via LSL
                for i in range(len(eeg_data)):
                    sample = eeg_data[i, :].tolist()
                    eeg_outlet.push_sample(sample)
                
                # Show status every 5 seconds
                if sample_count % (chunk_size * 125) == 0:  # ~5 seconds
                    elapsed = time.time() - start_time
                    sim_time = simulator.get_current_time()
                    print(f"📊 Streaming: {sim_time:.1f}s | Samples: {sample_count} | Real time: {elapsed:.1f}s")
                
                # Maintain real-time rate
                elapsed = time.time() - loop_start
                target_duration = chunk_size / config.eeg.sampling_rate
                sleep_time = target_duration - elapsed
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            print("\n🛑 Stopping standalone EEG generator...")
        finally:
            del eeg_outlet
            print("✅ Standalone EEG generator stopped")
    
    else:
        # Full chess-integrated mode (default)
        print("🧠 Starting Chess-Integrated Simulated EEG Streamer")
        print("=" * 60)
        
        # Enable verbose if requested
        if args.verbose:
            config.feedback.debug_mode = True
        
        # Create and start system
        streamer = SimulatedEEGStreamer(config)
        
        try:
            streamer.start()
            
            print("\n🎮 Simulated EEG System Ready!")
            print("This component:")
            print("  📡 Streams continuous simulated EEG via LSL")
            print("  🎯 Creates ChessTarget stream for chess engine")
            print("  ⚡ Creates ChessFlash stream for chess GUI")
            print("  🧠 Generates P300 when target squares flash")
            print("  🔧 Starts immediately with clean EEG")
            
            print("\nAvailable LSL streams:")
            print("  📊 SimulatedEEG    - Continuous EEG data")
            print("  🎯 ChessTarget     - For chess engine to send moves")
            print("  ⚡ ChessFlash      - For chess GUI to send flashes")
            print("  📈 P300Response    - P300 detection results")
            
            print("\nTo test manually:")
            print("  # Chess engine sets target:")
            print("  python -c \"import pylsl; inlet=pylsl.StreamInlet(pylsl.resolve_stream('name','ChessTarget')[0]); inlet.push_sample(['set_target|square=e4'])\"")
            print("  # Chess GUI flashes square:")  
            print("  python -c \"import pylsl; inlet=pylsl.StreamInlet(pylsl.resolve_stream('name','ChessFlash')[0]); inlet.push_sample(['square_flash|square=e4'])\"")
            
            print("\nPress Ctrl+C to stop...")
            
            # Show status updates
            while True:
                time.sleep(5.0)
                status = streamer.get_status()
                engine_status = "🎮 Connected" if status['chess_engine_connected'] else "⏳ Waiting for engine"
                print(f"📊 Time: {status['simulation_time']:.1f}s | Target: {status['current_target']} | {engine_status}")
        
        except KeyboardInterrupt:
            print("\n🛑 Stopping simulated EEG streamer...")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            streamer.stop()
            print("✅ Simulated EEG streamer stopped")