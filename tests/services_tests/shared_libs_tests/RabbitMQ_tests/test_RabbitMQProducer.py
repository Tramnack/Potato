import os
from unittest.mock import patch

import pika
import pytest
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from services.shared_libs.RabbitMQ import RabbitMQProducer
from services_tests.shared_libs_tests.RabbitMQ_tests.test_utils import mock_pika


# Define a concrete implementation for testing the abstract class
class ConcreteProducer(RabbitMQProducer):
    def __init__(self, *args, **kwargs):
        self.setup_called = False
        super().__init__(*args, **kwargs)

    def _setup(self):
        """Concrete implementation for testing."""
        self.setup_called = True


class ConcreteAlwaysReadyProducer(ConcreteProducer):
    def _ready(self):
        return True

    def disconnect_channel(self):
        self._channel.close()

    def disconnect_connection(self):
        self._connection.close()


@patch('pika.BlockingConnection')
def rabbitmq_instance_ready(mock_blocking_connection):
    """
    Provides a configured instance of ConcreteRabbitMQ.
    Allows passing kwargs to the constructor through pytest.mark.parametrize.
    """
    instance = ConcreteProducer()
    instance.connect()
    assert instance._ready()
    return instance


@patch('pika.BlockingConnection')
def rabbitmq_instance_not_ready(mock_blocking_connection):
    """
    Provides a configured instance of ConcreteRabbitMQ.
    Allows passing kwargs to the constructor through pytest.mark.parametrize.
    """
    instance = ConcreteProducer()
    assert not instance._ready()
    return instance


class TestInitialization:
    @pytest.mark.parametrize("params",
                             [{"host": "localhost", "port": 5672, "connection_attempts": 1, "retry_delay": 0.1}])
    def test_rabbitmq_producer_init_valid_params(self, params, mock_pika):
        instance = ConcreteProducer(**params)
        assert instance._message_broker_host == "localhost"
        assert instance._connection_parameters.host == "localhost"
        assert instance._message_broker_port == 5672
        assert instance._connection_parameters.port == 5672
        assert instance._connection_parameters.connection_attempts == 1
        assert instance._connection_parameters.retry_delay == 0.1
        assert not instance.setup_called  # setup() should only be called by connect()


