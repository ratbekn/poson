"""Модифицирует байткод"""

import types

from bytecode import Bytecode, Instr, Label

_IMPORT_SYS_MODULE = [
    Instr('LOAD_CONST', arg=0, lineno=1),
    Instr('LOAD_CONST', arg=None, lineno=1),
    Instr('IMPORT_NAME', arg='sys', lineno=1),
    Instr('STORE_NAME', arg='sys', lineno=1)
]


def modify(code, *, trace_func_name, stop_flag_name):
    """
    Модифицирует байткод

    Модифицирует code object вставляя вызов функций trace_func_name
    после каждой строки выполнения
    """

    # todo: добавить вызов trace функций перед первой строкой

    initial_bytecode = Bytecode.from_code(code)

    initial_bytecode[0:0] = _IMPORT_SYS_MODULE

    modified_bytecode = Bytecode()
    modified_bytecode.argcount = code.co_argcount
    modified_bytecode.freevars = code.co_freevars
    modified_bytecode.cellvars = code.co_cellvars

    previous_line_no = initial_bytecode.first_lineno
    for instr in initial_bytecode:
        if not isinstance(instr, Instr):
            modified_bytecode.append(instr)
            continue

        if isinstance(instr.arg, types.CodeType):
            old_instr_name = instr.name
            new_co = modify(
                instr.arg,
                trace_func_name=trace_func_name,
                stop_flag_name=stop_flag_name)
            instr.set(old_instr_name, new_co)

        if instr.lineno != previous_line_no or instr.lineno == 0:
            keep_running = Label()

            # инструкции вызова sys.exit(), если выставлен флаг остановки
            modified_bytecode.extend([
                Instr('LOAD_NAME', arg=stop_flag_name, lineno=instr.lineno),
                Instr('POP_JUMP_IF_FALSE', arg=keep_running,
                      lineno=instr.lineno),
                Instr('LOAD_NAME', arg='sys', lineno=instr.lineno),
                Instr('LOAD_ATTR', arg='exit', lineno=instr.lineno),
                Instr('CALL_FUNCTION', arg=0, lineno=instr.lineno),
                Instr('POP_TOP', lineno=instr.lineno),
                keep_running
            ])

            # инструкции вызова trace функции отладчика
            modified_bytecode.extend([
                Instr('LOAD_GLOBAL', arg=trace_func_name, lineno=instr.lineno),
                Instr('CALL_FUNCTION', arg=0, lineno=instr.lineno),
                Instr('POP_TOP', lineno=instr.lineno)
            ])

            previous_line_no = instr.lineno

        modified_bytecode.append(instr)

    code = modified_bytecode.to_code()

    return code
