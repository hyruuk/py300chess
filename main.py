# main.py

from PyQt5.QtWidgets import QApplication, QMainWindow
from src.gui.chess_gui import ChessBoardWidget
from src.eeg.eeg_data_acquisition import EEGDataAcquisition
import sys

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    chessboard = ChessBoardWidget()
    window.setCentralWidget(chessboard)
    window.setWindowTitle("P300 BCI Chess")
    window.resize(800, 800)
    window.show()

    # Create EEG data acquisition thread
    eeg_thread = EEGDataAcquisition(chessboard)

    # Connect signals
    eeg_thread.square_selected_signal.connect(chessboard.handle_square_selection)

    # Start the EEG thread before flashing
    eeg_thread.start()

    # Start flashing after the EEG thread is running
    chessboard.start_flashing()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
