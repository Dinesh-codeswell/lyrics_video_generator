"""GUI entry point for lyric-video-generator."""

import sys

from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Durt Nurs Lyric Video Generator")
    app.setStyleSheet("""
        QGroupBox {
            font-size: 14pt;
            font-weight: 600;
            margin-top: 26px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            top: 4px;
            padding: 0 4px;
        }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
