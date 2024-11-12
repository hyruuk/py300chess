from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QLabel, QApplication, QMainWindow
)
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt
import sys
import chess

class ChessBoardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.board = chess.Board()
        self.initUI()

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
                pixmap = QPixmap(self.get_piece_image(piece))
                label.setPixmap(pixmap)

    def get_piece_image(self, piece):
        # Map the piece to an image file
        piece_symbol = piece.symbol()
        color = 'w' if piece_symbol.isupper() else 'b'
        piece_type = piece_symbol.lower()
        filename = f'images/{color}{piece_type}.png'
        return filename