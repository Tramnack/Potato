"""
Unit tests for the AbstractRabbitMQ class.

This test suite verifies the functionality of the AbstractRabbitMQ class, including:
- Parameter validation during initialization.
- Connection logic, including retry mechanisms on failure.
- Graceful handling of resource cleanup for connections and channels,
  both through explicit disconnect methods and the class destructor.
"""
import os
from unittest.mock import patch

import pytest
from pika.exceptions import AMQPConnectionError

from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ
from tests.services_tests.shared_libs_tests.RabbitMQ_tests.test_utils import mock_pika


# Define a concrete implementation of the abstract class for testing purposes.
class ConcreteRabbitMQ(AbstractRabbitMQ):
    """A concrete RabbitMQ class for testing the abstract base class."""

    def __init__(self, *args, **kwargs):
        self.setup_called = False
        super().__init__(*args, **kwargs)

    def _setup(self):
        """A concrete setup implementation that flags when it has been called."""
        self.setup_called = True


# --- Pytest Fixtures ---


@pytest.fixture
def mock_sleep():
    """A fixture to mock time.sleep to prevent delays in tests."""
    with patch('time.sleep', return_value=None) as sleep_mock:
        yield sleep_mock


@patch('pika.BlockingConnection')
def rabbitmq_instance(mock_blocking_connection, **params):
    """
    Provides a configured instance of ConcreteRabbitMQ.
    Allows passing kwargs to the constructor through pytest.mark.parametrize.
    """
    instance = ConcreteRabbitMQ(**params)
    return instance


# --- Test Suites ---

class TestInitialization:
    """Tests focused on the __init__ method and parameter validation."""

    def test_successful_initialization(self):
        """Test that the class initializes correctly with valid parameters."""
        instance = ConcreteRabbitMQ(host="localhost", port=5672, connection_attempts=5, retry_delay=0.5)
        assert instance._message_broker_host == "localhost"
        assert instance._connection_parameters.host == "localhost"
        assert instance._message_broker_port == 5672
        assert instance._connection_parameters.port == 5672
        assert instance._connection_parameters.connection_attempts == 5
        assert instance._connection_parameters.retry_delay == 0.5
        assert not instance.setup_called  # setup() should only be called by connect()

    def test_connect_calls_setup(self, mock_pika):
        instance = ConcreteRabbitMQ(host="localhost", port=5672, connection_attempts=5, retry_delay=0.5)
        assert not instance.setup_called
        instance.connect()
        assert instance.setup_called

    @pytest.mark.parametrize("invalid_host", ["", "   ", "\n", "\t"])
    def test_init_raises_value_error_for_invalid_host(self, invalid_host):
        """Test that __init__ raises a ValueError for an invalid host type."""
        with pytest.raises(ValueError, match="host must not be empty."):
            ConcreteRabbitMQ(host=invalid_host)

    @pytest.mark.parametrize("invalid_host", [123, None, []])
    def test_init_raises_type_error_for_invalid_host(self, invalid_host):
        """Test that __init__ raises a TypeError for an invalid host type."""
        with pytest.raises(TypeError, match="host must be a string."):
            ConcreteRabbitMQ(host=invalid_host)

    @pytest.mark.parametrize("invalid_port", [0, -1, -1000])
    def test_init_raises_error_for_invalid_port(self, invalid_port):
        """Test that __init__ raises a ValueError for an invalid port."""
        with pytest.raises(ValueError, match="port must be a positive integer."):
            ConcreteRabbitMQ(port=invalid_port)

    @pytest.mark.parametrize("invalid_port", ["abc", None, list(), 1.1])
    def test_init_raises_type_error_for_invalid_port(self, invalid_port):
        """Test that __init__ raises a TypeError for an invalid port."""
        with pytest.raises(TypeError, match="port must be a positive integer."):
            ConcreteRabbitMQ(port=invalid_port)

    @pytest.mark.parametrize("invalid_attempts", [0, -1, -1000])
    def test_init_raises_value_error_for_invalid_connection_attempts(self, invalid_attempts):
        """Test that __init__ raises a ValueError for invalid connection_attempts."""
        with pytest.raises(ValueError, match="max_retries must be a positive integer."):
            ConcreteRabbitMQ(connection_attempts=invalid_attempts)

    @pytest.mark.parametrize("invalid_attempts", ["abc", None, list(), 1.1])
    def test_init_raises_type_error_for_invalid_connection_attempts(self, invalid_attempts):
        """Test that __init__ raises a ValueError for invalid connection_attempts."""
        with pytest.raises(TypeError, match="max_retries must be a positive integer."):
            ConcreteRabbitMQ(connection_attempts=invalid_attempts)

    @pytest.mark.parametrize("invalid_interval", [0.0, -1.0, -1000])
    def test_init_raises_value_error_for_invalid_retry_delay(self, invalid_interval):
        """Test that __init__ raises a ValueError for an invalid retry_delay."""
        with pytest.raises(ValueError, match="retry_delay must be a positive float."):
            ConcreteRabbitMQ(retry_delay=invalid_interval)

    @pytest.mark.parametrize("invalid_interval", ["abc", None, list()])
    def test_init_raises_type_error_for_invalid_retry_delay(self, invalid_interval):
        """Test that __init__ raises a TypeError for an invalid retry_delay."""
        with pytest.raises(TypeError, match="retry_delay must be a positive float."):
            ConcreteRabbitMQ(retry_delay=invalid_interval)


