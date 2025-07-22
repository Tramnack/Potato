from abc import ABC, abstractmethod
from typing import Optional

from pika.channel import Channel
from pika.exceptions import AMQPChannelError, AMQPConnectionError
from pika.spec import Basic, BasicProperties

from services.shared_libs.RabbitMQ import RMQ_HOST, RMQ_PORT
from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ


class RabbitMQConsumer(AbstractRabbitMQ, ABC):
    """
    Abstract base class for RabbitMQ Consumers.
    Subclasses must implement the `setup` and `callback` methods.
    """

    def __init__(self,
                 queue_name: str,
                 host: str = RMQ_HOST,
                 port: int = RMQ_PORT,
                 max_attempts: int = 5,
                 attempt_interval: float = 5):

        self._queue = None
        super().__init__(host, port, max_attempts, attempt_interval)
        self.queue = queue_name

    @property
    def queue(self) -> str:
        return self._queue

    @queue.setter
    def queue(self, queue_name: str):
        if not isinstance(queue_name, str):
            raise TypeError("queue_name must be a string.")
        elif not queue_name:
            raise ValueError("queue_name must not be empty.")
        if queue_name != self._queue:
            pass
            # TODO
        self._queue = queue_name

    def consume(self, auto_ack: bool = False, callback: Optional[callable] = None) -> None:
        """
        Starts consuming messages from the specified queue.

        :param auto_ack: If True, messages will be automatically acknowledged.
                         If False, the callback method must manually acknowledge.
        :param callback: An optional callback function to handle incoming messages.
                         If provided, it overrides the default callback method.
        :raises RuntimeError: If the RabbitMQConsumer is not connected.
        :raises AMQPChannelError: If a channel-related error occurs during consumption.
        :raises AMQPConnectionError: If a connection-related error occurs during consumption.
        """
        if not self._ready():
            msg = "RabbitMQProducer is not connected."
            self.logger.error(msg)
            raise RuntimeError(msg + " Call connect() first.")

        try:
            # Ensure queue is declared and QoS is set before consuming
            # This is now handled in the setup() method which is called during connect()
            # However, for robustness, we can ensure it here if consume is called directly
            # without a prior setup call that declared this specific queue.
            # For this implementation, we assume setup() handles all necessary declarations.

            callback = callback or self.callback  # Use default callback if not provided

            self._channel.basic_consume(queue=self._queue, on_message_callback=callback, auto_ack=auto_ack)
            self.logger.info(f"Consuming messages from queue '{self._queue}'...")
            self._channel.start_consuming()
        except AMQPChannelError as e:
            self.logger.error(f"AMQP Channel Error during consume: {e}")
            raise e
        except AMQPConnectionError as e:
            self.logger.error(f"AMQP Connection Error during consume: {e}")
            raise e
        except Exception as e:
            self.logger.critical(f"An unexpected error occurred during consume: {e}")
            raise e

    @abstractmethod
    def callback(self, ch: Channel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
        """
        Subclasses should override this method to handle incoming messages.
        This method is called by the Pika library when a message is received.

        :param ch: The channel object.
        :param method: The delivery method frame.
        :param properties: The message properties.
        :param body: The message body (bytes).
        """
        pass

