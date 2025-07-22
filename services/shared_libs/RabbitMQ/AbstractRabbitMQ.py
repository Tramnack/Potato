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
                 connection_attempts: int = 5,
                 retry_delay: float = 5):
        """
        :param host: The hostname or IP address of the RabbitMQ server.
        :param port: The port number on which the RabbitMQ server is listening.
        :param connection_attempts: The maximum number of attempts to connect to the RabbitMQ server.
        :param retry_delay: The interval in seconds between each attempt to connect to the RabbitMQ server.
        """
        if not isinstance(host, str):
            raise TypeError("host must be a string.")
        if not host or host.isspace():
            raise ValueError("host must not be empty.")

        if not isinstance(port, int):
            raise TypeError("port must be a positive integer.")
        elif port <= 0:
            raise ValueError("port must be a positive integer.")

        if not isinstance(connection_attempts, int):
            raise TypeError("max_retries must be a positive integer.")
        elif connection_attempts <= 0:
            raise ValueError("max_retries must be a positive integer.")

        if not isinstance(retry_delay, float | int):
            raise TypeError(f"retry_delay must be a positive float.")
        elif retry_delay <= 0:
            raise ValueError("retry_delay must be a positive float.")

        self.logger = setup_logging(service_name=self.__class__.__name__)
        self._connection: pika.BlockingConnection | None = None  # TCP connection
        self._channel: BlockingChannel | None = None  #

        self._message_broker_host = host
        self._message_broker_port = port
        self._connection_parameters = pika.ConnectionParameters(
            host=host,  # hostname or ip address of broker.
            port=port,  # port number of broker’s listening socket.
            # virtual_host,                  # rabbitmq virtual host name.
            # credentials,                   # one of the classes from pika.credentials.VALID_TYPES.
            # channel_max,                   # max preferred number of channels
            # frame_max,                     # desired maximum AMQP frame size to use.
            # heartbeat,                     # AMQP connection heartbeat timeout value for negotiation during connection
            #                                # tuning or callable which is invoked during connection tuning. None to
            #                                # accept broker’s value. 0 turns heartbeat off.
            # ssl_options,                   # None for plaintext or pika.SSLOptions instance for SSL/TLS.
            connection_attempts=connection_attempts,  # number of socket connection attempts.
            retry_delay=retry_delay,  # interval between socket connection attempts; see also
            #                                    # connection_attempts.
            # socket_timeout,                # socket connect timeout in seconds. The value None disables this timeout.
            # stack_timeout,                 # full protocol stack TCP/[SSL]/AMQP bring-up timeout in seconds. The value
            #                                # None disables this timeout.
            # locale,                        # locale value to pass to broker; e.g., ‘en_US’
            # blocked_connection_timeout,    # blocked connection timeout
            # client_properties,             # client properties used to override the fields in the default client
            #                                # properties reported to RabbitMQ via Connection.StartOk method.
            # tcp_options,                   # None or a dict of options to pass to the underlying socket
            # **kwargs,
        )

    def connect(self) -> bool:
        """
        Connects to the RabbitMQ server and returns success.

        :return: True if connection was successful, False otherwise.
        """

        # Establish connection with RabbitMQ server
        self.logger.info(
            f"Attempting to connect to RabbitMQ at {self._message_broker_host}:{self._message_broker_port}...")
        try:
            self._connection = pika.BlockingConnection(self._connection_parameters)
            self._channel = self._connection.channel()
            self._setup()
            self.logger.info("Connected to RabbitMQ successfully")
            return True  # Exit if connection is successful
        except AMQPConnectionError as e:
            self.logger.error(
                f"Failed to connect to RabbitMQ after attempts.")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise e

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
    def _setup(self) -> None:
        """Subclasses should override this method to declare queues, exchanges, bind queues to exchanges, handle dead letter queues, etc.
        Example:
            self._channel.queue_declare(queue='my_queue', durable=True)
            self._channel.basic_qos(prefetch_count=1) # Set prefetch count for fair dispatch
        """
        pass
