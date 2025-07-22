import os
from unittest.mock import patch

import pytest

from services.shared_libs.RabbitMQ import RabbitMQConsumer
from services_tests.shared_libs_tests.RabbitMQ_tests.test_utils import mock_pika


class ConcreteConsumer(RabbitMQConsumer):

    def __init__(self, *args, **kwargs):
        self.setup_called = False
        self.disconnect_called = False
        self.stop_consuming_called = False
        self.handle_unacknowledged_messages_called = False
        self.callback_called = False
        super().__init__(*args, **kwargs)

    def disconnect(self):
        self.disconnect_called = True
        super().disconnect()

    def stop_consuming(self) -> None:
        self.stop_consuming_called = True
        super().stop_consuming()

    def _setup(self):
        """Concrete implementation for testing."""
        self.setup_called = True

    def _callback(self, *args, **kwargs):
        """Concrete implementation for testing."""
        self.callback_called = True

    def _handle_unacknowledged_messages(self, un_acknowledged) -> None:
        """Concrete implementation for testing."""
        self.handle_unacknowledged_messages_called = True


@patch('pika.BlockingConnection')
def rabbitmq_instance_ready(queue_name, mock_blocking_connection):
    """
    Provides a configured instance of ConcreteRabbitMQ.
    Allows passing kwargs to the constructor through pytest.mark.parametrize.
    """
    instance = ConcreteConsumer(queue_name)
    instance.connect()
    assert instance._ready()
    return instance


@patch('pika.BlockingConnection')
def rabbitmq_instance_consuming(queue_name, mock_blocking_connection):
    """
    Provides a configured instance of ConcreteRabbitMQ.
    Allows passing kwargs to the constructor through pytest.mark.parametrize.
    """
    instance = ConcreteConsumer(queue_name)
    instance.connect()
    instance.consume()
    assert instance._ready()
    return instance


class TestInitialization:
    @pytest.mark.parametrize("params",
                             [{"queue_name": "test_queue", "host": "localhost", "port": 5672, "connection_attempts": 5,
                               "retry_delay": 0.5}])
    def test_rabbitmq_producer_init_valid_params(self, params, mock_pika):
        instance = ConcreteConsumer(**params)
        assert instance._message_broker_host == params["host"]
        assert instance._connection_parameters.host == params["host"]
        assert instance._message_broker_port == params["port"]
        assert instance._connection_parameters.port == params["port"]
        assert instance._connection_parameters.connection_attempts == params["connection_attempts"]
        assert instance._connection_parameters.retry_delay == params["retry_delay"]
        assert not instance.setup_called  # setup() should only be called by connect()

    def test_connect_calls_setup(self, mock_pika):
        instance = ConcreteConsumer(queue_name="test_queue")
        assert not instance.setup_called
        instance.connect()
        assert instance.setup_called


