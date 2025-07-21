"""
Unit tests for the AbstractRabbitMQ class.

This test suite verifies the functionality of the AbstractRabbitMQ class, including:
- Parameter validation during initialization.
- Connection logic, including retry mechanisms on failure.
- Graceful handling of resource cleanup for connections and channels,
  both through explicit close methods and the class destructor.
"""
import os
from unittest.mock import patch, MagicMock

import pytest
from pika.exceptions import AMQPConnectionError

from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ


# Define a concrete implementation of the abstract class for testing purposes.
class ConcreteRabbitMQ(AbstractRabbitMQ):
    """A concrete RabbitMQ class for testing the abstract base class."""

    def __init__(self, *args, **kwargs):
        self.setup_called = False
        super().__init__(*args, **kwargs)

    def setup(self):
        """A concrete setup implementation that flags when it has been called."""
        self.setup_called = True


# --- Pytest Fixtures ---

@pytest.fixture
def mock_pika():
    """A fixture to mock the pika.BlockingConnection and its components."""

    def close_connection(connection):
        setattr(connection, 'is_open', False)
        setattr(connection.channel.return_value, 'is_open', False)

    with patch('pika.BlockingConnection') as mock_blocking_connection:
        mock_connection = MagicMock()
        mock_connection.is_open = True
        mock_connection.close.side_effect = lambda: close_connection(mock_connection)

        mock_channel = MagicMock()
        mock_channel.is_open = True

        mock_connection.channel.return_value = mock_channel
        mock_blocking_connection.return_value = mock_connection

        yield mock_blocking_connection, mock_connection, mock_channel


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
        instance = ConcreteRabbitMQ(host="localhost", port=5672, max_attempts=5, attempt_interval=0.5)
        assert instance._message_broker_host == "localhost"
        assert instance._message_broker_port == 5672
        assert instance._max_attempts == 5
        assert instance._attempt_interval == 0.5
        assert not instance.setup_called  # setup() should only be called by connect()

    @pytest.mark.parametrize("invalid_host", [123, None, []])
    def test_init_raises_error_for_invalid_host(self, invalid_host):
        """Test that __init__ raises a ValueError for an invalid host type."""
        with pytest.raises(ValueError, match="host must be a string."):
            ConcreteRabbitMQ(host=invalid_host)

    @pytest.mark.parametrize("invalid_port", ["abc", 0, -1, None])
    def test_init_raises_error_for_invalid_port(self, invalid_port):
        """Test that __init__ raises a ValueError for an invalid port."""
        with pytest.raises(ValueError, match="port must be a positive integer."):
            ConcreteRabbitMQ(port=invalid_port)

    @pytest.mark.parametrize("invalid_attempts", ["abc", 0, -1, None])
    def test_init_raises_error_for_invalid_max_attempts(self, invalid_attempts):
        """Test that __init__ raises a ValueError for invalid max_attempts."""
        with pytest.raises(ValueError, match="max_retries must be a positive integer."):
            ConcreteRabbitMQ(max_attempts=invalid_attempts)

    @pytest.mark.parametrize("invalid_interval", ["abc", 0.0, -1.0, None])
    def test_init_raises_error_for_invalid_attempt_interval(self, invalid_interval):
        """Test that __init__ raises a ValueError for an invalid attempt_interval."""
        with pytest.raises(ValueError, match="attempt_interval must be a positive float."):
            ConcreteRabbitMQ(attempt_interval=invalid_interval)


class TestConnectionHandling:
    """Tests focused on the connect() method and related logic."""

    @pytest.mark.parametrize("params", [{"max_attempts": 3}])
    def test_connect_succeeds_on_first_try(self, params, mock_pika, mock_sleep):
        """Test a successful connection on the first attempt without any retries."""
        instance = rabbitmq_instance(**params)
        mock_blocking_connection, _, mock_channel = mock_pika
        instance.connect()

        mock_blocking_connection.assert_called_once()
        mock_sleep.assert_not_called()
        assert instance._channel == mock_channel

    @pytest.mark.parametrize("params", [{"max_attempts": 3, "attempt_interval": 0.01}])
    def test_connect_succeeds_after_retries(self, params, mock_pika, mock_sleep):
        """Test that the connection succeeds after several failed attempts."""
        instance = rabbitmq_instance(**params)
        mock_blocking_connection, mock_connection, mock_channel = mock_pika
        mock_blocking_connection.side_effect = [AMQPConnectionError, AMQPConnectionError, mock_connection]

        instance.connect()

        assert mock_blocking_connection.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.01)
        assert instance._channel == mock_channel

    @pytest.mark.parametrize("params", [{"max_attempts": 3}])
    def test_connect_raises_exception_after_max_retries(self, params, mock_pika, mock_sleep):
        """Test that connect() raises an exception after exhausting all retry attempts."""
        instance = rabbitmq_instance(**params)
        mock_blocking_connection, _, _ = mock_pika
        mock_blocking_connection.side_effect = AMQPConnectionError

        with pytest.raises(Exception, match="Failed to connect to RabbitMQ after 3 attempts."):
            instance.connect()

        assert mock_blocking_connection.call_count == 3
        assert mock_sleep.call_count == 3

    @pytest.mark.parametrize("params", [{}])
    def test_setup_method_is_called_on_connect(self, params, mock_pika):
        """Test that the concrete setup() method is called after a successful connection."""
        instance = rabbitmq_instance(**params)
        assert not instance.setup_called
        instance.connect()
        assert instance.setup_called


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

        instance.close()  # Manually close the connection
        mock_connection.close.assert_called_once()

        del instance
        mock_connection.close.assert_called_once()  # Ensure close wasn't called again
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
