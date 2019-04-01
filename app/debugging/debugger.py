"""Исполняет модифицированный байткод"""

import sys
from enum import Enum, auto
from threading import Thread, Event
from typing import Text, List
from types import CodeType
from queue import Queue

from .bytecode_modifier import BytecodeModifier
from .common import (
    DebugCommand, DebuggerExit, DebuggerNotStarted, EmptySourceCode)


class Debugger:
    """Отладчик"""
    _TRACE_FUNC = 'trace'
    _COMMAND = 'command'

    def __init__(self):
        self._commands = Queue()
        self._snapshots = Queue()
        self._finished = Event()

        self._bytecode_modifier = BytecodeModifier(
            self._TRACE_FUNC, self._COMMAND)
        self._globals_ = {}
        self._debug_variables = [
            self._TRACE_FUNC, self._COMMAND,
            'is_over', 'is_trace', 'first_breakpoint']

    def start(self, source: Text, filename: Text, breakpoints: List[int]):
        """
        Запускает отладчик

        Отладка программы запускается в отдельном потоке, следовательно, не
        блокирует вызывающий поток

        :param source: исходный код программы
        :param filename: название файла откуда был прочитан исходный код
        :param breakpoints: список номеров строк остановки отладки
        :raise EmptySourceCode: пустой исходный код
        """
        if not source:
            raise EmptySourceCode()

        if not self._commands.empty():
            self._commands = Queue()

        if not self._snapshots.empty():
            self._snapshots = Queue()

        modified_code = self._compile(source, filename, breakpoints)

        t = Thread(target=self._bootstrap, args=(modified_code, ), daemon=True)
        t.start()

    def send_command(self, command: DebugCommand):
        """
        Отправляет команду отладчику

        :raise DebuggerNotStarted: отладчик не запущен
        """
        self._commands.put(command)

    def get_snapshot(self) -> dict:
        """
        Блокирует вызывающий поток до тех пор, пока не появится новое состояние
        (команды step over, step in, step out) или отладка не завершится
        (команда stop)

        Структура:
            - словарь глобальных переменных
            - словарь локальных переменных
            - номер отлаживаемой строки
        :return: данные о текущем состояний отлаживаемой программы
        :raise DebuggingFinished: при завершении отладки
        """
        snapshot = self._snapshots.get()

        if snapshot is DebuggerExit:
            raise DebuggerExit('Отладка закончена')

        return snapshot

    def finish(self):
        """
        Завершает отладчик

        Вызов данного метода не завершает отладку сразу, а
        отправляет потоку отладки команду завершения.
        Чтобы дождаться полного завершения используйте вызов метода `join`
        """
        self._commands.put(DebuggerExit)

    def join(self):
        """
        Дожидается завершения работы отладчика

        Блокирует вызывающий поток
        """
        self._finished.wait()

    def _compile(
            self, source: Text, filename: Text,
            breakpoints: List[int]) -> CodeType:
        """Компилирует исходный код программы в модифицированный байткод"""
        try:
            code = compile(source, filename, 'exec')
        except (SyntaxError, ValueError) as e:
            raise e

        modified_code = self._bytecode_modifier.modify(code, breakpoints)

        return modified_code

    # все методы ниже выполняются в другом потоке
    # в потоке отладки
    def _bootstrap(self, code):
        try:
            self._run(code)
        except DebuggerExit:
            pass
        finally:
            self._snapshots.put(DebuggerExit)
            self ._finished.set()

    def _run(self, code):
        self._globals_ = {
            self._TRACE_FUNC: self._trace,
            self._COMMAND: None
        }
        exec(code, self._globals_)

    def _trace(self):
        frame = sys._getframe(1)
        snapshot = {
            'global_variables': self._sanitize(frame.f_globals),
            'local_variables': self._sanitize(frame.f_locals),
            'line_no': frame.f_lineno
        }
        self._snapshots.put(snapshot)

        command = self._commands.get()

        if command is DebuggerExit:
            raise DebuggerExit()

        self._globals_[self._COMMAND] = command

    def _sanitize(self, variables):
        sanitized = {}

        for k, v in variables.copy().items():
            if k in self._debug_variables:
                continue

            sanitized[k] = v if isinstance(v, str) else repr(v)

        return sanitized
