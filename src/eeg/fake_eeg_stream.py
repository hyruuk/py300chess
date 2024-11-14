# fake_eeg_stream.py

import time
import numpy as np
from pylsl import StreamInfo, StreamOutlet, local_clock

# Number of EEG channels
n_channels = 19

# Sampling rate in Hz
sampling_rate = 250
sampling_interval = 1.0 / sampling_rate

# Chunk size (number of samples per chunk)
chunk_size = 25  # Adjust as needed

# Create StreamInfo object
info = StreamInfo(
    name='FakeEEG',
    type='EEG',
    channel_count=n_channels,
    nominal_srate=sampling_rate,
    channel_format='float32',
    source_id='fake_eeg_stream'
)

# Add channel labels
chns = info.desc().append_child("channels")
for c in range(n_channels):
    ch = chns.append_child("channel")
    ch.append_child_value("label", f"Ch{c+1}")
    ch.append_child_value("unit", "microvolts")
    ch.append_child_value("type", "EEG")

# Create the outlet
outlet = StreamOutlet(info, chunk_size)

print("Now streaming fake EEG data...")

# Start streaming data
while True:
    # Generate a chunk of data
    chunk = []
    timestamps = []
    for i in range(chunk_size):
        sample = np.random.randn(n_channels).tolist()
        timestamp = local_clock()
        chunk.append(sample)
        timestamps.append(timestamp)
        time.sleep(sampling_interval)

    # Push the chunk to the outlet
    outlet.push_chunk(chunk, timestamps)
