# eeg_data_acquisition.py

from pylsl import StreamInlet, resolve_byprop
import numpy as np
import time
from collections import deque
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from PyQt5.QtCore import QObject, pyqtSignal, QThread

class EEGDataAcquisition(QThread):
    # Signal to emit the selected square (row, column)
    square_selected_signal = pyqtSignal(int, int)

    def __init__(self, gui_widget):
        super().__init__()
        # Resolve EEG data stream
        print("Looking for an EEG stream...")
        eeg_streams = resolve_byprop('type', 'EEG', timeout=5)
        if not eeg_streams:
            raise RuntimeError('Cannot find EEG stream.')
        self.eeg_inlet = StreamInlet(eeg_streams[0])

        # Resolve Marker stream
        print("Looking for a Markers stream...")
        marker_streams = resolve_byprop('name', 'Markers', timeout=5)
        if not marker_streams:
            raise RuntimeError('Cannot find Markers stream.')
        self.marker_inlet = StreamInlet(marker_streams[0])

        # Initialize buffers and variables
        self.eeg_buffer = deque()
        self.marker_queue = deque()
        self.fs = int(self.eeg_inlet.info().nominal_srate())  # Sampling rate
        self.num_channels = self.eeg_inlet.info().channel_count()

        # Parameters for epoch extraction
        self.pre_time = 0.2   # 200 ms before marker
        self.post_time = 0.8  # 800 ms after marker
        self.epoch_length = int((self.pre_time + self.post_time) * self.fs)

        # Storage for epochs and labels
        self.epochs = []
        self.labels = []

        # For classification
        self.target_groups = None  # To be set during training or runtime
        self.required_cycles = 5   # Number of cycles before making a decision

        # Classifier and scaler
        self.scaler = StandardScaler()
        self.classifier = LogisticRegression()
        self.is_trained = False  # Flag to check if the classifier is trained
        self.confidence_threshold = 0.5  # Default confidence threshold

        self.gui_widget = gui_widget

    def set_confidence_threshold(self, threshold):
        self.confidence_threshold = threshold
        print(f"Confidence threshold set to: {self.confidence_threshold}")

    def run(self):
        print("Starting data acquisition...")
        while True:
            # Pull EEG samples
            eeg_sample, eeg_timestamp = self.eeg_inlet.pull_sample(timeout=0.0)
            if eeg_sample is not None:
                self.eeg_buffer.append((eeg_timestamp, eeg_sample))
                # Keep buffer size reasonable
                while (self.eeg_buffer[-1][0] - self.eeg_buffer[0][0]) > 10:  # Keep last 10 seconds
                    self.eeg_buffer.popleft()

            # Pull markers
            marker_sample, marker_timestamp = self.marker_inlet.pull_sample(timeout=0.0)
            if marker_sample is not None:
                group_index = int(marker_sample[0])
                self.marker_queue.append((marker_timestamp, group_index))
                print(f"Received marker for group {group_index} at time {marker_timestamp}")

            # Check for new markers and segment data
            while self.marker_queue:
                marker_timestamp, group_index = self.marker_queue.popleft()
                print(f"Processing marker for group {group_index} at time {marker_timestamp}")

                # Segment EEG data around the marker
                epoch = self.get_eeg_epoch(marker_timestamp)
                if epoch is not None:
                    # Label the epoch (1 for target, 0 for non-target)
                    label = self.is_target_group(group_index)

                    # Store the epoch and label
                    self.epochs.append(epoch)
                    self.labels.append(label)
                    print(f"Stored epoch for group {group_index} with label {label}")

                    # After required cycles, perform classification
                    if len(self.labels) >= self.required_cycles * 16:
                        self.classify_and_reset()

            # Sleep briefly
            time.sleep(0.01)

    def get_eeg_epoch(self, marker_time):
        # Calculate start and end times
        start_time = marker_time - self.pre_time
        end_time = marker_time + self.post_time

        # Extract EEG data within the time window
        samples = [sample for timestamp, sample in self.eeg_buffer if start_time <= timestamp <= end_time]

        if len(samples) < self.epoch_length:
            print("Not enough EEG data for epoch.")
            return None

        # Convert to numpy array
        epoch_array = np.array(samples)
        return epoch_array

    def is_target_group(self, group_index):
        # Define the target row and column indices
        if self.target_groups is None:
            # For training, set the target groups here
            # For example, assume the target square is at row 3 and column 5
            target_row = 3  # Row indices 0-7
            target_col = 5  # Column indices 0-7
            self.target_groups = [target_row, target_col + 8]  # Column indices start at 8
            print(f"Target groups set to: {self.target_groups}")

        # Return 1 for target group, 0 for non-target
        return 1 if group_index in self.target_groups else 0

    def classify_and_reset(self):
        print("Performing classification...")

        # Prepare data for classification
        X = np.array([epoch.flatten() for epoch in self.epochs])
        y = np.array(self.labels)

        # Feature scaling
        X_scaled = self.scaler.fit_transform(X)

        if not self.is_trained:
            # Train the classifier
            self.classifier.fit(X_scaled, y)
            self.is_trained = True
            print("Classifier trained.")
        else:
            # Use the classifier to predict probabilities
            probabilities = self.classifier.predict_proba(X_scaled)[:, 1]  # Probability of class 1 (target)

            # Sum probabilities for each group over the cycles
            group_probabilities = [0] * 16
            for i, prob in enumerate(probabilities):
                group_index = i % 16
                group_probabilities[group_index] += prob

            # Average probabilities over the number of cycles
            num_cycles = len(self.labels) // 16
            group_probabilities = [gp / num_cycles for gp in group_probabilities]

            # Identify groups exceeding the confidence threshold
            confident_groups = [i for i, gp in enumerate(group_probabilities) if gp >= self.confidence_threshold]

            if len(confident_groups) >= 2:
                # Expecting one row and one column
                selected_row = None
                selected_col = None
                for group_index in confident_groups:
                    if group_index < 8:
                        selected_row = group_index
                    else:
                        selected_col = group_index - 8

                if selected_row is not None and selected_col is not None:
                    print(f"Selected row: {selected_row}, Selected column: {selected_col}")
                    selected_square = (selected_row, selected_col)
                    print(f"Selected square: {selected_square}")

                    # Emit the signal to the GUI
                    self.square_selected_signal.emit(selected_row, selected_col)
                else:
                    print("Confidence threshold met, but could not determine both row and column.")
            else:
                print("Confidence threshold not met for both row and column. No selection made.")

        # Reset epochs and labels for the next selection
        self.epochs = []
        self.labels = []

    # Additional methods for feature extraction and classifier training can be added here

# No changes to the main block as this class is now intended to be used within the GUI application
