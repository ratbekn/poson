from enum import Enum, auto


class DebuggerExit(Exception):
    pass


class DebuggerNotStarted(Exception):
    pass


class EmptySourceCode(Exception):
    pass


class DebugCommand(Enum):
    """
    Команды отладки
    """
    STEP_OVER = auto()
    STEP_IN = auto()
    STEP_OUT = auto()
