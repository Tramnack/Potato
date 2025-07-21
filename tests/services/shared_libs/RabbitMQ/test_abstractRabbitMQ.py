import os
from unittest.mock import patch, MagicMock

import pytest
from dotenv import load_dotenv
from pika.exceptions import AMQPConnectionError

from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ


# Define a concrete implementation for testing the abstract class
class ConcreteRabbitMQ(AbstractRabbitMQ):
    def __init__(self, *args, **kwargs):
        self.setup_called = False
        super().__init__(*args, **kwargs)

    def setup(self):
        """Concrete implementation for testing."""
        self.setup_called = True


def setup_mock_connection(mock_blocking_connection, open_connection):
    mock_connection = MagicMock()
    mock_connection.is_open = open_connection  # Simulate open/ closed connection
    mock_connection.close.side_effect = lambda: setattr(mock_connection, 'is_open', False)
    mock_blocking_connection.return_value = mock_connection

    return mock_connection


def setup_mock_channel(mock_connection, open_channel):
    mock_channel = MagicMock()
    mock_channel.is_open = open_channel
    mock_channel.close.side_effect = lambda: setattr(mock_channel, 'is_open', False)
    mock_connection.channel.return_value = mock_channel

    return mock_channel


# --- Test Initialization and Validation ---

@patch('pika.BlockingConnection')
def test_abstract_rabbitmq_init_valid_params(mock_blocking_connection):
    """Test successful initialization with valid parameters."""
    instance = ConcreteRabbitMQ(host="localhost", port=5672, max_attempts=1, attempt_interval=0.1)
    assert instance._message_broker_host == "localhost"  #
    assert instance._message_broker_port == 5672  #
    assert instance._max_attempts == 1  #
    assert instance._attempt_interval == 0.1  #
    assert instance.setup_called is False  # setup method should be called on connect


@pytest.mark.parametrize("invalid_host", [123, None, []])
def test_abstract_rabbitmq_init_invalid_host(invalid_host):
    """Test initialization with invalid host types."""
    with pytest.raises(ValueError, match="host must be a string."):
        ConcreteRabbitMQ(host=invalid_host)


@pytest.mark.parametrize("invalid_port", ["abc", 0, -1, None])
def test_abstract_rabbitmq_init_invalid_port(invalid_port):
    """Test initialization with invalid port values/types."""
    with pytest.raises(ValueError, match="port must be a positive integer."):
        ConcreteRabbitMQ(port=invalid_port)


@pytest.mark.parametrize("invalid_attempts", ["abc", 0, -1, None])
def test_abstract_rabbitmq_init_invalid_max_attempts(invalid_attempts):
    """Test initialization with invalid max_attempts values/types."""
    with pytest.raises(ValueError, match="max_retries must be a positive integer."):
        ConcreteRabbitMQ(max_attempts=invalid_attempts)


@pytest.mark.parametrize("invalid_interval", ["abc", 0.0, -1.0, None])
def test_abstract_rabbitmq_init_invalid_attempt_interval(invalid_interval):
    """Test initialization with invalid attempt_interval values/types."""
    with pytest.raises(ValueError, match="attempt_interval must be a positive float."):
        ConcreteRabbitMQ(attempt_interval=invalid_interval)


# --- Test Connection Logic (connect method) ---

