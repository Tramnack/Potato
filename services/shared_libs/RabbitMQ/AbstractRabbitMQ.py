import os
import time
from abc import ABC, abstractmethod

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, ChannelClosed

#TODO: Replace print with logger

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))  # Also good to make port dynamic


class AbstractRabbitMQ(ABC):
    def __init__(self, host: str = RABBITMQ_HOST, port: int = RABBITMQ_PORT, max_attempts: int = 5,
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

        if not isinstance(attempt_interval, float) or attempt_interval <= 0:
            raise ValueError("attempt_interval must be a positive float.")
        self._attempt_interval = attempt_interval

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
        print(f"Attempting to connect to RabbitMQ at {host}:{port}")
        for attempt_nr in range(max_attempts):
            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
                print("Connected to RabbitMQ!")
                break  # Exit loop if connection is successful
            except AMQPConnectionError:
                print(f"Failed to connect to RabbitMQ. Retrying in {interval} seconds...")
                time.sleep(interval)
        else:
            raise Exception(
                f"Failed to connect to RabbitMQ after {interval} attempts. Tried for {max_attempts * interval} seconds.")
        return connection.channel()

    @property
    def channel(self) -> BlockingChannel:
        return self._channel

    def __del__(self):
        if self._channel.is_closed:
            print("Channel already closed.")
            return
        self._channel.close()
        print("Channel closed.")

    @abstractmethod
    def setup(self):
        """Subclasses should override this to declare queues, exchanges, etc."""
        pass
