from abc import ABC, abstractmethod

class Resource(ABC):
    @abstractmethod
    def deploy(self):
        pass

    @abstractmethod
    def teardown(self):
        pass

    @abstractmethod
    def serialize(self):
        pass