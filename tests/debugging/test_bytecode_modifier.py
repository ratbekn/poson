import os
import sys
from collections import defaultdict
from types import CodeType

import pytest
from bytecode import Bytecode, Compare, Instr

sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.path.pardir,
    os.path.pardir))

from app.debugging.bytecode_modifier import BytecodeModifier
from app.debugging import DebugCommand


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


def test_bytecode_modifier_created_correctly():
    trace_name = 'trace'
    command_name = 'command'

    modifier = BytecodeModifier(trace_name, command_name)

    assert modifier._trace_func == trace_name
    assert modifier._command == command_name


def test_get_trace_func_call_instructions(bytecode_modifier, trace_func):
    line_no = 42
    expected = [
        Instr('LOAD_GLOBAL', arg=trace_func, lineno=line_no),
        Instr('CALL_FUNCTION', arg=0, lineno=line_no),
        Instr('POP_TOP', lineno=line_no)
    ]

    assert (bytecode_modifier._get_trace_func_call_instructions(line_no)
            == expected)


@pytest.fixture()
def sample_code():
    source = '''def gcd(m, n):
        while True:
            if m == n:
                return m
            if m > n:
                m -= n
            else:
                n -= m'''
    sample = compile(source, '<string>', 'exec')

    return sample


def test_modified_code_has_saved_properties(bytecode_modifier, sample_code):
    modified = bytecode_modifier.modify(sample_code)

    assert modified.co_argcount == sample_code.co_argcount
    assert modified.co_varnames == sample_code.co_varnames
    assert modified.co_cellvars == sample_code.co_cellvars
    assert modified.co_filename == sample_code.co_filename
    assert modified.co_firstlineno == sample_code.co_firstlineno
    assert modified.co_freevars == sample_code.co_freevars
    assert modified.co_name == sample_code.co_name


def group_instructions_by_line(code, *, skip=0):
    bc = Bytecode.from_code(code)
    groups = defaultdict(list)
    for instr in bc[skip:]:
        if isinstance(instr, CodeType):
            groups[instr.lineno].append(instr)

    return groups


def get_first_inner_code_obj(code):
    for const in code.co_consts:
        if isinstance(const, CodeType):
            return const

    return None


def test_every_line_has_trace_func_call(bytecode_modifier, sample_code):
    modified = bytecode_modifier.modify(sample_code)

    groups = group_instructions_by_line(modified)

    for line_instructions in groups.values():
        assert line_instructions[0].name == 'LOAD_GLOBAL'
        assert line_instructions[0].arg == bytecode_modifier._trace_func

        assert line_instructions[1].name == 'CALL_FUNCTION'
        assert line_instructions[1].arg == 0

        assert line_instructions[2].name == 'POP_TOP'


@pytest.fixture()
def sample_inner():
    sample = compile(
        '''def f():
            a = 42
            b = 73
            return a + b''', '<string>', 'exec')

    sample_inner = get_first_inner_code_obj(sample)
    assert sample_inner is not None

    return sample_inner


def test_every_inner_setup_is_over_variable(bytecode_modifier, sample_inner):
    modified = bytecode_modifier.modify(sample_inner, inner=True)
    bc = Bytecode.from_code(modified)
    is_over_setup_instructions = bc[:4]

    assert is_over_setup_instructions[0].name == 'LOAD_NAME'
    assert is_over_setup_instructions[0].arg == bytecode_modifier._command

    assert is_over_setup_instructions[1].name == 'LOAD_CONST'
    assert is_over_setup_instructions[1].arg == DebugCommand.STEP_OVER

    assert is_over_setup_instructions[2].name == 'COMPARE_OP'
    assert is_over_setup_instructions[2].arg == Compare.EQ

    assert is_over_setup_instructions[3].name == 'STORE_NAME'
    assert is_over_setup_instructions[3].arg == 'is_over'


def test_every_inner_check_is_over(bytecode_modifier, sample_inner):
    modified = bytecode_modifier.modify(sample_inner, inner=True)
    groups = group_instructions_by_line(modified, skip=4)

    for line_instructions in groups.values():
        assert line_instructions[0].name == 'LOAD_NAME'
        assert line_instructions[0].arg == 'is_over'

        assert line_instructions[1].name == 'POP_JUMP_IF_TRUE'


def test_every_inner_check_step_out(bytecode_modifier, sample_inner):
    modified = bytecode_modifier.modify(sample_inner, inner=True)
    groups = group_instructions_by_line(modified, skip=6)

    for line_instructions in groups.values():
        assert line_instructions[0].name == 'LOAD_NAME'
        assert line_instructions[0].arg == bytecode_modifier._trace_func

        assert line_instructions[1].name == 'LOAD_CONST'
        assert line_instructions[1].arg == DebugCommand.STEP_OUT

        assert line_instructions[2].name == 'COMPARE_OP'
        assert line_instructions[2].arg == Compare.EQ

        assert line_instructions[3].name == 'POP_JUMP_IF_TRUE'
