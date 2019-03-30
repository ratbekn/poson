"""Модифицирует байткод"""

import types

from bytecode import Bytecode, Instr, Label, Compare


def _get_import_sys_instructions(line_no):
    return [
        Instr('LOAD_CONST', arg=0, lineno=line_no),
        Instr('LOAD_CONST', arg=None, lineno=line_no),
        Instr('IMPORT_NAME', arg='sys', lineno=line_no),
        Instr('STORE_NAME', arg='sys', lineno=line_no)
    ]


class BytecodeModifier:
    def __init__(self, trace_func, command):
        self._trace_func = trace_func
        self._command = command

    def modify(self, code, *, inner=False):
        initial_bytecode = Bytecode.from_code(code)

        modified_bytecode = Bytecode()
        modified_bytecode.argcount = code.co_argcount
        modified_bytecode.freevars = code.co_freevars
        modified_bytecode.cellvars = code.co_cellvars

        # добавляем инструкции отладки перед первой строкой
        if not inner:
            line_no = initial_bytecode.first_lineno
            modified_bytecode.extend(
                    _get_import_sys_instructions(line_no)
                    + self._get_trace_func_call_instructions(line_no))

        previous_line_no = initial_bytecode.first_lineno
        for instr in initial_bytecode:
            if not isinstance(instr, Instr):
                modified_bytecode.append(instr)
                continue

            if isinstance(instr.arg, types.CodeType):
                old_instr_name = instr.name
                new_co = self.modify(instr.arg, inner=True)
                instr.set(old_instr_name, new_co)

            if instr.lineno != previous_line_no:
                modified_bytecode.extend(
                    self._get_trace_func_call_instructions(instr.lineno))

                previous_line_no = instr.lineno

            modified_bytecode.append(instr)

        code = modified_bytecode.to_code()

        return code

    def _get_trace_func_call_instructions(self, line_no):
        return [
            Instr('LOAD_GLOBAL', arg=self._trace_func, lineno=line_no),
            Instr('CALL_FUNCTION', arg=0, lineno=line_no),
            Instr('POP_TOP', lineno=line_no)
        ]

    def _get_stop_instractions(self, place_for_continue, line_no):
        return [
            Instr('LOAD_NAME', arg=self._command, lineno=line_no),
            Instr('LOAD_CONST', arg='stop', lineno=line_no),
            Instr('COMPARE_OP', arg=Compare.EQ, lineno=line_no),
            Instr(
                'POP_JUMP_IF_FALSE', arg=place_for_continue, lineno=line_no),
            Instr('LOAD_NAME', arg='sys', lineno=line_no),
            Instr('LOAD_ATTR', arg='exit', lineno=line_no),
            Instr('CALL_FUNCTION', arg=0, lineno=line_no),
            Instr('POP_TOP', lineno=line_no),
            place_for_continue
        ]
