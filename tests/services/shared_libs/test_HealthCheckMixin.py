import time
from unittest.mock import patch

import pytest
import requests

from services.shared_libs import HealthCheckMixin


# A simple class to mix in HealthCheckMixin for testing purposes
class MyService(HealthCheckMixin):
    def __init__(self, port):
        super().__init__(health_check_port=port)
        # Simulate some initialization
        time.sleep(0.1)
        self.ready = True
        self.status = "operational"


class MyServiceNotReady(HealthCheckMixin):
    def __init__(self, port):
        super().__init__(health_check_port=port)
        self.ready = False
        self.status = "initializing"


class MyServiceNoApp(HealthCheckMixin):
    def __init__(self):
        # Use the class method to initialize without an app
        super().__init__(health_check_port=0)


@pytest.fixture(scope="module")
def health_service_ready():
    """Fixture to provide a ready HealthCheckMixin instance."""
    port = 5001  # Use a distinct port for this fixture
    service = MyService(port)

    count = 0
    # Give the server a moment to start
    while service.uptime is None and count < 10:
        time.sleep(0.5)
        count += 1
    if service.uptime is None:
        raise RuntimeError("Health check server failed to start.")

    yield service
    # Teardown: In a real scenario, you might need to explicitly stop the Flask app if it wasn't a daemon thread,
    # but daemon threads will exit with the test runner.


@pytest.fixture(scope="module")
def health_service_not_ready():
    """Fixture to provide a not-ready HealthCheckMixin instance."""
    port = 5002  # Use a distinct port
    service = MyServiceNotReady(port)
    time.sleep(0.5)
    yield service


@pytest.fixture(scope="module")
def health_service_no_app():
    """Fixture to provide a HealthCheckMixin instance initialized with no_app."""
    service = MyServiceNoApp()
    yield service


def test_initialization_with_valid_port():
    """Test that the mixin initializes correctly with a valid port."""
    mixin = HealthCheckMixin(health_check_port=8000)
    assert mixin.health_check_port == 8000
    assert not mixin.ready  # Should be False initially
    assert mixin.status is None


def test_initialization_with_invalid_port_string():
    """Test that initialization raises ValueError for an invalid string port."""
    with pytest.raises(ValueError, match="health_check_port must be an integer."):
        HealthCheckMixin(health_check_port="invalid")


def test_initialization_with_invalid_port_negative():
    """Test that initialization raises ValueError for an invalid negative port."""
    with pytest.raises(ValueError, match="health_check_port must be a positive integer."):
        HealthCheckMixin(health_check_port=-1)


def test_initialization_with_invalid_port_zero():
    """Test that initialization raises ValueError for an invalid port (0)."""
    with pytest.raises(ValueError, match="health_check_port must be a positive integer."):
        HealthCheckMixin(health_check_port=0)


def test_initialization_with_valid_port_float():
    """Test that the mixin initializes correctly with a valid port."""
    mixin = HealthCheckMixin(health_check_port=7999.0)
    assert mixin.health_check_port == 7999


def test_initialization_with_invalid_port_float():
    """Test that initialization raises ValueError for an invalid float port."""
    with pytest.raises(ValueError, match="health_check_port must be a positive integer."):
        HealthCheckMixin(health_check_port=0.5)


def test_no_app_initialization():
    """Test initialization using the no_app class method."""
    mixin = HealthCheckMixin.no_app()
    assert mixin.health_check_port is None
    assert mixin._health_app is None
    assert mixin.ready is True  # Should be True when no_app is used


def test_ready_property():
    """Test the ready getter and setter."""
    mixin = HealthCheckMixin(health_check_port=8003)
    assert mixin.ready is False  # Should be False initially
    mixin.ready = True
    assert mixin.ready is True
    mixin.ready = False
    assert mixin.ready is False


def test_no_app_initialization_ready_property():
    """Test initialization using the no_app class method."""
    mixin = HealthCheckMixin.no_app()
    assert mixin.ready is True  # Should be True when no_app is used
    mixin.ready = False
    assert mixin.ready is False
    mixin.ready = True
    assert mixin.ready is True


def test_status_property():
    """Test the status getter and setter."""
    mixin = HealthCheckMixin(health_check_port=8004)
    assert mixin.status is None
    mixin.status = "initializing"
    assert mixin.status == "initializing"
    mixin.status = "healthy"
    assert mixin.status == "healthy"


def test_uptime_property():
    """Test the uptime getter."""
    mixin = HealthCheckMixin(health_check_port=8005)
    time.sleep(0.5)
    assert mixin.uptime is not None
    assert mixin.uptime > 0


def test_health_endpoint_ready(health_service_ready):
    """Test the /health endpoint when the service is ready."""
    response = requests.get(f"http://127.0.0.1:{health_service_ready.health_check_port}/health")
    assert response.status_code == 200
    assert response.text == "OK"


def test_health_endpoint_not_ready(health_service_not_ready):
    """Test the /health endpoint when the service is not ready."""
    response = requests.get(f"http://127.0.0.1:{health_service_not_ready.health_check_port}/health")
    assert response.status_code == 503
    assert response.text == "Starting..."


def test_status_endpoint_ready(health_service_ready):
    """Test the /status endpoint when the service is ready."""
    response = requests.get(f"http://127.0.0.1:{health_service_ready.health_check_port}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["ready"] is True
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] > 0


def test_status_endpoint_not_ready(health_service_not_ready):
    """Test the /status endpoint when the service is not ready."""
    response = requests.get(f"http://127.0.0.1:{health_service_not_ready.health_check_port}/status")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "initializing"
    assert data["ready"] is False
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] > 0


def test_health_server_starts_in_thread():
    """
    Test that the health server is started in a separate thread.
    This is more of an integration-like unit test.
    """
    # Use a mock for Flask.run to check if it's called in a new thread
    with patch('flask.Flask.run') as mock_run:
        mixin = HealthCheckMixin(health_check_port=8005)
        # Give a brief moment for the thread to potentially start
        time.sleep(0.1)
        # Verify that Flask.run was called
        mock_run.assert_called_once_with(
            host="0.0.0.0", port=8005, debug=False, use_reloader=False
        )
        assert mixin.uptime is not None
        assert mixin.uptime >= 0.1
