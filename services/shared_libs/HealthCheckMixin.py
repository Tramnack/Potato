import threading
import time
from typing import Any, Optional

from flask import Flask


class HealthCheckMixin:
    """
    Mixin class to add health check functionality to other classes.

    This mixin provides a simple HTTP health check server that can be used
    to monitor the readiness and status of a service.
    """

    def __init__(self, health_check_port: Optional[int] = 5000):
        """
        Initialize the HealthCheckMixin class.

        Creates a health check server and starts it in a separate thread.

        The ``ready`` property should be manipulated by subclasses to
        indicate the service's readiness state.

        :param health_check_port: The port on which the health check server will listen.
                                  If set to None, the health check server will not be started.
                                  Defaults to 5000.
        :raises ValueError: If `health_check_port` is not a valid integer.
        """

        self._is_ready = False
        self._status = None

        # If no_app was called, skip setting up the Flask app and return early.
        if health_check_port is None:
            self._health_port = None
            self._health_app = None
            self._is_ready = True
            return

        # Ensure the health_check_port is an integer.
        if not isinstance(health_check_port, int):
            try:
                health_check_port = int(health_check_port)
            except ValueError:
                raise ValueError("health_check_port must be an integer or a string convertible to an integer.")

        if health_check_port <= 0:
            raise ValueError("health_check_port must be a positive integer.")

        self._health_port = health_check_port
        self._health_app = Flask(__name__)

        # Set up the health check server routes.
        self._setup_health_routines()
        # Start the health check server in a separate thread.
        self._start_health_server()
        # Record the start time for uptime calculation.
        self._start_time = time.time()

    @classmethod
    def no_app(cls):
        """
        Initialize the HealthCheckMixin class without a health check server.

        This factory method allows creating an instance of the mixin where
        the health check server functionality is disabled. The `ready` property
        will default to True in this case.
        """
        return cls(health_check_port=None)

    @property
    def health_check_port(self) -> int:
        """
        Get the port on which the health check server is listening.

        :return: The health check port.
        """
        return self._health_port

    @property
    def ready(self):
        """
        Get or set whether the service is ready.

        When `True`, the service is considered ready to handle requests.
        When `False`, the service is still initializing or in an unready state.

        :return: True if the service is ready, False otherwise.
        """
        return self._is_ready

    @ready.setter
    def ready(self, value: bool):
        """
        Set whether the service is ready.

        :param value: True to mark the service as ready, False otherwise.
        """
        if not isinstance(value, bool):
            raise ValueError("ready must be a boolean.")
        self._is_ready = value

    @property
    def status(self) -> Any:
        """
        Get or set the current status message of the service.

        This can be used to provide more detailed information about the
        service's internal state.

        :return: A string representing the service's status.
        """
        return self._status

    @status.setter
    def status(self, value: Any):
        """
        Set the current status message of the service.

        :param value: The status message string.
        """
        self._status = value

    @property
    def uptime(self) -> Optional[float]:
        """
        Get the uptime of the service in seconds.

        :return: The uptime of the service in seconds. None if the start time is not set.
        """
        if self._start_time is None:
            return None
        return round(time.time() - self._start_time, 2)

    def _setup_health_routines(self) -> None:
        """
        Set up the Flask routes for health and status checks.

        The '/health' endpoint returns a 200 OK if the service is ready,
        otherwise a 503 Service Unavailable.
        The '/status' endpoint provides more detailed information including
        readiness, current status message, and uptime.
        """
        @self._health_app.route("/health")
        def health():
            """
            Health check endpoint.

            Returns 200 OK if the service is ready, 503 Service Unavailable otherwise.
            """
            return ("OK", 200) if self._is_ready else ("Starting...", 503)

        @self._health_app.route("/status")
        def status():
            """
            Status check endpoint.

            Returns a JSON object with the service's status, readiness, and uptime.
            Returns 200 OK if the service is ready, 503 Service Unavailable otherwise.
            """
            return {
                "status": self._status,
                "ready": self._is_ready,
                "uptime_seconds": self.uptime
            }, 200 if self._is_ready else 503

    def _start_health_server(self):
        """
        Starts the Flask health check server in a separate daemon thread.

        The server listens on 0.0.0.0 (all available interfaces) and the
        configured `_health_port`. It runs in debug mode off and without
        a reloader to ensure stability in production-like environments.
        """
        threading.Thread(
            target=self._health_app.run,
            kwargs={
                "host": "0.0.0.0",
                "port": self._health_port,
                "debug": False,
                "use_reloader": False
            },
            daemon=True
        ).start()
