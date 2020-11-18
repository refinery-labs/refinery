from abc import ABC, abstractmethod

class Resource(ABC):
    @abstractmethod
    def deploy(self):
        pass

    @abstractmethod
    def teardown(self):
        pass

    @property
    @abstractmethod
    def uid(self):
        pass
