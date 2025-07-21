import time
from unittest.mock import patch

import pytest
import requests

from services.shared_libs import HealthCheckMixin


# A simple class to mix in HealthCheckMixin for testing purposes
class MyService(HealthCheckMixin):
    def __init__(self, port):
        super().__init__(health_check_port=port)
        self._health_app.config.update({
            "TESTING": True
        })
        # Simulate some initialization
        time.sleep(0.1)
        self.ready = True


class MyServiceReady(HealthCheckMixin):
    def __init__(self, port):
        super().__init__(health_check_port=port)
        self._health_app.config.update({
            "TESTING": True
        })
        # Simulate some initialization
        time.sleep(0.1)
        self.ready = True
        self.status = "operational"
        self.status_code = 200


class MyServiceNotReady(HealthCheckMixin):
    def __init__(self, port):
        super().__init__(health_check_port=port)
        self._health_app.config.update({
            "TESTING": True
        })
        # Simulate some initialization
        time.sleep(0.1)
        # self.ready = False  # Keep the service not ready


@pytest.fixture(scope="module")
def health_service_ready():
    """Fixture to provide a ready HealthCheckMixin instance."""
    port = 5001  # Use a distinct port for this fixture
    service = MyServiceReady(port)

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
def health_service():
    """Fixture to provide a not-ready HealthCheckMixin instance."""
    port = 5002  # Use a distinct port
    service = MyService(port)
    time.sleep(0.5)
    yield service


@pytest.fixture(scope="module")
def health_service_not_ready():
    """Fixture to provide a not-ready HealthCheckMixin instance."""
    port = 5003  # Use a distinct port
    service = MyServiceNotReady(port)
    time.sleep(0.5)
    yield service


class TestInitialization:

    @pytest.mark.parametrize("valid_port", [5000, 8000.0])
    def test_initialization_with_valid_port(self, valid_port):
        """Test that the mixin initializes correctly with a valid port."""
        mixin = HealthCheckMixin(health_check_port=valid_port)
        assert mixin.health_check_port == valid_port
        assert not mixin.ready
        assert mixin.status is None
        assert mixin.status_code == 503

    @pytest.mark.parametrize("invalid_port", ["invalid", -1, 0, 0.5])
    def test_initialization_with_invalid_port_string(self, invalid_port):
        """Test that initialization raises ValueError for an invalid string port."""
        with pytest.raises(ValueError, match="health_check_port must be a valid port number"):
            HealthCheckMixin(health_check_port=invalid_port)


class TestProperties:

    def test_ready_property(self):
        """Test the ready getter and setter."""
        mixin = HealthCheckMixin(health_check_port=8003)
        assert not mixin.ready
        assert mixin.status is None
        assert mixin.status_code == 503

        mixin.ready = True
        assert mixin.ready
        assert mixin.status is None
        assert mixin.status_code == 503

    @pytest.mark.parametrize("status", ["operational", 200])
    @pytest.mark.parametrize("code", [200, 200])
    def test_status_property(self, status, code):
        """Test the status getter and setter."""
        mixin = HealthCheckMixin(health_check_port=8004)
        assert not mixin.ready
        assert mixin.status is None
        assert mixin.status_code == 503

        mixin.status = status
        mixin.status_code = code
        assert mixin.status == str(status)
        assert mixin.status_code == code

    def test_status_property_none(self):
        """Test the status getter and setter."""
        mixin = HealthCheckMixin(health_check_port=8004)
        assert not mixin.ready
        assert mixin.status is None
        assert mixin.status_code == 503

        mixin.status = "status"
        mixin.status_code = 200

        mixin.status = None
        mixin.status_code = 204
        assert mixin.status is None
        assert mixin.status_code == 204

    @pytest.mark.parametrize("code", ["operational", 600, -200, None])
    def test_status_property_bad_status_code(self, code):
        """Test the status getter and setter."""
        mixin = HealthCheckMixin(health_check_port=8004)
        assert not mixin.ready
        assert mixin.status_code == 503

        with pytest.raises(ValueError, match="status_code should be valid HTTP status code."):  # Regex
            mixin.status_code = code
        assert mixin.status_code == 503

    def test_uptime_property(self):
        """Test the uptime getter."""
        mixin = HealthCheckMixin(health_check_port=8005)
        time.sleep(0.5)
        assert mixin.uptime is not None
        assert mixin.uptime >= 0.5


class TestHealthEndpoint:

    def test_health_endpoint_ready(self, health_service_ready):
        """Test the /health endpoint when the service is ready."""
        response = requests.get(f"http://127.0.0.1:{health_service_ready.health_check_port}/health")
        assert response.status_code == 200
        assert response.text == "OK"

    def test_health_endpoint(self, health_service):
        """Test the /health endpoint when the service is ready."""
        response = requests.get(f"http://127.0.0.1:{health_service.health_check_port}/health")
        assert response.status_code == 200
        assert response.text == "OK"

    def test_health_endpoint_not_ready(self, health_service_not_ready):
        """Test the /health endpoint when the service is not ready."""
        response = requests.get(f"http://127.0.0.1:{health_service_not_ready.health_check_port}/health")
        assert response.status_code == 503
        assert response.text == "Starting..."


class TestStatusEndpoint:

    def test_status_endpoint_ready(self, health_service_ready):
        """Test the /status endpoint when the service is ready."""
        response = requests.get(f"http://127.0.0.1:{health_service_ready.health_check_port}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"  # defined by MyServiceReady class
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] > 0

    def test_status_endpoint(self, health_service):
        """Test the /status endpoint when the service is ready."""
        response = requests.get(f"http://127.0.0.1:{health_service.health_check_port}/status")
        assert response.status_code == 503  # Default
        data = response.json()
        assert data["status"] is None  # not defined in MyService class
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] > 0

    def test_status_endpoint_not_ready(self, health_service_not_ready):
        """Test the /status endpoint when the service is not ready."""
        response = requests.get(f"http://127.0.0.1:{health_service_not_ready.health_check_port}/status")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] is None
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] > 0


class TestHealthServer:

    def test_health_server_starts_in_thread(self):
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