@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)  # Mock time.sleep to avoid actual delays
def test_connect_success_first_attempt(mock_sleep, mock_blocking_connection):
    """Test successful connection on the first attempt."""
    mock_channel = MagicMock()
    mock_connection = MagicMock()
    mock_connection.channel.return_value = mock_channel
    mock_blocking_connection.return_value = mock_connection

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()

    mock_blocking_connection.assert_called_once()  # Called on __init__
    mock_sleep.assert_not_called()  #
    assert instance.channel == mock_channel  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_connect_success_after_retries(mock_sleep, mock_blocking_connection):
    """Test successful connection after a few retries."""
    mock_channel = MagicMock()
    mock_connection = MagicMock()
    mock_connection.channel.return_value = mock_channel

    # Configure BlockingConnection to raise AMQPConnectionError twice, then succeed
    mock_blocking_connection.side_effect = [
        AMQPConnectionError,
        AMQPConnectionError,
        mock_connection  # Success on the third call
    ]

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=3, attempt_interval=0.01)  #
    instance.connect()

    assert mock_blocking_connection.call_count == 3  #
    assert mock_sleep.call_count == 2  # Sleep should be called after each failed attempt
    mock_sleep.assert_called_with(0.01)  # Check sleep interval
    assert instance.channel == mock_channel  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_connect_failure_after_max_attempts(mock_sleep, mock_blocking_connection):
    """Test that connection fails and raises an exception after max_attempts."""
    mock_blocking_connection.side_effect = AMQPConnectionError  # Always fail

    with pytest.raises(Exception, match="Failed to connect to RabbitMQ after "):  #
        instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=3, attempt_interval=1)  #
        instance.connect()

    assert mock_blocking_connection.call_count == 3  #
    assert mock_sleep.call_count == 3  # Sleep after each failed attempt, including the last one before raising


# --- Test Channel Property ---

