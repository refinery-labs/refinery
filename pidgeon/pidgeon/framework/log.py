from asyncio import InvalidStateError
from logging import getLogger, DEBUG as level, StreamHandler, Formatter
from sys import stdout
from traceback import extract_stack, format_list


handler = StreamHandler(stdout)
log = getLogger("pidgeon")


handler.setFormatter(Formatter('%(asctime)s [%(levelname)s] %(message)s'))
log.addHandler(handler)
log.setLevel(level)


def log_task_exception(task):
    formatted = ['Traceback (most recent call last):\n']

    for frame in task.get_stack():
        formatted.extend(format_list(extract_stack(frame)))

    try:
        formatted.append(str(task.exception()))
    except InvalidStateError:
        pass

    log.error("".join(formatted))
