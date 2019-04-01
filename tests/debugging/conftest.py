import os
import sys

import pytest

sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.path.pardir,
    os.path.pardir))
from app.debugging.bytecode_modifier import BytecodeModifier


@pytest.fixture()
def command():
    cmd = 'command'

    return cmd


@pytest.fixture()
def trace_func():
    trace = 'trace'

    return trace


@pytest.fixture()
def bytecode_modifier(trace_func, command):
    modifier = BytecodeModifier(trace_func, command)

    return modifier


@pytest.fixture()
def sample_source():
    source = '''def gcd(m, n):
            while True:
                if m == n:
                    return m
                if m > n:
                    m -= n
                else:
                    n -= m'''

    return source


@pytest.fixture()
def sample_code(sample_source):
    sample = compile(sample_source, '<string>', 'exec')

    return sample
