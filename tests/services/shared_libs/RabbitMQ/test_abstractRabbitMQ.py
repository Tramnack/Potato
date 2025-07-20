from unittest.mock import patch, MagicMock

import pytest
from pika.exceptions import AMQPConnectionError

from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ


# import time  # Import time for mocking purposes


# Define a concrete implementation for testing the abstract class
class ConcreteRabbitMQ(AbstractRabbitMQ):
    def __init__(self, *args, **kwargs):
        self.setup_called = False
        super().__init__(*args, **kwargs)

    def setup(self):
        """Concrete implementation for testing."""
        self.setup_called = True


# Fixture to patch Flask and threading for HealthCheckMixin, ensuring tests don't try to start a real server
@pytest.fixture(autouse=True)
def mock_health_check_dependencies():
    """Mocks Flask and threading to prevent actual server startup in HealthCheckMixin."""
    with patch('services.shared_libs.HealthCheckMixin.Flask', autospec=True) as mock_flask, \
            patch('services.shared_libs.HealthCheckMixin.threading', autospec=True) as mock_threading:
        # Configure the mock Flask app to return a mock run method
        mock_flask_instance = MagicMock()
        mock_flask.return_value = mock_flask_instance
        mock_flask_instance.route.return_value = lambda f: f  # Decorator returns the original function

        yield mock_flask, mock_threading


# --- Test Initialization and Validation ---

@patch('pika.BlockingConnection')
def test_abstract_rabbitmq_init_valid_params(mock_blocking_connection, mock_health_check_dependencies):
    """Test successful initialization with valid parameters."""
    instance = ConcreteRabbitMQ(host="localhost", port=5672, max_attempts=1, attempt_interval=0.1)
    assert instance._message_broker_host == "localhost"  #
    assert instance._message_broker_port == 5672  #
    assert instance._max_attempts == 1  #
    assert instance._attempt_interval == 0.1  #
    assert instance.ready is True  # AbstractRabbitMQ sets ready to True after initialization
    assert instance.setup_called is True  # setup method should be called


@pytest.mark.parametrize("invalid_host", [123, None, []])
def test_abstract_rabbitmq_init_invalid_host(invalid_host, mock_health_check_dependencies):
    """Test initialization with invalid host types."""
    with pytest.raises(ValueError, match="host must be a string."):
        ConcreteRabbitMQ(host=invalid_host)


@pytest.mark.parametrize("invalid_port", ["abc", 0, -1, None])
def test_abstract_rabbitmq_init_invalid_port(invalid_port, mock_health_check_dependencies):
    """Test initialization with invalid port values/types."""
    with pytest.raises(ValueError, match="port must be a positive integer."):
        ConcreteRabbitMQ(port=invalid_port)


@pytest.mark.parametrize("invalid_attempts", ["abc", 0, -1, None])
def test_abstract_rabbitmq_init_invalid_max_attempts(invalid_attempts, mock_health_check_dependencies):
    """Test initialization with invalid max_attempts values/types."""
    with pytest.raises(ValueError, match="max_retries must be a positive integer."):
        ConcreteRabbitMQ(max_attempts=invalid_attempts)


@pytest.mark.parametrize("invalid_interval", ["abc", 0.0, -1.0, None])
def test_abstract_rabbitmq_init_invalid_attempt_interval(invalid_interval, mock_health_check_dependencies):
    """Test initialization with invalid attempt_interval values/types."""
    with pytest.raises(ValueError, match="attempt_interval must be a positive float."):
        ConcreteRabbitMQ(attempt_interval=invalid_interval)


# --- Test Connection Logic (_connect method) ---

