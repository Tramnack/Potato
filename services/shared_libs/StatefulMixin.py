from abc import ABC, abstractmethod

from services.shared_libs.logging_config import setup_logging


class StatefulMixin(ABC):
    """
    A generic mixin for classes that need to manage external state.
    Requires concrete implementation of state retrieval and update methods.
    """

    def __init__(self):
        self.logger = setup_logging(service_name=self.__class__.__name__)

    @abstractmethod
    def _retrieve_state(self, key: str) -> dict:
        """
        Abstract method to retrieve state associated with a given key.
        Must be implemented by the concrete class.

        :param key: The unique identifier for the state (e.g., session ID, user ID).
        :return: A dictionary representing the current state.
        """
        pass

    @abstractmethod
    def _update_state(self, key: str, state: dict) -> None:
        """
        Abstract method to update state associated with a given key.
        Must be implemented by the concrete class.

        :param key: The unique identifier for the state.
        :param state: The dictionary representing the updated state.
        """
        pass
