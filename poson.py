import sys

from PyQt5.QtWidgets import QApplication

from app.debugger_client import DebuggerClient
from app.ui import MainWindow
from app.utils import QThreadRunner


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    debugger_client = DebuggerClient()

    debugger_client.update.connect(window.update)
    debugger_client.debugging_finished.connect(window.on_finish)

    window.start_clicked.connect(debugger_client.start)
    window.step_over_clicked.connect(debugger_client.step_over)
    window.step_in_clicked.connect(debugger_client.step_in)
    window.step_out_clicked.connect(debugger_client.step_out)
    window.stop_clicked.connect(debugger_client.finish)

    # window.showMaximized()
    window.show()

    debugging_thread = QThreadRunner(target=debugger_client)
    debugging_thread.start()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
