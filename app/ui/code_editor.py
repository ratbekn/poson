from functools import partial

from PyQt5.QtWidgets import QWidget, QPlainTextEdit, QTextEdit
from PyQt5.QtGui import (
    QColor, QTextFormat, QPainter, QTextCursor, QTextDocument, QFontMetricsF,
    QIcon)
from PyQt5.QtCore import Qt, QRect, QSize, QEvent, QPoint, QObject, pyqtSignal

from . import resources


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super(LineNumberArea, self).__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        digits = 1
        max_ = max(1, self.code_editor.blockCount())
        while max_ >= 10:
            max_ /= 10
            digits += 1

        space = 3 + self.fontMetrics().width('9') * digits

        return QSize(space, 0)

    def resizeEvent(self, event):
        super(LineNumberArea, self).resizeEvent(event)

    def paintEvent(self, event):
        super(LineNumberArea, self).paintEvent(event)
        painter = QPainter(self)

        for top, block_number, block in self.code_editor._visible_blocks:
            if block.isVisible():
                number = str(block_number + 1)
                painter.setPen(Qt.black)
                painter.drawText(
                    0, top, self.width(),
                    self.fontMetrics().height(), Qt.AlignCenter, number)


class Breakpoint(QObject):
    def __init__(self, line, icon='', parent=None):
        super(Breakpoint, self).__init__(parent)

        self.line = line
        self._icon = icon


class BreakpointArea(QWidget):
    def __init__(self, editor):
        super(BreakpointArea, self).__init__()

        self.editor = editor
        self.setParent(editor)
        self.breakpoints = []
        self.scrollable = True

    def add_breakpoint(self, brkpnt):
        self.breakpoints.append(brkpnt)
        doc = self.editor.document()
        block = doc.findBlockByLineNumber(brkpnt.line)
        brkpnt.block = block
        self.repaint()

    def remove_breakpoint(self, brkpnt):
        self.breakpoints.remove(brkpnt)
        self.repaint()

    def clear_breakpoints(self):
        self.breakpoints = []
        self.repaint()

    def breakpoint_for_line(self, line):
        for brkpnt in self.breakpoints:
            if brkpnt.line == line:
                return brkpnt

        return None

    def sizeHint(self):
        metrics = QFontMetricsF(self.editor.font())
        size_hint = QSize(metrics.height(), metrics.height())

        if size_hint.width() > 16:
            size_hint.setWidth(16)

        return size_hint

    def paintEvent(self, event):
        super(BreakpointArea, self).paintEvent(event)

        painter = QPainter(self)
        painter.fillRect(event.rect(), Qt.lightGray)

        for top, block_nbr, block in self.editor._visible_blocks:
            for brpnt in self.breakpoints:
                if brpnt.block == block and brpnt._icon:
                    rect = QRect()
                    rect.setX(0)
                    rect.setY(top)
                    rect.setWidth(self.sizeHint().width())
                    rect.setHeight(self.sizeHint().height())
                    brpnt._icon.paint(painter, rect)

    def mousePressEvent(self, event):
        line = self.line_number_from_position(event.pos().y())
        brkpnt = self.breakpoint_for_line(line)

        if brkpnt is not None:
            if event.button() == Qt.LeftButton:
                self.remove_breakpoint(brkpnt)
        else:
            self.add_breakpoint(
                Breakpoint(line, QIcon(':/icons/breakpoint.png'), self))

    def line_number_from_position(self, y_pos):
        height = self.editor.fontMetrics().height()

        for top, line, block in self.editor._visible_blocks:
            if top <= y_pos <= top + height:
                return line

        return -1


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super(CodeEditor, self).__init__()

        self.breakpoint_area = BreakpointArea(self)
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self._update_areas_width)
        self.updateRequest.connect(self._update_areas)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_areas_width(0)
        self._highlight_current_line()

        self._visible_blocks = []

    def _update_areas_width(self, _):
        self.setViewportMargins(
            self.line_number_area.sizeHint().width()
            + self.breakpoint_area.sizeHint().width(), 0, 0, 0)

    def _update_areas(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
            self.breakpoint_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(),
                self.line_number_area.sizeHint().width(), rect.height())
            self.breakpoint_area.update(
                0, rect.y(),
                self.breakpoint_area.sizeHint().width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self._update_areas_width(0)

    def _highlight_current_line(self):
        color = QColor(255, 255, 0)
        self.highlight_line(self.textCursor(), color)

    def highlight_line(self, text_cursor, color):
        extra_selections = []

        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(color)
        selection.format.setProperty(
            QTextFormat.FullWidthSelection, True)

        selection.cursor = text_cursor
        selection.cursor.clearSelection()

        extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def _update_visible_blocks(self, _):
        self._visible_blocks[:] = []
        block = self.firstVisibleBlock()
        block_nbr = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        ebottom_top = 0
        ebottom_bottom = self.height()
        while block.isValid():
            visible = (top >= ebottom_top and bottom <= ebottom_bottom)
            if not visible:
                break
            if block.isVisible():
                self._visible_blocks.append((top, block_nbr, block))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_nbr = block.blockNumber()

    def resizeEvent(self, event):
        super(CodeEditor, self).resizeEvent(event)

        cr = self.contentsRect()
        breakpoint_area_width = self.breakpoint_area.sizeHint().width()
        line_number_area_width = self.line_number_area.sizeHint().width()
        self.breakpoint_area.setGeometry(QRect(
            cr.left(), cr.top(),
            breakpoint_area_width, cr.height()))
        self.line_number_area.setGeometry(QRect(
            breakpoint_area_width, cr.top(),
            line_number_area_width, cr.height()))

    def paintEvent(self, event):
        super(CodeEditor, self).paintEvent(event)

        self._update_visible_blocks(event)
