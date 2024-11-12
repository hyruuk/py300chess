from pylsl import StreamInlet, resolve_byprop

# Resolve an EEG stream on the lab network
print("Looking for an EEG stream...")
streams = resolve_byprop('type', 'EEG', timeout=5)

if len(streams) == 0:
    raise RuntimeError('Cannot find EEG stream.')

# Create a new inlet to read from the stream
inlet = StreamInlet(streams[0])

print("Connected to EEG stream.")