class TestBasicPublish:
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Load environment variables to enable logging for output capture."""
        os.environ["LOG_LEVEL"] = "DEBUG"

    def test_basic_publish_success(self, mock_pika):
        # Directly test the internal _basic_publish method to ensure it correctly interacts with the pika channel's
        # basic_publish method under normal circumstances, including setting delivery_mode based on the durable flag.
        instance = rabbitmq_instance_ready()

        instance._basic_publish("test_exchange", "test_routing_key", b"test_message")  # durable=True by default
        instance._channel.basic_publish.assert_called_once_with(
            exchange="test_exchange",
            routing_key="test_routing_key",
            body=b"test_message",
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent)
        )

    def test_basic_publish_durable(self, mock_pika):
        # Explicitly verify that when durable is True, pika.BasicProperties(delivery_mode=2) is passed to
        instance = rabbitmq_instance_ready()

        instance._basic_publish("test_exchange", "test_routing_key", b"test_message", durable=True)
        instance._channel.basic_publish.assert_called_once_with(
            exchange="test_exchange",
            routing_key="test_routing_key",
            body=b"test_message",
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent)
        )

    def test_basic_publish_not_durable(self, mock_pika):
        # Explicitly verify that when durable is False, properties=None is passed to basic_publish.
        instance = rabbitmq_instance_ready()

        instance._basic_publish("test_exchange", "test_routing_key", b"test_message", durable=False)
        instance._channel.basic_publish.assert_called_once_with(
            exchange="test_exchange",
            routing_key="test_routing_key",
            body=b"test_message",
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Transient)
        )

    def test_basic_publish_when_not_connected(self, mock_pika):
        # Although publish handles this, it's good to ensure _basic_publish itself also relies on _ready() and raises
        # the RuntimeError if called directly when not connected.
        instance = rabbitmq_instance_not_ready()
        assert not instance._ready()

        with pytest.raises(RuntimeError, match="RabbitMQProducer is not connected."):
            instance._basic_publish("test_exchange", "test_routing_key", b"test_message", durable=True)

    def test_basic_publish_when_log_success(self, mock_pika, capsys):
        # Verify that a success message is logged when _basic_publish successfully publishes a message.
        instance = rabbitmq_instance_ready()

        instance._basic_publish("test_exchange", "test_routing_key", b"test_message")

        captured = capsys.readouterr()
        assert "Published message to exchange: test_exchange, routing key: test_routing_key" in captured.out

    def test_basic_publish_when_log_error_connection(self, mock_pika, capsys):
        # Verify that appropriate error messages are logged when AMQPChannelError or AMQPConnectionError occur during
        # _basic_publish.
        # Verify that a success message is logged when _basic_publish successfully publishes a message.
        instance = ConcreteAlwaysReadyProducer()
        instance.connect()
        instance.disconnect_connection()

        assert instance._ready()
        assert not instance._connection.is_open

        with pytest.raises(AMQPConnectionError):
            instance._basic_publish("test_exchange", "test_routing_key", b"test_message")

        captured = capsys.readouterr()
        assert "AMQP Connection Error during publish" in captured.out

    def test_basic_publish_when_log_error_channel(self, mock_pika, capsys):
        # Verify that appropriate error messages are logged when AMQPChannelError or AMQPConnectionError occur during
        # _basic_publish.
        # Verify that a success message is logged when _basic_publish successfully publishes a message.
        instance = ConcreteAlwaysReadyProducer()
        instance.connect()
        instance.disconnect_channel()

        assert instance._ready()
        assert instance._connection.is_open
        assert not instance._channel.is_open

        with pytest.raises(AMQPChannelError):
            instance._basic_publish("test_exchange", "test_routing_key", b"test_message")

        captured = capsys.readouterr()
        assert "AMQP Channel Error during publish" in captured.out


class TestPublish:
    def test_publish_with_default_exchange(self, mock_pika):
        """..."""
        # Ensure that messages are correctly published to the default exchange when no exchange is specified and durable
        # is False. This tests the basic functionality and the delivery_mode property.
        instance = rabbitmq_instance_ready()

        instance.publish(b"test_message", "test_routing_key")  # durable=True by default
        instance._channel.basic_publish.assert_called_once_with(
            exchange="",  # Default exchange
            routing_key="test_routing_key",
            body=b"test_message",
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent)
        )

    def test_publish_with_default_exchange_durable(self, mock_pika):
        """..."""
        # Verify that messages are correctly published to the default exchange with delivery_mode=2 (
        # durable) when durable is True.
        #
        instance = rabbitmq_instance_ready()

        instance.publish(b"test_message", "test_routing_key", durable=True)
        instance._channel.basic_publish.assert_called_once_with(
            exchange="",  # Default exchange
            routing_key="test_routing_key",
            body=b"test_message",
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent)
        )

    def test_publish_with_default_exchange_not_durable(self, mock_pika):
        """..."""
        # Ensure that messages are correctly published to the default exchange when no exchange is specified and durable
        # is False. This tests the basic functionality and the delivery_mode property.
        instance = rabbitmq_instance_ready()

        instance.publish(b"test_message", "test_routing_key", durable=False)
        instance._channel.basic_publish.assert_called_once_with(
            exchange="",  # Default exchange
            routing_key="test_routing_key",
            body=b"test_message",
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Transient)
        )

    def test_publish_with_custom_exchange(self, mock_pika):
        # Confirm that the producer can publish messages to a user-defined exchange with durable set to False.
        #
        instance = rabbitmq_instance_ready()

        instance.publish(b"test_message", "test_routing_key", "test_exchange", durable=False)
        instance._channel.basic_publish.assert_called_once_with(
            exchange="test_exchange",  # Default exchange
            routing_key="test_routing_key",
            body=b"test_message",
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Transient)
        )

    def test_publish_with_custom_exchange_durable(self, mock_pika):
        # Ensure that messages are published to a user-defined exchange with delivery_mode=2 when durable is True.
        #
        instance = rabbitmq_instance_ready()

        instance.publish(b"test_message", "test_routing_key", "test_exchange", durable=True)
        instance._channel.basic_publish.assert_called_once_with(
            exchange="test_exchange",  # Default exchange
            routing_key="test_routing_key",
            body=b"test_message",
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent)
        )

    def test_publish_when_not_connected(self, mock_pika):
        #
        # Verify that a RuntimeError is raised when publish is called before the producer has successfully connected to
        # RabbitMQ (i.e., when _ready() returns False).
        #
        instance = rabbitmq_instance_not_ready()

        with pytest.raises(RuntimeError, match="RabbitMQProducer is not connected."):
            instance.publish(b"test_message", "test_routing_key")

    def test_publishHandles_AMQPConnectionError(self, mock_pika, capsys):
        #
        # Simulate an AMQPConnectionError during _basic_publish to ensure that the exception is caught, logged, and
        # re-raised correctly, indicating issues with the underlying connection.
        instance = ConcreteAlwaysReadyProducer()
        instance.connect()
        instance.disconnect_connection()

        assert instance._ready()
        assert not instance._connection.is_open
        assert not instance._channel.is_open

        with pytest.raises(AMQPConnectionError):
            instance.publish(b"test_message", "test_routing_key")

        captured = capsys.readouterr()
        assert "Error during publish" in captured.out

    def test_publishHandles_AMQPChannelError(self, mock_pika, capsys):
        #
        # Simulate an AMQPChannelError during _basic_publish to ensure that the exception is caught, logged, and
        # re-raised correctly, indicating issues with the channel.
        instance = ConcreteAlwaysReadyProducer()
        instance.connect()
        instance.disconnect_channel()

        assert instance._ready()
        assert instance._connection.is_open
        assert not instance._channel.is_open

        with pytest.raises(AMQPChannelError):
            instance.publish(b"test_message", "test_routing_key")

        captured = capsys.readouterr()
        assert "Error during publish" in captured.out
