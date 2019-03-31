from PyQt5.QtCore import QObject, pyqtSignal

from .debugging import Debugger, DebugCommand, DebuggerExit
from .utils import RunnableMixin


class DebuggerClient(RunnableMixin, QObject):
    debugging_finished = pyqtSignal()
    update = pyqtSignal(dict, dict, int)

    def __init__(self):
        super(DebuggerClient, self).__init__()

        self._debugger = Debugger()

    def start(self, source, filename='<string>'):
        self._debugger.start(source, filename)

    def step_over(self):
        self._debugger.send_command(DebugCommand.STEP_OVER)

    def step_in(self):
        self._debugger.send_command(DebugCommand.STEP_IN)

    def step_out(self):
        self._debugger.send_command(DebugCommand.STEP_OUT)

    def finish(self):
        self._debugger.finish()

    def run(self):
        while True:
            try:
                snapshot = self._debugger.get_snapshot()

                self.update.emit(
                    snapshot['global_variables'],
                    snapshot['local_variables'],
                    snapshot['line_no'])
            except DebuggerExit:
                self.debugging_finished.emit()