@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_channel_property(mock_sleep, mock_blocking_connection):
    """Test that the channel property returns the correct channel."""
    mock_channel = MagicMock()
    mock_connection = MagicMock()
    mock_connection.channel.return_value = mock_channel
    mock_blocking_connection.return_value = mock_connection

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()
    assert instance.channel == mock_channel  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_close_channel_if_open(mock_sleep, mock_blocking_connection, capsys):
    """Test that __del__ closes the channel if it's open."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_channel = MagicMock()
    mock_channel.is_open = True  # Simulate open channel
    mock_connection = MagicMock()
    mock_connection.is_open = True  # Simulate open connection
    mock_connection.channel.return_value = mock_channel
    mock_blocking_connection.return_value = mock_connection

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()  # Ensure the channel and connection are created

    instance.close_channel()

    mock_channel.close.assert_called_once()  #
    captured = capsys.readouterr()  # Capture print statements
    assert "Channel closed." in captured.out  #


# --- Test __del__ method ---

@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_connection_if_open(mock_sleep, mock_blocking_connection, capsys):
    """Test that __del__ closes the connection if it's open."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_connection = setup_mock_connection(mock_blocking_connection, open_connection=True)

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()  # Ensure the channel and connection are created
    assert mock_connection.is_open

    # Explicitly delete the instance to call __del__
    del instance

    mock_connection.close.assert_called_once()  #
    captured = capsys.readouterr()  # Capture print statements
    assert "Closing RabbitMQ connection." in captured.out  #
    assert "Connection closed." in captured.out  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_connection_if_already_closed(mock_sleep, mock_blocking_connection, capsys):
    """Test that __del__ closes the connection if it's closed."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_connection = setup_mock_connection(mock_blocking_connection, open_connection=False)

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()  # Ensure the channel and connection are created
    # Explicitly delete the instance to call __del__
    del instance

    mock_connection.close.assert_not_called()  #
    captured = capsys.readouterr()  # Capture print statements
    assert "Closing RabbitMQ connection." in captured.out  #
    assert "Connection already closed." in captured.out  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_connection_after_close(mock_sleep, mock_blocking_connection, capsys):
    """Test that __del__ closes the connection if it's closed."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_connection = setup_mock_connection(mock_blocking_connection, open_connection=True)

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()  # Ensure the channel and connection are created
    instance.close()  # Close the connection

    mock_connection.close.assert_called_once()  # Called, but not by __del__
    # Explicitly delete the instance to call __del__ after close
    del instance

    mock_connection.close.assert_called_once()  # Called, but not by __del__
    captured = capsys.readouterr()  # Capture print statements
    assert "Closing RabbitMQ connection." in captured.out  #
    assert "Connection already closed." in captured.out  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_connection_never_connected(mock_sleep, mock_blocking_connection, capsys):
    """Test that __del__ closes the connection if it's closed."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_connection = setup_mock_connection(mock_blocking_connection, open_connection=True)

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    # instance.connect()  # Don't connect
    # instance.close()  # Close the connection

    # Explicitly delete the instance to call __del__ after close
    del instance

    assert mock_connection.close.call_count == 0  #

    captured = capsys.readouterr()  # Capture print statements
    assert "Closing RabbitMQ connection." in captured.out  #
    assert "Connection already closed." in captured.out  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_channel_if_open(mock_sleep, mock_blocking_connection, capsys):
    """Test that __del__ closes the connection if it's open."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_connection = setup_mock_connection(mock_blocking_connection, open_connection=True)
    mock_channel = setup_mock_channel(mock_connection, open_channel=True)

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()  # Ensure the channel and connection are created

    # Connection and channel are open
    assert mock_connection.is_open
    assert mock_channel.is_open
    assert mock_connection.close.call_count == 0  #

    # Explicitly delete the instance to call __del__
    del instance

    assert mock_connection.close.call_count == 1  #

    captured = capsys.readouterr()  # Capture print statements
    assert "Channel closed." in captured.out  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_channel_if_closed(mock_sleep, mock_blocking_connection, capsys):
    """..."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_connection = setup_mock_connection(mock_blocking_connection, open_connection=True)
    mock_channel = setup_mock_channel(mock_connection, open_channel=False)

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()  # Ensure the channel and connection are created

    # Connection is open
    assert mock_connection.is_open
    assert not mock_channel.is_open
    assert mock_connection.close.call_count == 0  #

    # Explicitly delete the instance to call __del__
    del instance

    assert mock_connection.close.call_count == 1  #
    assert mock_channel.close.call_count == 0  #

    captured = capsys.readouterr()  # Capture print statements
    assert "Channel already closed." in captured.out  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_channel_if_connection_closed(mock_sleep, mock_blocking_connection, capsys):
    """..."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_connection = setup_mock_connection(mock_blocking_connection, open_connection=False)
    mock_channel = setup_mock_channel(mock_connection, open_channel=False)

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()  # Ensure the channel and connection are created
    assert not mock_connection.is_open
    assert not mock_channel.is_open

    # Explicitly delete the instance to call __del__
    del instance

    assert mock_connection.close.call_count == 0  #
    assert mock_channel.close.call_count == 0  #

    captured = capsys.readouterr()  # Capture print statements
    assert "Channel already closed." in captured.out  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_channel_after_channel_closed(mock_sleep, mock_blocking_connection, capsys):
    """..."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_connection = setup_mock_connection(mock_blocking_connection, open_connection=True)
    mock_channel = setup_mock_channel(mock_connection, open_channel=True)

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    instance.connect()  # Ensure the channel and connection are created
    assert mock_connection.is_open
    assert mock_channel.is_open

    instance.close_channel()

    assert mock_connection.close.call_count == 0  #
    assert mock_channel.close.call_count == 1  #

    # Explicitly delete the instance to call __del__
    del instance

    assert mock_connection.close.call_count == 1  #
    assert mock_channel.close.call_count == 1  #

    captured = capsys.readouterr()  # Capture print statements
    assert "Channel already closed." in captured.out  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_channel_if_no_connection(mock_sleep, mock_blocking_connection, capsys):
    """..."""
    load_dotenv(".env")
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    mock_connection = setup_mock_connection(mock_blocking_connection, open_connection=False)
    mock_channel = setup_mock_channel(mock_connection, open_channel=False)

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    # instance.connect()  # Ensure the channel and connection are created
    assert not mock_connection.is_open
    assert not mock_channel.is_open

    # Explicitly delete the instance to call __del__
    del instance

    assert mock_connection.close.call_count == 0  #
    assert mock_channel.close.call_count == 0  #

    captured = capsys.readouterr()  # Capture print statements
    assert "Channel already closed." in captured.out  #


# --- Test Setup method call ---
@patch('pika.BlockingConnection')
def test_setup_called_on_init(mock_blocking_connection):
    """Test that the abstract setup method is called during initialization."""
    # We use ConcreteRabbitMQ which sets a flag when setup is called
    instance = ConcreteRabbitMQ(host="localhost", port=5672, max_attempts=1, attempt_interval=0.1)  #
    assert instance.setup_called is False  #
    instance.connect()
    assert instance.setup_called is True
