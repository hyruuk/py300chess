# fake_eeg_stream.py

import time
import numpy as np
from pylsl import StreamInfo, StreamOutlet

# Number of EEG channels
n_channels = 19

# Sampling rate in Hz
sampling_rate = 250

# Create StreamInfo object
info = StreamInfo(
    name='FakeEEG',
    type='EEG',
    channel_count=n_channels,
    nominal_srate=sampling_rate,
    channel_format='float32',
    source_id='fake_eeg_stream'
)

# Add channel labels (optional but helpful)
chns = info.desc().append_child("channels")
for c in range(n_channels):
    ch = chns.append_child("channel")
    ch.append_child_value("label", f"Ch{c+1}")
    ch.append_child_value("unit", "microvolts")
    ch.append_child_value("type", "EEG")

# Create the outlet
outlet = StreamOutlet(info)

print("Now streaming fake EEG data...")

# Start streaming data
start_time = time.time()
while True:
    # Generate a random sample for each channel
    sample = np.random.randn(n_channels).tolist()

    # Alternatively, simulate a sinusoidal signal for testing
    # t = time.time() - start_time
    # sample = (np.sin(2 * np.pi * 10 * t) * 10).tolist()

    # Push the sample to the outlet
    outlet.push_sample(sample)

    # Sleep to mimic the sampling rate
    time.sleep(1.0 / sampling_rate)
