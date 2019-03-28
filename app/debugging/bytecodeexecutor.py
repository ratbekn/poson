"""Исполняет модифицированный байткод"""

import sys
from enum import Enum, auto
from multiprocessing import Queue

from .bytecodemodifier import modify


class DebuggingEventType(Enum):
    START = auto()
    STEP_OVER = auto()
    STEP_IN = auto()
    STEP_OUT = auto()
    STOP = auto()
    FINISH = auto()


class DebuggingEvent:
    def __init__(
            self, type_, line_no,
            globals_=None, locals_=None, call_stack=None):
        self.type = type_
        self.line_no = line_no
        self.globals_ = globals_
        self.locals_ = locals_


class BytecodeExecutor:
    _trace_func_name = 'trace'
    _stop_flag_name = 'stop'

    def __init__(self, source, filename, commands, events):
        self.debugging_commands = commands
        self.debugging_events = events

        self.source = source
        self.filename = filename

        self._stop_flag = False
        self._globals = {
            self._trace_func_name: self._trace,
            self._stop_flag_name: self._stop_flag,
            '__name__': '__main__'
        }

        self.debugging_variables = [
            self._trace_func_name,
            self._stop_flag_name
        ]

    def _trace(self):
        """
        Обрабатывает вызов из байткода
        """
        frame = sys._getframe(1)
        self._update(frame)

        command = self.debugging_commands.get()

        if command == 'stop':
            self._globals[self._stop_flag_name] = True
            self.debugging_events.put(
                DebuggingEvent(DebuggingEventType.STOP, line_no))

    def _update(self, frame):
        line_no = frame.f_lineno
        globals_ = self._prepare_variables(frame.f_globals)
        locals_ = self._prepare_variables(frame.f_locals)

        self.debugging_events.put(DebuggingEvent(
            DebuggingEventType.STEP_OVER,
            line_no,
            globals_,
            locals_))

    def execute(self):
        modified_code = self._compile_source()
        exec(modified_code, self._globals)
        self.debugging_events.put(
            DebuggingEvent(DebuggingEventType.FINISH, None))

    def _compile_source(self):
        initial_bytecode = compile(self.source, self.filename, 'exec')
        modified_code = modify(
            initial_bytecode,
            trace_func_name=self._trace_func_name,
            stop_flag_name=self._stop_flag_name)

        return modified_code

    def __call__(self):
        self.execute()

    def _prepare_variables(self, variables):
        """
        Подготавливает глобальные/локальные переменные

        Переводит все значения переменных в cтроковое представление
        Удаляет отладочные переменные
        Обрезаем слишком длинные строки

        :param variables: словарь с глобальными/локальными переменными
        :return новый подготовленный словарь
        """
        prepared = {}
        for k, v in variables.copy().items():
            if k in self.debugging_variables:
                continue

            if not isinstance(v, str):
                v = repr(v)

            if len(v) > 40:
                v = v[:40] + '...'

            prepared[k] = v

        return prepared
