from functools import cached_property
from hashlib import sha256
from json import dumps


class LambdaConfig:
    def __init__(self, name, runtime, code, libraries, env, shared_files, role, memory, handler, is_inline_execution, max_execution_time, tags, layers):
        self.name = name
        self.runtime = runtime
        self.code = code
        self.libraries = libraries
        self.env = env
        self.shared_files = shared_files
        self.role = role
        self.handler = handler
        self.is_inline_execution = is_inline_execution
        self.max_execution_time = int(max_execution_time)
        self.memory = int(memory)
        self.tags = tags
        self.layers = layers
        self.description = "A Lambda deployed by refinery"

    @cached_property
    def uid(self):
        attrs = [
            self.name,
            self.runtime,
            self.code,
            dumps(self.libraries, sort_keys=True),
            dumps(self.env, sort_keys=True),
            dumps(self.shared_files, sort_keys=True),
            self.role,
            self.handler,
            self.is_inline_execution,
            self.max_execution_time,
            self.memory,
            self.tags,
            self.layers,
            self.description
        ]
        template = '{}' * len(attrs)
        return sha256(template.formate(attrs).encode("UTF-8")).hexdigest()
