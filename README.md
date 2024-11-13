# P300-Based BCI Chess Application

This project is a Brain-Computer Interface (BCI) application that allows users to play chess using their brain signals, specifically detecting P300 event-related potentials (ERPs). The application uses Python and the Lab Streaming Layer (LSL) protocol to acquire EEG data, process it, and interpret user intent to select chessboard squares.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [TODOs](#todos)
- [License](#license)

## Introduction

The P300-Based BCI Chess Application enables users to interact with a chess game using their brain signals. By detecting P300 responses to visual stimuli on a chessboard, the system interprets the user's intended move. This project is ideal for exploring BCI technology and its applications in assistive technologies and gaming.

## Features

- **EEG Data Acquisition**: Real-time acquisition of EEG data using LSL.
- **Visual Stimuli Presentation**: Flashing chessboard squares to elicit P300 responses.
- **Signal Processing**: Epoch extraction and preprocessing of EEG data.
- **Machine Learning Classification**: Training a classifier to detect P300 signals.
- **User Interface**: Graphical chessboard interface for interaction.

## Requirements

- Python 3.7 or higher
- Required Python packages:
  - `numpy`
  - `scipy`
  - `scikit-learn`
  - `pyqt5`
  - `pylsl` (Lab Streaming Layer for Python)
- An EEG device compatible with LSL or the provided fake EEG data generator.

## Installation

1. **Clone the Repository**

   [CODE BLOCK: CLONE AND NAVIGATE TO REPOSITORY]

2. **Create a Virtual Environment (Optional but Recommended)**

   [CODE BLOCK: CREATE AND ACTIVATE VIRTUAL ENVIRONMENT]

3. **Install Required Packages**

   [CODE BLOCK: INSTALL REQUIRED PACKAGES]

4. **Install Lab Streaming Layer (LSL)**

   - Download the LSL distribution from the [official repository](https://github.com/sccn/labstreaminglayer).
   - Follow the installation instructions for your operating system.

## Usage

### 1. Start the EEG Data Stream

- **Using an Actual EEG Device**

  - Ensure your EEG device is connected and streaming data via LSL.

- **Using the Fake EEG Data Generator**

  - Open a new terminal window.
  - [CODE BLOCK: RUN FAKE EEG STREAM GENERATOR]

### 2. Run the Application

[CODE BLOCK: RUN MAIN APPLICATION]

### 3. Interact with the Application

- The chessboard GUI will appear.
- The application will begin the calibration phase to collect training data.
- Follow on-screen instructions to focus on flashing squares.
- After calibration, the application will attempt to detect your intended chess moves based on P300 responses.

## Project Structure

- `main.py`: Entry point of the application. Initializes the GUI and starts the EEG data acquisition thread.
- `chess_gui.py`: Contains the GUI code for the chessboard and handles user interactions.
- `eeg_data_acquisition.py`: Contains the `EEGDataAcquisition` class responsible for acquiring EEG data and processing markers.
- `fake_eeg_stream.py`: Simulates an EEG data stream for testing purposes.
- `requirements.txt`: Lists all Python dependencies.
- `README.md`: Project documentation.

## Troubleshooting

- **EEG Data Not Received**

  - Ensure that your EEG device or the fake EEG data generator is running.
  - Verify that the EEG data stream is correctly named and of type `'EEG'` in LSL.

- **Insufficient Epoch Samples**

  - Make sure that the EEG data acquisition thread starts before the flashing sequence.
  - Verify that there is sufficient delay between starting data acquisition and generating markers to allow the buffer to fill.
  - Check time synchronization between EEG data and markers.

- **Timing Drift Issues**

  - Ensure that the `run` method in `EEGDataAcquisition` uses precise loop timing with `time.perf_counter()`.
  - Avoid arbitrary `time.sleep()` calls in the data acquisition loop.

## TODOs

- [ ] **Resolve Insufficient Epoch Samples Issue**

  - Investigate why the EEG buffer lacks enough data during epoch extraction.
  - Ensure the EEG data acquisition starts early enough before markers are received.
  - Verify correct application of time corrections and synchronization between EEG data and markers.

- [ ] **Implement P300 Detection and Classification**

  - Finalize the signal processing pipeline for P300 detection.
  - Train and test the machine learning classifier with collected data.
  - Optimize feature extraction and classification parameters.

- [ ] **Enhance User Interface**

  - Improve the GUI responsiveness and visual appeal.
  - Add instructions and feedback for the user during calibration and gameplay.

- [ ] **Add Real EEG Device Support**

  - Test the application with actual EEG hardware.
  - Ensure compatibility with various EEG devices that support LSL.

- [ ] **Code Optimization and Refactoring**

  - Clean up the codebase for better readability and maintainability.
  - Add comments and documentation to explain complex sections.

- [ ] **Error Handling and Robustness**

  - Implement comprehensive exception handling.
  - Ensure the application can recover gracefully from errors.

- [ ] **Unit Testing**

  - Write unit tests for critical components to ensure reliability.
  - Set up continuous integration to automate testing.

- [ ] **Documentation**

  - Expand the README with detailed usage examples.
  - Document each module and function within the code.

- [ ] **License and Contribution Guidelines**

  - Decide on a license for the project (e.g., MIT, GPL).
  - Add a `CONTRIBUTING.md` file to guide future contributors.

## License

This project is licensed under the [MIT License](LICENSE).

---

**Note:** This application is currently under development. Contributions and feedback are welcome!
