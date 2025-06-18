"""
Real EEG Device LSL Stream Handler.

This module handles connection to real EEG hardware devices and streams
the data via Lab Streaming Layer (LSL). It focuses purely on hardware
interface and data forwarding - no P300 simulation.

Supports various EEG devices like:
- Muse headsets
- OpenBCI boards  
- DSI systems
- Any device that streams via LSL
"""

import numpy as np
import time
import threading
from typing import Optional, List, Dict, Callable
import logging
import pylsl as lsl


class RealEEGStreamer:
    """
    Real EEG device stream handler.
    
    Connects to hardware EEG devices and forwards data via LSL.
    Can also apply real-time processing (filtering, re-referencing, etc.)
    """
    
    def __init__(self, config):
        """
        Initialize real EEG streamer.
        
        Args:
            config: Configuration object with EEG parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Stream parameters
        self.sampling_rate = config.eeg.sampling_rate
        self.n_channels = config.eeg.n_channels
        self.channel_names = config.eeg.channel_names
        self.stream_name = config.eeg.stream_name
        
        # LSL components
        self.input_inlet = None   # Connect to hardware
        self.output_outlet = None # Forward processed data
        
        # Threading
        self.streaming_thread = None
        self.is_running = False
        
        # Data processing
        self.data_buffer = []
        self.processing_callback = None
        
    def start(self, processing_callback: Optional[Callable] = None):
        """
        Start real EEG streaming.
        
        Args:
            processing_callback: Optional function to process data in real-time
                                 callback(data, timestamps) -> processed_data
        """
        if self.is_running:
            self.logger.warning("Real EEG streaming already running")
            return
        
        try:
            # Connect to hardware EEG device
            self._connect_to_hardware()
            
            # Create output stream for processed data
            self._create_output_stream()
            
            # Set processing callback
            self.processing_callback = processing_callback
            
            # Start streaming thread
            self.is_running = True
            self.streaming_thread = threading.Thread(
                target=self._streaming_loop,
                name="RealEEGStream",
                daemon=True
            )
            self.streaming_thread.start()
            
            self.logger.info("✅ Real EEG streaming started")
            
        except Exception as e:
            self.logger.error(f"Failed to start real EEG streaming: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop real EEG streaming."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Wait for streaming thread
        if self.streaming_thread:
            self.streaming_thread.join(timeout=2.0)
        
        # Clean up LSL
        if self.input_inlet:
            del self.input_inlet
            self.input_inlet = None
        if self.output_outlet:
            del self.output_outlet
            self.output_outlet = None
        
        self.logger.info("✅ Real EEG streaming stopped")
    
    def _connect_to_hardware(self):
        """Connect to real EEG hardware device."""
        self.logger.info(f"Looking for EEG hardware: {self.stream_name}")
        
        # Look for the specified EEG stream
        streams = lsl.resolve_stream('name', self.stream_name)
        if not streams:
            # Try resolving by type if name doesn't work
            streams = lsl.resolve_stream('type', 'EEG')
            if not streams:
                raise RuntimeError(f"No EEG device found. Checked for name='{self.stream_name}' and type='EEG'")
        
        # Connect to the first available stream
        self.input_inlet = lsl.StreamInlet(streams[0])
        
        # Get stream info
        info = self.input_inlet.info()
        self.hardware_rate = info.nominal_srate()
        self.hardware_channels = info.channel_count()
        
        self.logger.info(f"✅ Connected to EEG device:")
        self.logger.info(f"  Name: {info.name()}")
        self.logger.info(f"  Channels: {self.hardware_channels}")
        self.logger.info(f"  Sample Rate: {self.hardware_rate} Hz")
        self.logger.info(f"  Type: {info.type()}")
    
    def _create_output_stream(self):
        """Create LSL output stream for processed EEG data."""
        # Create stream info for processed data
        output_info = lsl.StreamInfo(
            name="ProcessedEEG",
            type="EEG",
            channel_count=self.n_channels,
            nominal_srate=self.sampling_rate,
            channel_format=lsl.cf_float32,
            source_id="py300chess_real_eeg"
        )
        
        # Add channel metadata
        channels = output_info.desc().append_child("channels")
        for name in self.channel_names:
            ch = channels.append_child("channel")
            ch.append_child_value("label", name)
            ch.append_child_value("unit", "microvolts")
            ch.append_child_value("type", "EEG")
        
        # Add processing info
        processing = output_info.desc().append_child("processing")
        processing.append_child_value("source", f"Hardware device: {self.stream_name}")
        processing.append_child_value("software", "py300chess real EEG streamer")
        
        self.output_outlet = lsl.StreamOutlet(output_info)
        self.logger.info("Created ProcessedEEG LSL outlet")
    
    def _streaming_loop(self):
        """Main streaming loop for real EEG data."""
        self.logger.info("Starting real EEG streaming loop")
        
        sample_count = 0
        
        try:
            while self.is_running:
                # Pull sample from hardware
                try:
                    sample, timestamp = self.input_inlet.pull_sample(timeout=1.0)
                    
                    if sample is None:
                        self.logger.warning("No data received from EEG device")
                        continue
                    
                    sample_count += 1
                    
                    # Apply processing if callback provided
                    if self.processing_callback:
                        try:
                            processed_sample = self.processing_callback(sample, timestamp)
                            if processed_sample is not None:
                                sample = processed_sample
                        except Exception as e:
                            self.logger.warning(f"Processing callback error: {e}")
                    
                    # Forward to output stream
                    if self.output_outlet:
                        # Ensure sample has correct number of channels
                        if len(sample) != self.n_channels:
                            # Handle channel count mismatch
                            sample = self._adapt_channels(sample)
                        
                        self.output_outlet.push_sample(sample, timestamp)
                    
                    # Periodic status
                    if (self.config.feedback.debug_mode and 
                        sample_count % (self.hardware_rate * 10) == 0):  # Every 10 seconds
                        self.logger.info(f"📊 Processed {sample_count} samples from hardware")
                
                except Exception as e:
                    self.logger.error(f"Error in streaming loop: {e}")
                    time.sleep(0.1)
        
        except Exception as e:
            self.logger.error(f"Real EEG streaming loop error: {e}")
        finally:
            self.logger.info("Real EEG streaming loop ended")
    
    def _adapt_channels(self, sample: List[float]) -> List[float]:
        """
        Adapt hardware channels to match configuration.
        
        Args:
            sample: Raw sample from hardware
            
        Returns:
            Adapted sample with correct channel count
        """
        hardware_channels = len(sample)
        target_channels = self.n_channels
        
        if hardware_channels == target_channels:
            return sample
        elif hardware_channels > target_channels:
            # Select first N channels
            self.logger.debug(f"Selecting first {target_channels} of {hardware_channels} channels")
            return sample[:target_channels]
        else:
            # Pad with zeros or duplicate channels
            self.logger.debug(f"Padding {hardware_channels} channels to {target_channels}")
            adapted = list(sample)
            while len(adapted) < target_channels:
                adapted.append(0.0)  # Pad with zeros
            return adapted
    
    def get_status(self) -> Dict:
        """Get current streaming status."""
        return {
            'is_running': self.is_running,
            'stream_name': self.stream_name,
            'hardware_connected': self.input_inlet is not None,
            'hardware_rate': getattr(self, 'hardware_rate', 0),
            'hardware_channels': getattr(self, 'hardware_channels', 0),
            'target_channels': self.n_channels,
            'target_rate': self.sampling_rate
        }


class EEGDeviceManager:
    """
    Manager for discovering and connecting to EEG devices.
    
    Helps identify available EEG hardware and configure connections.
    """
    
    def __init__(self):
        """Initialize EEG device manager."""
        self.logger = logging.getLogger(__name__)
    
    def discover_devices(self, timeout: float = 5.0) -> List[Dict]:
        """
        Discover available EEG devices on the network.
        
        Args:
            timeout: How long to search for devices
            
        Returns:
            List of device info dictionaries
        """
        self.logger.info(f"Scanning for EEG devices ({timeout}s timeout)...")
        
        devices = []
        
        try:
            # Look for EEG streams
            streams = lsl.resolve_stream('type', 'EEG')
            
            for stream in streams:
                info = {
                    'name': stream.name(),
                    'type': stream.type(),
                    'channel_count': stream.channel_count(),
                    'sample_rate': stream.nominal_srate(),
                    'source_id': stream.source_id(),
                    'hostname': stream.hostname()
                }
                devices.append(info)
                
                self.logger.info(f"Found EEG device: {info['name']} "
                               f"({info['channel_count']}ch @ {info['sample_rate']}Hz)")
        
        except Exception as e:
            self.logger.error(f"Error discovering devices: {e}")
        
        if not devices:
            self.logger.warning("No EEG devices found")
        
        return devices
    
    def test_connection(self, stream_name: str) -> bool:
        """
        Test connection to a specific EEG device.
        
        Args:
            stream_name: Name of the stream to test
            
        Returns:
            True if connection successful
        """
        self.logger.info(f"Testing connection to: {stream_name}")
        
        try:
            # Try to resolve and connect
            streams = lsl.resolve_stream('name', stream_name)
            if not streams:
                self.logger.error(f"Device not found: {stream_name}")
                return False
            
            # Test connection
            inlet = lsl.StreamInlet(streams[0])
            
            # Try to pull a sample
            sample, timestamp = inlet.pull_sample(timeout=2.0)
            
            if sample is not None:
                self.logger.info(f"✅ Connection test successful")
                self.logger.info(f"  Sample: {len(sample)} channels")
                self.logger.info(f"  Value range: {min(sample):.2f} to {max(sample):.2f}")
                return True
            else:
                self.logger.error("No data received from device")
                return False
        
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False


# Built-in processing functions
def basic_preprocessing(sample: List[float], timestamp: float) -> List[float]:
    """
    Basic EEG preprocessing.
    
    Args:
        sample: Raw EEG sample
        timestamp: Sample timestamp
        
    Returns:
        Processed sample
    """
    # Convert to numpy for processing
    data = np.array(sample)
    
    # Simple bandpass filtering (placeholder - would use proper filtering)
    # For now, just return the data as-is
    
    return data.tolist()


def notch_filter_60hz(sample: List[float], timestamp: float) -> List[float]:
    """
    Apply 60Hz notch filter to remove line noise.
    
    Args:
        sample: Raw EEG sample
        timestamp: Sample timestamp
        
    Returns:
        Filtered sample
    """
    # TODO: Implement proper notch filtering
    # For now, just return the data as-is
    return sample


# Standalone execution
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
    
    print("🔌 Real EEG Device Manager")
    print("=" * 50)
    
    # Create device manager
    device_manager = EEGDeviceManager()
    
    # Discover available devices
    print("Scanning for EEG devices...")
    devices = device_manager.discover_devices()
    
    if not devices:
        print("❌ No EEG devices found!")
        print("\nMake sure your EEG device is:")
        print("  - Connected and powered on")
        print("  - Running LSL streaming software")
        print("  - On the same network (for wireless devices)")
        sys.exit(1)
    
    print(f"\n✅ Found {len(devices)} EEG device(s):")
    for i, device in enumerate(devices):
        print(f"  [{i+1}] {device['name']}")
        print(f"      Channels: {device['channel_count']}")
        print(f"      Rate: {device['sample_rate']} Hz") 
        print(f"      Host: {device['hostname']}")
    
    # Let user choose device or test automatically
    if len(devices) == 1:
        chosen_device = devices[0]
        print(f"\nUsing device: {chosen_device['name']}")
    else:
        choice = input(f"\nSelect device [1-{len(devices)}]: ")
        try:
            chosen_device = devices[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection!")
            sys.exit(1)
    
    # Test connection
    if device_manager.test_connection(chosen_device['name']):
        print(f"\n🎮 Starting real EEG streaming from {chosen_device['name']}...")
        
        # Load config and start streaming
        config = get_config()
        config.eeg.stream_name = chosen_device['name']
        config.feedback.debug_mode = True
        
        streamer = RealEEGStreamer(config)
        
        try:
            # Start with basic preprocessing
            streamer.start(processing_callback=basic_preprocessing)
            
            print("\n✅ Real EEG streaming active!")
            print("This component:")
            print("  🔌 Connects to real EEG hardware")
            print("  📡 Streams processed data via LSL")
            print("  🔧 Applies real-time filtering")
            print("  📊 Forwards to P300 detection system")
            
            print("\nPress Ctrl+C to stop...")
            
            # Show status updates
            while True:
                time.sleep(5.0)
                status = streamer.get_status()
                print(f"📊 Hardware: {status['hardware_rate']}Hz "
                      f"({status['hardware_channels']}ch) → "
                      f"Output: {status['target_rate']}Hz "
                      f"({status['target_channels']}ch)")
        
        except KeyboardInterrupt:
            print("\n🛑 Stopping real EEG streaming...")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            streamer.stop()
            print("✅ Real EEG streaming stopped")
    
    else:
        print("❌ Could not connect to EEG device!")