from abc import ABC
from typing import Optional

from pika.spec import BasicProperties

from services.shared_libs.StatefulMixin import StatefulMixin


class RabbitMQStatefulMixin(StatefulMixin, ABC):
    """
    A mixin for RabbitMQ consumers that need to manage external state.
    Provides utility methods for extracting session IDs from RabbitMQ message properties.
    Relies on the abstract methods from StatefulMixin for actual state storage/retrieval.
    """

    def _get_session_id_from_properties(self, properties: BasicProperties) -> Optional[str]:
        """
        Utility method to extract the session ID from RabbitMQ message properties.

        Assumes the session ID is stored in ``properties.headers['session_id']``.
        This method can be overridden if the session ID is stored differently
        (e.g., in the message body, or a different header).

        :param properties: The Pika BasicProperties object from the incoming message.
        :return: The session ID as a string.
        :raises TypeError: If the 'properties' argument is not a Pika BasicProperties object.
        """

        if not isinstance(properties, BasicProperties):
            msg = "Expected Pika BasicProperties object."
            self.logger.error(msg)
            raise TypeError(msg)
        elif not properties.headers:
            self.logger.warning("Message properties missing headers for stateful processing.")
            return None

        if 'session_id' not in properties.headers:
            self.logger.warning("Message properties missing 'session_id' header for stateful processing.")
            return None
        session_id = properties.headers['session_id']
        if not session_id:
            self.logger.warning("Message properties 'session_id' header is empty.")
            return None
        return str(session_id)
