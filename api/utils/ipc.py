from subprocess import Popen, PIPE


def popen_communicate(cmd, cwd=None):
    process_handler = Popen(
        cmd,
        stdout=PIPE,
        stderr=PIPE,
        shell=False,
        universal_newlines=True,
        cwd=cwd,
    )

    # Returns tuple (stdout, stderr)
    return process_handler.communicate()
