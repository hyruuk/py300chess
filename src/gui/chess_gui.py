# chess_gui.py

from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QLabel, QApplication, QMainWindow
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
import chess
import random
from pylsl import StreamInfo, StreamOutlet
import os
import pylsl


class ChessBoardWidget(QWidget):
    # Signal to receive selected square
    square_selected = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.board = chess.Board()
        self.initUI()

        # Initialize variables for flashing
        self.flash_duration = 100  # Duration of each flash in milliseconds
        self.inter_flash_interval = 200  # Interval between flashes in milliseconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.flash_next_group)
        self.flash_sequence = []
        self.current_flash_index = 0
        self.total_cycles = 0
        self.required_cycles = 5  # Number of cycles before making a selection

        # Define stimuli groups (rows and columns)
        self.stimuli_groups = self.create_stimuli_groups()

        # Set up LSL outlet for markers
        self.marker_info = StreamInfo('Markers', 'Markers', 1, 0, 'int32', 'marker_stream')
        self.marker_outlet = StreamOutlet(self.marker_info)

        # Connect signal to a slot
        self.square_selected.connect(self.handle_square_selection)

    def initUI(self):
        grid_layout = QGridLayout()
        grid_layout.setSpacing(0)  # No space between squares
        self.squares = {}

        # Create 8x8 grid of labels
        for row in range(8):
            for col in range(8):
                label = QLabel()
                label.setFixedSize(80, 80)
                label.setAlignment(Qt.AlignCenter)  # Center the content
                color = self.get_square_color(row, col)
                label.setStyleSheet(f'background-color: {color}')
                grid_layout.addWidget(label, row, col)
                square = chess.square(col, 7 - row)
                self.squares[square] = label  # Map square index to label

        self.setLayout(grid_layout)
        self.update_board()

    def get_square_color(self, row, col):
        if (row + col) % 2 == 0:
            return '#F0D9B5'  # Light color
        else:
            return '#B58863'  # Dark color

    def update_board(self):
        # Clear all labels
        for label in self.squares.values():
            label.clear()

        # Place pieces on the board
        for square, label in self.squares.items():
            piece = self.board.piece_at(square)
            if piece:
                image_path = self.get_piece_image(piece)
                pixmap = QPixmap(image_path)

                # Scale the pixmap to fit within the label while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    label.width(),
                    label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                label.setPixmap(scaled_pixmap)
                label.setAlignment(Qt.AlignCenter)  # Ensure the pixmap is centered

    def get_piece_image(self, piece):
        # Map the piece to an image file
        piece_symbol = piece.symbol()
        color = 'w' if piece_symbol.isupper() else 'b'
        piece_type = piece_symbol.lower()
        filename = f'{color}{piece_type}.png'

        # Construct the full path to the image
        script_dir = os.path.dirname(os.path.realpath(__file__))
        images_dir = os.path.join(script_dir, 'images')
        file_path = os.path.join(images_dir, filename)

        return file_path

    def create_stimuli_groups(self):
        groups = []

        # Add rows (indices 0 to 7)
        for row in range(8):
            group = []
            for col in range(8):
                square = chess.square(col, 7 - row)
                group.append(square)
            groups.append(group)

        # Add columns (indices 8 to 15)
        for col in range(8):
            group = []
            for row in range(8):
                square = chess.square(col, 7 - row)
                group.append(square)
            groups.append(group)

        return groups

    def start_flashing(self):
        # Generate a random sequence of group indices to flash
        num_groups = len(self.stimuli_groups)
        self.flash_sequence = random.sample(range(num_groups), num_groups)
        self.current_flash_index = 0
        self.total_cycles = 0
        self.timer.start(self.inter_flash_interval)

    def flash_next_group(self):
        # Reset the color of the previous group
        if self.current_flash_index > 0:
            previous_group_index = self.flash_sequence[self.current_flash_index - 1]
            previous_group = self.stimuli_groups[previous_group_index]
            for square in previous_group:
                label = self.squares[square]
                row, col = chess.square_rank(square), chess.square_file(square)
                color = self.get_square_color(row, col)
                label.setStyleSheet(f'background-color: {color}')

        # Flash the next group
        if self.current_flash_index < len(self.flash_sequence):
            group_index = self.flash_sequence[self.current_flash_index]
            group = self.stimuli_groups[group_index]
            for square in group:
                label = self.squares[square]
                label.setStyleSheet('background-color: yellow')

            # Send marker with group index
            self.send_marker(group_index)

            self.current_flash_index += 1
        else:
            # Reset the sequence
            self.current_flash_index = 0
            self.total_cycles += 1
            if self.total_cycles >= self.required_cycles:
                # Stop flashing after required cycles
                self.timer.stop()
                print("Completed required flashing cycles.")
            else:
                # Start a new sequence
                self.flash_sequence = random.sample(range(len(self.stimuli_groups)), len(self.stimuli_groups))
                self.current_flash_index = 0

    def send_marker(self, group_index):
        # Get the current time according to LSL
        timestamp = pylsl.local_clock()
        # Send the group index as a marker with the timestamp
        self.marker_outlet.push_sample([int(group_index)], timestamp=timestamp)

    def handle_square_selection(self, row, col):
        # Highlight the selected square or make the move
        square = chess.square(col, 7 - row)
        label = self.squares[square]
        label.setStyleSheet('background-color: green')

        # You may want to update the game state here
        # For example, move a piece or prompt for the next action

        # Optionally, reset flashing for the next selection
        # self.start_flashing()

    # Additional methods for handling game logic can be added here

# The main function can remain in your main.py file
