import os
import sys
import threading
from queue import Queue

import pytest

sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.path.pardir,
    os.path.pardir))

from app.debugging.debugger import Debugger
from app.debugging.bytecode_modifier import BytecodeModifier
from app.debugging.common import EmptySourceCode, DebugCommand, DebuggerExit


@pytest.fixture()
def patched_thread_start(monkeypatch):
    def start_patch(self):
        start_patch.is_called = True

    monkeypatch.setattr(threading.Thread, 'start', start_patch)

    yield start_patch


@pytest.fixture()
def debugger():
    return Debugger()


class TestDebuggerStart:
    def test_throw_emptysourceexception_if_source_is_empty(
            self, patched_thread_start, debugger):
        with pytest.raises(EmptySourceCode):
            debugger.start('', '<string>')

    def test_new_empty_commands_if_commands_is_not_empty(
            self, patched_thread_start, debugger, sample_source):
        not_empty_commands = Queue()
        not_empty_commands.put(DebugCommand.STEP_OVER)
        not_empty_commands.put(DebugCommand.STEP_OVER)
        debugger._commands = not_empty_commands

        debugger.start(sample_source, '<string>')

        assert debugger._commands.empty()

    def test_new_empty_snapshot_if_snapshot_is_not_empty(
            self, patched_thread_start, debugger, sample_source):
        not_empty_snapshots = Queue()
        not_empty_snapshots.put(debugger._globals_)
        not_empty_snapshots.put(debugger._globals_)
        debugger._snapshots = not_empty_snapshots

        debugger.start(sample_source, '<string>')

        assert debugger._snapshots.empty()

    def test_thread_start_called(
            self, patched_thread_start, debugger, sample_source):
        debugger.start(sample_source, '<string>')

        assert patched_thread_start.is_called


def test_send_command(debugger):
    assert debugger._commands.empty()
    debugger.send_command(DebugCommand.STEP_OVER)
    assert debugger._commands.qsize() == 1


def test_get_snapshot_works(debugger):
    debugger._snapshots.put({'test': 'dict'})
    snapshot = debugger.get_snapshot()

    assert snapshot == {'test': 'dict'}


def test_get_snapshot_raise_debuggerexitexception(debugger):
    debugger._snapshots.put(DebuggerExit)
    with pytest.raises(DebuggerExit):
        debugger.get_snapshot()


def test_finish(debugger, sample_source):
    debugger.start(sample_source, '<string>')

    debugger.finish()
    debugger.join()

    assert debugger._finished.is_set()


@pytest.fixture()
def patch_modify(monkeypatch):
    def patched_modify(source, filename):
        patched_modify.is_called = True

    monkeypatch.setattr(BytecodeModifier, 'modify', patched_modify)

    yield patched_modify


def test_compile_call_bytecodemodifier_modify(
        debugger, patch_modify, sample_source):
    debugger._compile(sample_source, '<string>')

    assert patch_modify.is_called


def test_compile_raise_exception_if_invalid_source(debugger):
    with pytest.raises(ValueError):
        debugger._compile(b'\x00', '<string>')

    with pytest.raises(SyntaxError):
        debugger._compile(
            '''if False:
                pass
               else if:
                pass''', '<string>')


@pytest.fixture()
def patch_run(monkeypatch):
    def patched_run(self, code):
        patched_run.is_called = True
    monkeypatch.setattr(Debugger, '_run', patched_run)

    yield patched_run


def test_bootstrap_call_run(patch_run, debugger, sample_code):
    debugger._bootstrap(sample_code)

    assert patch_run.is_called


def test_bootstrap_put_debugexit(patch_run, debugger, sample_code):
    debugger._bootstrap(sample_code)

    assert debugger._snapshots.get() is DebuggerExit


def test_bootstrap_set_finished(patch_run, debugger, sample_code):
    debugger._bootstrap(sample_code)

    assert debugger._finished.is_set()


def test_sanitize_contain_only_str(debugger, sample_code):
    d = {
        'int': 42,
        'tuple': (42, 73),
        'code': sample_code,
        'dict': {'int': 42}
    }

    for v in debugger._sanitize(d).values():
        assert isinstance(v, str)
