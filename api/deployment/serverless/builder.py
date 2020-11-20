from deployment.base import Builder


class ServerlessBuilder(Builder):
    def __init__(self, project_config):
        self.project_config = project_config

        self.validate()

    def validate(self):
        pass

    def build(self):
        pass
    
    def teardown(self):
        pass