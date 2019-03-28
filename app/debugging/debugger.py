from multiprocessing import Process, Queue, set_start_method

from .bytecodeexecutor import BytecodeExecutor


class Debugger:
    def __init__(self, *, debugging_events):
        self._engine = Process(daemon=True)
        self._commands = Queue()
        self.debugging_events = debugging_events

    def debug(self, source, filename='<string>'):
        if not isinstance(source, str):
            raise TypeError(f'source should be string, not {type(source)}')

        if self._engine.is_alive():
            return

        if self._commands:
            self._commands = Queue()

        executor = BytecodeExecutor(
            source, filename, self._commands, self.debugging_events)

        self._engine = Process(target=executor, daemon=True)
        self._engine.start()

    def step_over(self):
        if self._engine.is_alive():
            self._commands.put('step over')

    def step_in(self):
        pass

    def step_out(self):
        pass

    def stop(self):
        if self._engine.is_alive():
            self._commands.put('stop')
