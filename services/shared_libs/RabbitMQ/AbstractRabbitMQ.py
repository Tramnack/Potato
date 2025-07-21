import time
from abc import ABC, abstractmethod

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError

from services.shared_libs.RabbitMQ.const import RMQ_HOST, RMQ_PORT
from services.shared_libs.logging_config import setup_logging


class RabbitMQConnectionError(Exception):
    """Custom exception for when RabbitMQ connection fails."""
    pass


class AbstractRabbitMQ(ABC):
    def __init__(self,
                 host: str = RMQ_HOST,
                 port: int = RMQ_PORT,
                 max_attempts: int = 5,
                 attempt_interval: float = 5.0):
        """
        :param host: The hostname or IP address of the RabbitMQ server.
        :param port: The port number on which the RabbitMQ server is listening.
        :param max_attempts: The maximum number of attempts to connect to the RabbitMQ server.
        :param attempt_interval: The interval in seconds between each attempt to connect to the RabbitMQ server.
        """
        if not isinstance(host, str):
            raise ValueError("host must be a string.")
        self._message_broker_host = host

        if not isinstance(port, int) or port <= 0:
            raise ValueError("port must be a positive integer.")
        self._message_broker_port = port

        if not isinstance(max_attempts, int) or max_attempts <= 0:
            raise ValueError("max_retries must be a positive integer.")
        self._max_attempts = max_attempts

        if not isinstance(attempt_interval, float | int) or attempt_interval <= 0:
            raise ValueError(f"attempt_interval must be a positive float, was {attempt_interval}.")
        self._attempt_interval = attempt_interval

        self.logger = setup_logging(service_name=self.__class__.__name__)
        self._connection: pika.BlockingConnection | None = None  # TCP connection
        self._channel: BlockingChannel | None = None  #

    def connect(self) -> bool:
        """
        Connects to the RabbitMQ server and returns success.

        :return: True if connection was successful, False otherwise.
        """

        host, port = self._message_broker_host, self._message_broker_port
        max_attempts = self._max_attempts
        interval = self._attempt_interval

        # Establish connection with RabbitMQ server
        self.logger.info(f"Attempting to connect to RabbitMQ at {host}:{port}")

        for attempt in range(max_attempts):
            try:
                self._connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
                self._channel = self._connection.channel()
                self.logger.info("Connected to RabbitMQ successfully")
                self.setup()
                return True  # Exit if connection is successful
            except AMQPConnectionError:
                self.logger.warning(
                    f"Failed to connect (attempt {attempt + 1}/{max_attempts}). Retrying in {interval}s...")
                time.sleep(interval)
        # If we reach here, it means all attempts failed
        self.logger.error(
            f"Failed to connect to RabbitMQ after {max_attempts} attempts. Tried for {max_attempts * interval} seconds.")
        return False

    def disconnect(self):
        """Closes the RabbitMQ connection."""
        self.logger.info("Closing RabbitMQ connection.")
        if self._connection and self._connection.is_open:
            self._connection.close()
            self.logger.debug("Connection closed.")
        else:
            self.logger.debug("Connection already closed.")

    def _ready(self) -> bool:
        return (self._connection and self._connection.is_open and
                self._channel and self._channel.is_open)

    def __del__(self):
        self.logger.debug("Deleting RabbitMQ instance.")
        self.disconnect()

    @abstractmethod
    def setup(self):
        """Subclasses should override this to declare queues, exchanges, etc. Called in ``__init__``."""
        pass
