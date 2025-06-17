from pylsl import StreamInlet, resolve_byprop

# Resolve the EEG stream
print("Looking for an EEG stream...")
streams = resolve_byprop('type', 'EEG', timeout=5)

if not streams:
    raise RuntimeError('Cannot find EEG stream.')

# Create an inlet to receive data
inlet = StreamInlet(streams[0])

print("Connected to EEG stream.")

while True:
    # Receive a sample
    sample, timestamp = inlet.pull_sample()
    print(f"Timestamp: {timestamp}, Sample: {sample}")
