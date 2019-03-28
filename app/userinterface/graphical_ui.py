from PyQt5.QtCore import pyqtSignal, Qt, QSize, QAbstractTableModel, QVariant
from PyQt5.QtGui import QIcon, QTextCursor, QColor
from PyQt5.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar, QAction, QFileDialog, QDockWidget,
    QLabel, qApp, QPlainTextEdit, QTableView, QHeaderView)

from .code_editor import CodeEditor
from . import resources


class WatcherModel(QAbstractTableModel):
    """
    Модель-обёртка над dict для отображения переменных в QTableView
    """
    def __init__(self, data=None):
        super(WatcherModel, self).__init__()

        self.data_model = data or {}

    def update(self, new_data):
        self.layoutAboutToBeChanged.emit()
        self.data_model.update(new_data)
        self.layoutChanged.emit()

    def clear(self):
        self.layoutAboutToBeChanged.emit()
        self.data_model = {}
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


class MainWindow(QMainWindow):
    start_debug = pyqtSignal(str)
    step_over = pyqtSignal()
    stop_debug = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle('Debugger')

        self._open_act = self._create_act(
            'Open', 'open.png',
            shortcut='Ctrl+O',
            status_tip='Open file',
            handler=self._show_open_dialog)
        self._exit_act = self._create_act(
            'Exit', 'exit.png',
            shortcut='Ctrl+W',
            status_tip='Close app',
            handler=self.close)

        self._start_debug_act = self._create_act(
            'Start Debug', 'debug.png',
            shortcut='Ctrl+F5',
            status_tip='debug program',
            handler=self._start_debug)
        self._step_over_act = self._create_act(
            'Step Over', 'step_over.png',
            shortcut='F8',
            status_tip='step to the next line in this file',
            handler=self._step_over)
        self._step_in_act = self._create_act(
            'Step In', 'step_in.png',
            shortcut='F7',
            status_tip='step to the next line executed',
            handler=self._step_in)
        self._step_out_act = self._create_act(
            'Step Out', 'step_out.png',
            shortcut='F9',
            status_tip='step to the first line executed after '
                       'returning from this method',
            handler=self._stop_out)
        self._stop_debug_act = self._create_act(
            'Stop Debug', 'stop.png',
            shortcut='Ctrl+F2',
            status_tip='stop debugging program',
            handler=self._stop_debug)

        self._menu_bar = self.menuBar()
        self._init_menu_bar()

        self._toolbar = QToolBar('toolbar')
        self._init_toolbar()

        self._status_bar = QStatusBar(self)
        self._init_status_bar()

        self._globals_watcher = QTableView()
        self._globals_watcher_model = WatcherModel()
        self._init_globals_watcher()
        self._globals_watcher_dock = QDockWidget('global variables', self)
        self._init_globals_watcher_dock()

        self._locals_watcher = QTableView()
        self._locals_watcher_model = WatcherModel()
        self._init_locals_watcher()
        self._locals_watcher_dock = QDockWidget('local variables', self)
        self._init_locals_watcher_dock()

        self.tabifyDockWidget(
            self._globals_watcher_dock, self._locals_watcher_dock)

        self._call_stack_dock = QDockWidget('call stack', self)
        self._init_call_stack_dock()

        self.code_editor = CodeEditor()
        self.setCentralWidget(self.code_editor)

    def _create_act(
            self, name, icon, shortcut=None, status_tip=None,
            handler=None):
        new_action = QAction(QIcon(f':/icons/{icon}'), name, self)
        if shortcut is not None:
            new_action.setShortcut(shortcut)
        if status_tip is not None:
            new_action.setStatusTip(status_tip)
        if handler is not None:
            new_action.triggered.connect(handler)

        return new_action

    def _show_open_dialog(self):
        file_name = QFileDialog.getOpenFileName(self, 'Open file', '/home')

        if file_name[0]:
            with open(file_name[0]) as f:
                source = f.read()
                self.code_editor.setPlainText(source)

    def _start_debug(self):
        source = self.code_editor.toPlainText()

        if not source:
            return

        self.code_editor.setDisabled(True)

        self.start_debug.emit(source)

    def _step_over(self):
        self.step_over.emit()

    def _step_in(self):
        pass

    def _stop_out(self):
        pass

    def _stop_debug(self):
        self.stop_debug.emit()
        self._finish_debug()

    def _finish_debug(self):
        self.code_editor.setEnabled(True)
        qApp.setCursorFlashTime(qApp.cursorFlashTime())

    def _init_menu_bar(self):
        file_menu = self._menu_bar.addMenu('&File')
        file_menu.addAction(self._open_act)
        file_menu.addAction(self._exit_act)

    def _init_toolbar(self):
        self._toolbar.setIconSize(QSize(16, 16))

        self._toolbar.addAction(self._start_debug_act)
        self._toolbar.addAction(self._step_over_act)
        self._toolbar.addAction(self._step_in_act)
        self._toolbar.addAction(self._step_out_act)
        self._toolbar.addAction(self._stop_debug_act)

        self.addToolBar(self._toolbar)

    def _init_status_bar(self):
        self.setStatusBar(self._status_bar)

    def _init_globals_watcher(self):
        self._globals_watcher.setModel(self._globals_watcher_model)

        header = self._globals_watcher.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self._globals_watcher.setWordWrap(False)

    def _init_globals_watcher_dock(self):
        self._globals_watcher_dock.setAllowedAreas(Qt.RightDockWidgetArea)

        self._globals_watcher_dock.setWidget(self._globals_watcher)

        self.addDockWidget(Qt.RightDockWidgetArea, self._globals_watcher_dock)

    def _init_locals_watcher(self):
        self._locals_watcher.setModel(self._locals_watcher_model)

        header = self._locals_watcher.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self._locals_watcher.setWordWrap(False)

    def _init_locals_watcher_dock(self):
        self._locals_watcher_dock.setAllowedAreas(Qt.RightDockWidgetArea)

        self._locals_watcher_dock.setWidget(self._locals_watcher)

        self.addDockWidget(Qt.RightDockWidgetArea, self._locals_watcher_dock)

    def _init_call_stack_dock(self):
        self._call_stack_dock.setAllowedAreas(
            Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

        label = QLabel('This is call trace dock widget')
        self._call_stack_dock.setWidget(label)

        self.addDockWidget(Qt.RightDockWidgetArea, self._call_stack_dock)

    def on_step_over(self, line_no, globals_, locals_):
        self._highlight_line(line_no)
        self._globals_watcher_model.update(globals_)
        self._locals_watcher_model.update(locals_)

    def _highlight_line(self, line_no):
        if not line_no:
            return

        line_no_text_block = (self.code_editor
                              .document()
                              .findBlockByLineNumber(line_no - 1))
        cursor = QTextCursor(line_no_text_block)
        self.code_editor.highlight_line(cursor, QColor(255, 0, 0))

    def on_finish(self):
        self.code_editor.setEnabled(True)

        self.code_editor.highlight_line(
            self.code_editor.textCursor(), QColor(255, 255, 0))

        self._globals_watcher_model.clear()
        self._locals_watcher_model.clear()
