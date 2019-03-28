import sys
from multiprocessing import Queue

from PyQt5.QtCore import (
    Qt, QObject, QThread, pyqtSignal, QAbstractTableModel, QVariant,
    QModelIndex)
from PyQt5.QtWidgets import QApplication

from app.debugging import Debugger, DebuggingEvent, DebuggingEventType
from app.userinterface.graphical_ui import MainWindow


class QThreadRunner(QThread):
    """Класс обёртка над QThread для запуска задач в отдельном потоке"""
    def __init__(self, *, task=None, args=()):
        super(QThreadRunner, self).__init__()

        self.task = task
        self.args = args

    def run(self):
        if self.task:
            self.task(*self.args)


class DebuggerAdapter(QObject):
    """Адаптер отладчика специфичный для PyQt

    Подсистема отладки должна быть максимально изолированной и самостоятельной.
    И не зависить от реализаций подсистемы взаимодействия с пользователем.
    Добавляет подсистеме отладки возможность общаться с подсистемой
    взаимодействия с пользователем через систему сигналов и слотов PyQT"""
    on_step_over = pyqtSignal(int, dict, dict)
    on_finish = pyqtSignal()

    def __init__(self, debugging_events):
        super(DebuggerAdapter, self).__init__()

        self._debugger = Debugger(debugging_events=debugging_events)

    def __call__(self):
        self.run()

    def run(self):
        while True:
            event = self._debugger.debugging_events.get()

            if event.type is DebuggingEventType.STEP_OVER:
                self.on_step_over.emit(
                    event.line_no,
                    event.globals_,
                    event.locals_)

            if event.type is DebuggingEventType.STOP:
                self.on_finish.emit()

            if event.type is DebuggingEventType.FINISH:
                self.on_finish.emit()

    def debug(self, source, filename='<string>'):
        self._debugger.debug(source, filename)

    def step_over(self):
        self._debugger.step_over()

    def step_in(self):
        pass

    def step_out(self):
        pass

    def stop(self):
        self._debugger.stop()


class WatcherModel(QAbstractTableModel):
    """
    Модель-обёртка над dict для отображения переменных в QTableView
    """
    def __init__(self, data):
        super(WatcherModel, self).__init__()

        self.data_model = data

    def update(self, new_data):
        self.layoutAboutToBeChanged.emit()
        self.data_model.update(new_data)
        self.dataChanged.emit(
            self.createIndex(0, 0),
            self.createIndex(self.rowCount(0), self.columnCount(0)),
            [])
        self.layoutChanged.emit()

    def rowCount(self, index):
        return len(self.data_model)

    def columnCount(self, index):
        return 2

    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = index.row()

            var, value = tuple(self.data_model.items())[row]

            column = index.column()

            return var if column == 0 else value

        return QVariant()

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return 'variable' if section == 0 else 'value'

        return QVariant()


def main():
    app = QApplication(sys.argv)

    debugging_events = Queue()
    debugging = DebuggerAdapter(debugging_events)

    window = MainWindow()

    debugging.on_step_over.connect(window.on_step_over)
    debugging.on_finish.connect(window.on_finish)

    window.start_debug.connect(debugging.debug)
    window.step_over.connect(debugging.step_over)
    window.stop_debug.connect(debugging.stop)

    # window.showMaximized()
    window.show()

    debugging_thread = QThreadRunner(task=debugging)
    debugging_thread.start()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
