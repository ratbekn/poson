"""Модифицирует байткод"""

from types import CodeType
from typing import List

from bytecode import Bytecode, Instr, Label, Compare

from .common import DebugCommand


class BytecodeModifier:
    def __init__(self, trace_func, command):
        self._trace_func = trace_func
        self._command = command

    def modify(
            self, code: CodeType,
            breakpoints: List[int] = None,
            *, inner=False, to_modify=False) -> CodeType:
        initial_bytecode = Bytecode.from_code(code)

        modified_bytecode = Bytecode()
        modified_bytecode.first_lineno = initial_bytecode.first_lineno
        modified_bytecode.argcount = code.co_argcount
        modified_bytecode.argnames = initial_bytecode.argnames
        modified_bytecode.name = initial_bytecode.name
        modified_bytecode.freevars = code.co_freevars
        modified_bytecode.cellvars = code.co_cellvars

        first_breakpoint = min(breakpoints) if breakpoints else 1

        first_line_no = initial_bytecode.first_lineno

        if inner:
            modified_bytecode.extend([
                Instr('LOAD_NAME', arg=self._command, lineno=first_line_no),
                Instr(
                    'LOAD_CONST',
                    arg=DebugCommand.STEP_OVER, lineno=first_line_no),
                Instr('COMPARE_OP', arg=Compare.EQ, lineno=first_line_no),
                Instr('STORE_NAME', arg='is_over', lineno=first_line_no),
            ])

        # добавляем инструкции отладки перед первой строкой модуля
        if not inner and first_breakpoint == 1:
            modified_bytecode.extend(
                self._get_trace_func_call_instructions(first_line_no))

        previous_line_no = first_line_no
        for instr in initial_bytecode:
            if not isinstance(instr, Instr):
                modified_bytecode.append(instr)
                continue

            if not to_modify:
                to_modify = instr.lineno == first_breakpoint

            if isinstance(instr.arg, CodeType):
                old_instr_name = instr.name
                bc = Bytecode.from_code(instr.arg)
                last_lineno = bc.first_lineno + len(bc) - 1
                to_modify_inner = not (
                        bc.first_lineno <= first_breakpoint <= last_lineno)
                new_co = self.modify(
                    instr.arg, breakpoints,
                    inner=True, to_modify=to_modify_inner)
                instr.set(old_instr_name, new_co)

            skip = Label()
            if to_modify and instr.lineno != previous_line_no:
                if inner:
                    modified_bytecode.extend([
                        Instr(
                            'LOAD_NAME', arg='is_over', lineno=instr.lineno),
                        Instr(
                            'POP_JUMP_IF_TRUE', arg=skip, lineno=instr.lineno)
                    ])
                    modified_bytecode.extend([
                        Instr(
                            'LOAD_NAME',
                            arg=self._command, lineno=instr.lineno),
                        Instr(
                            'LOAD_CONST',
                            arg=DebugCommand.STEP_OUT, lineno=instr.lineno),
                        Instr(
                            'COMPARE_OP', arg=Compare.EQ, lineno=instr.lineno),
                        Instr(
                            'POP_JUMP_IF_TRUE', arg=skip, lineno=instr.lineno)
                    ])

                modified_bytecode.extend(
                    self._get_trace_func_call_instructions(instr.lineno))

                if inner:
                    modified_bytecode.append(skip)

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
