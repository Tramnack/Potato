from abc import abstractmethod, ABC


class Template(ABC):
    @abstractmethod
    def run(self):
        pass