class TestConnectionHandling:
    """Tests focused on the connect() method and related logic."""

    @pytest.mark.parametrize("params", [{"connection_attempts": 1}, {"connection_attempts": 5}])
    def test_connect_succeeds(self, params, mock_pika, mock_sleep):
        """Test a successful connection on the first attempt without any retries."""
        instance = rabbitmq_instance(**params)
        mock_blocking_connection, _, mock_channel = mock_pika
        success = instance.connect()

        assert success
        mock_blocking_connection.assert_called_once()
        assert instance._channel == mock_channel
        mock_sleep.assert_not_called()

    @pytest.mark.parametrize("params", [{"connection_attempts": 1}, {"connection_attempts": 5, "retry_delay": 0.1}])
    def test_connect_returns_false_after_max_retries(self, params, mock_pika, mock_sleep):
        """Test that connect() raises an exception after exhausting all retry attempts."""
        instance = rabbitmq_instance(**params)
        mock_blocking_connection, _, _ = mock_pika
        mock_blocking_connection.side_effect = AMQPConnectionError

        success = instance.connect()

        assert not success
        assert mock_blocking_connection.call_count == 1
        mock_sleep.assert_not_called()

    def test_setup_method_is_called_on_connect(self, mock_pika):
        """Test that the concrete setup() method is called after a successful connection."""
        instance = rabbitmq_instance()
        assert not instance.setup_called
        instance.connect()
        assert instance.setup_called


class TestReadyState:
    """Tests focused on the is_ready() method."""

    def test_is_ready_returns_true_when_connected(self, mock_pika):
        """Test that is_ready() returns True when the instance is connected."""
        instance = rabbitmq_instance()
        instance.connect()

        assert instance._channel is not None
        assert instance._channel.is_open

        assert instance._connection is not None
        assert instance._connection.is_open

        assert instance._ready()

    def test_is_ready_returns_false_when_disconnected(self, mock_pika):
        """Test that is_ready() returns True when the instance is disconnected."""
        instance = rabbitmq_instance()
        instance.connect()
        instance.disconnect()

        assert instance._channel is not None
        assert not instance._channel.is_open

        assert instance._connection is not None
        assert not instance._connection.is_open

        assert not instance._ready()

    def test_is_ready_returns_false_without_connection(self, mock_pika):
        """Test that is_ready() returns True when the instance was never connected."""
        instance = rabbitmq_instance()

        assert instance._channel is None
        assert instance._connection is None

        assert not instance._ready()

    def test_is_ready_returns_false_without_channel(self, mock_pika):
        """Test that is_ready() returns True when the instance lost its channel."""
        instance = rabbitmq_instance()
        instance.connect()

        assert instance._channel is not None
        assert instance._channel.is_open

        assert instance._connection is not None
        assert instance._connection.is_open

        instance._channel = None
        assert instance._channel is None

        assert not instance._ready()

    def test_is_ready_returns_false_with_closed_channel(self, mock_pika):
        """Test that is_ready() returns True when the instance lost its channel."""
        instance = rabbitmq_instance()
        instance.connect()

        assert instance._channel is not None
        assert instance._channel.is_open

        assert instance._connection is not None
        assert instance._connection.is_open

        instance._channel.close()

        assert instance._channel is not None
        assert not instance._channel.is_open

        assert not instance._ready()


class TestResourceCleanup:
    """
    Tests focused on the explicit and implicit (__del__) cleanup of resources.
    Note: Testing __del__ relies on deterministic garbage collection (as in CPython).
    """

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Load environment variables to enable logging for output capture."""

        os.environ["LOG_LEVEL"] = "DEBUG"

    def test_destructor_closes_open_connection_and_channel(self, mock_pika, capsys):
        """Test that the destructor (__del__) closes an open connection and channel."""
        instance = rabbitmq_instance()
        instance.connect()
        _, mock_connection, mock_channel = mock_pika

        assert mock_connection.is_open
        assert mock_channel.is_open

        del instance

        assert not mock_connection.is_open
        assert not mock_channel.is_open

        mock_connection.close.assert_called_once()
        captured = capsys.readouterr()
        assert "Connection closed." in captured.out

    def test_destructor_handles_already_closed_connection(self, mock_pika, capsys):
        """Test that the destructor handles an already closed connection gracefully."""
        instance = rabbitmq_instance()
        instance.connect()
        _, mock_connection, _ = mock_pika

        instance.disconnect()  # Manually disconnect the connection
        mock_connection.close.assert_called_once()

        del instance
        mock_connection.close.assert_called_once()  # Ensure disconnect wasn't called again
        assert "Connection already closed." in capsys.readouterr().out

    def test_destructor_handles_no_active_connection(self, mock_pika, capsys):
        """Test that the destructor runs without error if connect() was never called."""
        instance = rabbitmq_instance()
        _, mock_connection, mock_channel = mock_pika

        # instance is created but connect() is never called.
        del instance

        mock_connection.close.assert_not_called()
        captured = capsys.readouterr()
        assert "Connection already closed." in captured.out
