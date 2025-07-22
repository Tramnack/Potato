from abc import ABC, abstractmethod
from typing import Optional

from pika.channel import Channel
from pika.exceptions import AMQPChannelError, AMQPConnectionError
from pika.spec import Basic, BasicProperties

from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ
from services.shared_libs.RabbitMQ.const import RMQ_HOST, RMQ_PORT


class RabbitMQConsumer(AbstractRabbitMQ, ABC):
    """
    Abstract base class for RabbitMQ Consumers.
    Subclasses must implement the `_setup` and `callback` methods.
    """

    def __init__(self,
                 queue_name: str,
                 host: str = RMQ_HOST,
                 port: int = RMQ_PORT,
                 connection_attempts: int = 5,
                 retry_delay: float = 5):

        self._queue = queue_name
        self._consuming = False
        self._consumer_tag = None

        super().__init__(host, port, connection_attempts, retry_delay)

    @property
    def queue(self) -> str:
        return self._queue

    @queue.setter
    def queue(self, value: str):
        """
        Set the queue name.
        """
        if not isinstance(value, str):
            raise TypeError("queue_name must be a string.")
        elif not value:
            raise ValueError("queue_name must not be empty.")
        if value != self._queue and self._consumer_tag and self._consuming:
            self.stop_consuming()
        self._queue = value
        self.logger.info(f"Queue name set to: {self._queue}")

    def consume(self, auto_ack: bool = False, callback: Optional[callable] = None,
                restart_if_running: bool = True) -> None:
        """
        Starts consuming messages from the specified queue.

        :param auto_ack: If True, messages will be automatically acknowledged.
                         If False, the callback method must manually acknowledge.
        :param callback: An optional callback function to handle incoming messages.
                         If provided, it overrides the default callback method.
        :param restart_if_running: If True, the consumer will be restarted if it's already consuming messages.
        :raises RuntimeError: If the RabbitMQConsumer is not connected.
        :raises AMQPChannelError: If a channel-related error occurs during consumption.
        :raises AMQPConnectionError: If a connection-related error occurs during consumption.
        """
        if not self._ready():
            msg = "RabbitMQProducer is not connected."
            self.logger.error(msg)
            raise RuntimeError(msg + " Call connect() first.")

        if self._consuming and not restart_if_running:
            self.logger.info("Consumer is already consuming messages from the queue.")
            return
        elif self._consuming and restart_if_running:
            self.logger.info("Consumer is already consuming messages from the queue. Restarting...")
            self.stop_consuming()

        if (not callable(callback) or not hasattr(callback, '__call__')) and callback is not None:
            raise TypeError("callback must be a callable object or None.")
        callback = callback or self._callback  # Use default callback if not provided

        try:

            # Start a new consumer
            self._consumer_tag = self._channel.basic_consume(
                queue=self._queue,
                on_message_callback=callback,
                auto_ack=auto_ack
            )
            self._consuming = True
            self.logger.info(f"Consuming messages from queue '{self._queue}'")
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

    def stop_consuming(self) -> None:
        """
        Stop consuming messages from the current queue.
        This will cancel the active consumer if one exists.
        """
        if self._consumer_tag and self._ready():
            try:
                un_acknowledged = self._channel.basic_cancel(self._consumer_tag)
                self.logger.info(f"Stopped consuming messages from queue '{self._queue}'")
                if un_acknowledged:
                    self._handle_unacknowledged_messages(un_acknowledged)
            except Exception as e:
                self.logger.error(f"Error stopping consumer: {e}")
                raise e
            finally:
                self._consuming = False
                self._consumer_tag = None

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point - ensures resources are cleaned up."""
        self.stop_consuming()
        self.disconnect()

    @abstractmethod
    def _callback(self, ch: Channel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
        """
        Subclasses should override this method to handle incoming messages.
        This method is called by the Pika library when a message is received.

        :param ch: The channel object.
        :param method: The delivery method frame.
        :param properties: The message properties.
        :param body: The message body (bytes).
        """
        pass

    @abstractmethod
    def _handle_unacknowledged_messages(self,
                                        un_acknowledged: list[tuple[Channel, Basic.Deliver, BasicProperties, bytes]]
                                        ) -> None:
        """
        Subclasses should override this method to handle unacknowledged messages after stopping consumption.

        :param un_acknowledged: A list of unacknowledged messages.
        """
        pass
