from abc import ABC, abstractmethod

class Builder(ABC):
    @abstractmethod
    def build(self):
        pass

class Dismantler(ABC):
    @abstractmethod
    def dismantle(self):
        pass