@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)  # Mock time.sleep to avoid actual delays
def test_connect_success_first_attempt(mock_sleep, mock_blocking_connection, mock_health_check_dependencies):
    """Test successful connection on the first attempt."""
    mock_channel = MagicMock()
    mock_connection_instance = MagicMock()
    mock_connection_instance.channel.return_value = mock_channel
    mock_blocking_connection.return_value = mock_connection_instance

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    channel = instance.channel  #

    mock_blocking_connection.assert_called_once()  # Called on __init__
    mock_sleep.assert_not_called()  #
    assert channel == mock_channel  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_connect_success_after_retries(mock_sleep, mock_blocking_connection, mock_health_check_dependencies):
    """Test successful connection after a few retries."""
    mock_channel = MagicMock()
    mock_connection_instance = MagicMock()
    mock_connection_instance.channel.return_value = mock_channel

    # Configure BlockingConnection to raise AMQPConnectionError twice, then succeed
    mock_blocking_connection.side_effect = [
        AMQPConnectionError,
        AMQPConnectionError,
        mock_connection_instance  # Success on the third call
    ]

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=3, attempt_interval=0.01)  #
    channel = instance.channel

    assert mock_blocking_connection.call_count == 3  #
    assert mock_sleep.call_count == 2  # Sleep should be called after each failed attempt
    mock_sleep.assert_called_with(0.01)  # Check sleep interval
    assert channel == mock_channel  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_connect_failure_after_max_attempts(mock_sleep, mock_blocking_connection, mock_health_check_dependencies):
    """Test that connection fails and raises an exception after max_attempts."""
    mock_blocking_connection.side_effect = AMQPConnectionError  # Always fail

    with pytest.raises(Exception, match="Failed to connect to RabbitMQ after "):  #
        instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=3, attempt_interval=1)  #

    assert mock_blocking_connection.call_count == 3  #
    assert mock_sleep.call_count == 3  # Sleep after each failed attempt, including the last one before raising


# --- Test Channel Property ---

@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_channel_property(mock_sleep, mock_blocking_connection, mock_health_check_dependencies):
    """Test that the channel property returns the correct channel."""
    mock_channel = MagicMock()
    mock_connection_instance = MagicMock()
    mock_connection_instance.channel.return_value = mock_channel
    mock_blocking_connection.return_value = mock_connection_instance

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    assert instance.channel == mock_channel  #


# --- Test __del__ method ---

@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_closes_channel_if_open(mock_sleep, mock_blocking_connection, mock_health_check_dependencies, capsys):
    """Test that __del__ closes the channel if it's open."""
    mock_channel = MagicMock()
    mock_channel.is_closed = False  # Simulate open channel
    mock_connection_instance = MagicMock()
    mock_connection_instance.channel.return_value = mock_channel
    mock_blocking_connection.return_value = mock_connection_instance

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    # Explicitly delete the instance to call __del__
    del instance

    mock_channel.close.assert_called_once()  #
    captured = capsys.readouterr()  # Capture print statements
    assert "Channel closed." in captured.out  #


@patch('pika.BlockingConnection')
@patch('time.sleep', return_value=None)
def test_del_does_not_close_channel_if_already_closed(mock_sleep, mock_blocking_connection,
                                                      mock_health_check_dependencies, capsys):
    """Test that __del__ does not attempt to close an already closed channel."""
    mock_channel = MagicMock()
    mock_channel.is_closed = True  # Simulate closed channel
    mock_connection_instance = MagicMock()
    mock_connection_instance.channel.return_value = mock_channel
    mock_blocking_connection.return_value = mock_connection_instance

    instance = ConcreteRabbitMQ(host="test_host", port=1234, max_attempts=1, attempt_interval=0.01)  #
    del instance

    mock_channel.close.assert_not_called()  #
    captured = capsys.readouterr()  # Capture print statements
    assert "Channel already closed." in captured.out  #
    assert "Channel closed." in captured.out  # The final "Channel closed." print should still occur


# --- Test Setup method call ---
@patch('pika.BlockingConnection')
def test_setup_called_on_init(mock_blocking_connection, mock_health_check_dependencies):
    """Test that the abstract setup method is called during initialization."""
    # We use ConcreteRabbitMQ which sets a flag when setup is called
    instance = ConcreteRabbitMQ(host="localhost", port=5672, max_attempts=1, attempt_interval=0.1)  #
    assert instance.setup_called is True  #
