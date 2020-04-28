class BuildException(Exception):
    def __init__(self, msg, build_output):
        self.msg = msg
        self.build_output = build_output