class TestConsume:
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Load environment variables to enable logging for output capture."""
        os.environ["LOG_LEVEL"] = "DEBUG"

    def test_rabbitmq_producer_init_valid_params(self, mock_pika):
        instance = rabbitmq_instance_ready("test_queue")
        assert instance.setup_called

    def test_consume_starts_consuming(self, mock_pika):
        """Verify that consume() starts the consumption process."""
        instance = rabbitmq_instance_ready("test_queue")
        instance.consume()

        assert instance._consuming
        assert instance._consumer_tag is not None
        instance._channel.basic_consume.assert_called_once()
        instance._channel.start_consuming.assert_called_once()

    def test_consume_with_restart_if_running_false(self, mock_pika):
        """Verify that calling consume() again with restart_if_running=False does nothing."""
        instance = rabbitmq_instance_consuming("test_queue")  # Starts in a consuming state
        instance._channel.reset_mock()  # Reset mocks to test the second call

        instance.consume(restart_if_running=False)

        # Asserts that no new consuming actions were taken
        instance._channel.basic_consume.assert_not_called()
        instance._channel.start_consuming.assert_not_called()
        assert not instance.stop_consuming_called

    def test_consume_with_restart_if_running_true(self, mock_pika):
        """Verify that calling consume() again with restart_if_running=True restarts the consumer."""
        instance = rabbitmq_instance_consuming("test_queue")  # Starts in a consuming state
        instance._channel.reset_mock()  # Reset mocks to test the second call

        instance.consume(restart_if_running=True)

        assert instance.stop_consuming_called
        instance._channel.basic_consume.assert_called_once()
        instance._channel.start_consuming.assert_called_once()

    def test_consume_raises_runtime_error_if_not_connected(self, mock_pika):
        """Verify that consume() raises a RuntimeError if the instance is not connected."""
        instance = ConcreteConsumer("test_queue")  # Not connected
        with pytest.raises(RuntimeError, match="not connected"):
            instance.consume()

    def test_consume_uses_custom_callback(self, mock_pika):
        """Verify that a custom callback can be passed to consume()."""
        instance = rabbitmq_instance_ready("test_queue")
        custom_callback = lambda a, b, c, d: None
        instance.consume(callback=custom_callback)

        instance._channel.basic_consume.assert_called_with(
            queue='test_queue',
            on_message_callback=custom_callback,
            auto_ack=False
        )


class TestStopConsuming:
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Load environment variables to enable logging for output capture."""
        os.environ["LOG_LEVEL"] = "DEBUG"

    @pytest.mark.parametrize("consuming", [True, False])
    def test_stop_consuming(self, mock_pika, consuming):
        instance = rabbitmq_instance_ready("test_queue")

        if consuming:
            instance.consume()
        else:
            assert instance._consumer_tag is None

        instance.stop_consuming()
        assert instance.stop_consuming_called
        assert instance._channel.basic_cancel.call_count == (1 if consuming else 0)  # Only called if consuming

    def test_stop_consuming_handles_unacknowledged_messages(self, mock_pika):
        """Verify that _handle_unacknowledged_messages is called if basic_cancel returns messages."""
        instance = rabbitmq_instance_consuming("test_queue")

        # Mock the return value of basic_cancel
        unacked_messages = [("ch", "method", "props", "body")]
        instance._channel.basic_cancel.return_value = unacked_messages

        instance.stop_consuming()

        assert instance.handle_unacknowledged_messages_called

    def test_stop_consuming_handles_no_unacknowledged_messages(self, mock_pika):
        """Verify that _handle_unacknowledged_messages is called if basic_cancel returns messages."""
        instance = rabbitmq_instance_consuming("test_queue")

        # Mock the return value of basic_cancel
        unacked_messages = []
        instance._channel.basic_cancel.return_value = unacked_messages

        instance.stop_consuming()

        assert not instance.handle_unacknowledged_messages_called


class TestQueueProperty:
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Load environment variables to enable logging for output capture."""
        os.environ["LOG_LEVEL"] = "DEBUG"

    @pytest.mark.parametrize("consuming", [True, False])
    def test_queue_getter(self, mock_pika, consuming):
        instance = rabbitmq_instance_ready("test_queue")
        if consuming:
            instance.consume()
            assert instance._consuming
            assert instance._consumer_tag
        else:
            assert not instance._consuming
            assert not instance._consumer_tag

        assert instance._queue == "test_queue"
        assert instance.queue == "test_queue"

    @pytest.mark.parametrize("consuming", [True, False])
    def test_queue_setter(self, mock_pika, consuming):
        instance = rabbitmq_instance_ready("test_queue")
        if consuming:
            instance.consume()

        instance.queue = "new_queue"
        assert instance._queue == "new_queue"
        assert instance.queue == "new_queue"

    @pytest.mark.parametrize("queue_name", [None, 0, list()])
    def test_queue_setter_invalid_type(self, mock_pika, queue_name):
        instance = rabbitmq_instance_consuming("test_queue")
        with pytest.raises(TypeError):
            instance.queue = queue_name

    def test_queue_setter_invalid_value(self, mock_pika):
        instance = rabbitmq_instance_consuming("test_queue")
        with pytest.raises(ValueError):
            instance.queue = ""

    @pytest.mark.parametrize("consuming", [True, False])
    def test_queue_setter_same_value_keeps_consuming(self, mock_pika, consuming):
        instance = rabbitmq_instance_ready("test_queue")
        if consuming:
            instance.consume()

        instance.queue = "test_queue"
        assert instance._queue == "test_queue"
        assert instance.queue == "test_queue"

        assert not instance.stop_consuming_called

    @pytest.mark.parametrize("consuming", [True, False])
    def test_queue_setter_different_value_stops_consuming(self, mock_pika, consuming):
        instance = rabbitmq_instance_ready("test_queue")
        if consuming:
            instance.consume()

        instance.queue = "new_queue"
        assert instance._queue == "new_queue"
        assert instance.queue == "new_queue"

        assert instance.stop_consuming_called == consuming  # Only called if consuming


class TestContextManager:
    @pytest.fixture(autouse=True)
    def setup_env(self):
        os.environ["LOG_LEVEL"] = "DEBUG"

    def test_context_manager_calls_stop_consuming_and_disconnect(self, mock_pika):
        """Verify that __exit__ calls stop_consuming and disconnect."""
        instance = rabbitmq_instance_ready("test_queue")
        instance.consume()  # Start consuming

        with instance as consumer:
            assert consumer is instance  # __enter__ returns self

        assert instance.stop_consuming_called
        assert instance.disconnect_called
