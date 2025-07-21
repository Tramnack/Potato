import time
from abc import ABC, abstractmethod

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError

from services.shared_libs.RabbitMQ.const import RMQ_HOST, RMQ_PORT
from services.shared_libs.logging_config import setup_logging


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

        self._channel = self._connect()
        self.setup()

    def _connect(self) -> BlockingChannel:
        """
        Connects to the RabbitMQ server and returns a channel.

        :return: The channel to the RabbitMQ server.
        """

        host, port = self._message_broker_host, self._message_broker_port
        max_attempts = self._max_attempts
        interval = self._attempt_interval

        # Establish connection with RabbitMQ server
        self.logger.info(f"Attempting to connect to RabbitMQ at {host}:{port}")
        for attempt_nr in range(max_attempts):
            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
                self.logger.info("Connected to RabbitMQ successfully")
                break  # Exit loop if connection is successful
            except AMQPConnectionError:
                self.logger.warning(f"Failed to connect to RabbitMQ. Retrying in {interval} seconds...")
                time.sleep(interval)
        else:
            self.logger.error(f"Failed to connect to RabbitMQ after {max_attempts} attempts."
                              f"Tried for {max_attempts * interval} seconds.")
            raise Exception(f"Failed to connect to RabbitMQ after {max_attempts} attempts.")
        return connection.channel()

    @property
    def channel(self) -> BlockingChannel:
        return self._channel

    def __del__(self):
        if self._channel.is_closed:
            self.logger.debug("Channel already closed.")
        else:
            self._channel.close()
        self.logger.info("Channel closed.")

    @abstractmethod
    def setup(self):
        """Subclasses should override this to declare queues, exchanges, etc."""
        pass
