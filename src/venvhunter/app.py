from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from venvhunter.ui.main_window import MainWindow

APP_NAME = "DevCleaner"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_NAME)

    window = MainWindow()
    window.resize(1180, 760)
    window.show()

    return app.exec()
