# main.py

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow

# Import ChessBoardWidget from the gui package
from src.gui.chess_gui import ChessBoardWidget

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    chessboard = ChessBoardWidget()
    window.setCentralWidget(chessboard)
    window.setWindowTitle("P300 BCI Chess")
    window.resize(800, 800)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
