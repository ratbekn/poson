import os
import sys

import pytest

sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.path.pardir))

from app.debugger_client import DebuggerClient
from app.debugging.debugger import Debugger
from app.debugging.common import DebugCommand


@pytest.fixture()
def client():
    return DebuggerClient()


@pytest.fixture()
def debugger_patched_start(monkeypatch):
    def patched_start(self, source, filename, breakpoints):
        patched_start.is_called = True

    monkeypatch.setattr(Debugger, 'start', patched_start)

    yield patched_start


@pytest.fixture()
def debugger_patched_send_command(monkeypatch):
    def patched_send_command(self, command):
        patched_send_command.command = command
        patched_send_command.is_called = True

    monkeypatch.setattr(Debugger, 'send_command', patched_send_command)

    yield patched_send_command


@pytest.fixture()
def debugger_patched_finish(monkeypatch):
    def patched_command(self):
        patched_command.is_called = True

    monkeypatch.setattr(Debugger, 'finish', patched_command)

    yield patched_command


def test_start_called(debugger_patched_start, client):
    client.start('1 + 1', '<string>', [])

    assert debugger_patched_start.is_called


def test_step_over_called(debugger_patched_send_command, client):
    client.step_over()

    assert debugger_patched_send_command.is_called
    assert debugger_patched_send_command.command == DebugCommand.STEP_OVER


def test_step_in_called(debugger_patched_send_command, client):
    client.step_in()

    assert debugger_patched_send_command.is_called
    assert debugger_patched_send_command.command == DebugCommand.STEP_IN


def test_step_out_called(debugger_patched_send_command, client):
    client.step_out()

    assert debugger_patched_send_command.is_called
    assert debugger_patched_send_command.command == DebugCommand.STEP_OUT
