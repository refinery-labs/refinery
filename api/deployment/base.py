from abc import ABC, abstractmethod

class Builder(ABC):
    @abstractmethod
    def build(self):
        pass
