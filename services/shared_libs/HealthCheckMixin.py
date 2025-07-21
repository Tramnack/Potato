import threading
import time
from typing import Optional

from flask import Flask

from services.shared_libs.logging_config import setup_logging


class HealthCheckMixin:
    """
    Mixin class to add health check functionality to other classes.

    This mixin provides a simple HTTP health check server that can be used
    to monitor the readiness and status of a service.
    """

    def __init__(self, health_check_port: int = 5000):
        """
        Initialize the HealthCheckMixin class.

        Creates a health check server and starts it in a separate thread.

        The ``status`` property should be set by subclasses to
        indicate the service's readiness state. (not Null)

        :param health_check_port: The port on which the health check server will listen.
                                  If set to None, the health check server will not be started.
                                  Defaults to 5000.
        :raises ValueError: If `health_check_port` is not a valid integer.
        """

        # Ensure the health_check_port is an integer.
        try:
            health_check_port = int(health_check_port)
        except ValueError:
            raise ValueError("health_check_port must be a valid port number.")

        if health_check_port <= 0:
            raise ValueError("health_check_port must be a valid port number.")

        self._ready = False
        self._status = None
        self._status_code = 503

        self.logger = setup_logging(service_name=self.__class__.__name__)

        self._health_port = health_check_port
        self._health_app = Flask(__name__)

        # Set up the health check server routes.
        self._setup_health_routines()
        # Start the health check server in a separate thread.
        self._start_health_server()
        # Record the start time for uptime calculation.
        self._start_time = time.time()
        self.logger.info(f"Health Check Server initialized on port {self.health_check_port}")

    @property
    def health_check_port(self) -> int:
        """
        Get the port on which the health check server is listening.

        :return: The health check port.
        """
        return self._health_port

    @property
    def ready(self) -> bool:
        """
        Get or set the readiness state of the service.

        :return: True if the service is ready, False otherwise.
        """
        return self._ready

    @ready.setter
    def ready(self, value: bool):
        """
        Set the readiness state of the service.

        :param value: True to set the service as ready, False otherwise.
        """
        if not isinstance(value, bool):
            raise ValueError("ready must be a boolean.")
        self._ready = value

    @property
    def status(self) -> Optional[str]:
        """
        Get or set the current status message of the service.

        This can be used to provide more detailed information about the
        service's internal state.

        :return: The status message string.
        """
        return self._status

    @status.setter
    def status(self, value: str):
        """
        Set the current status message of the service.

        :param value: The status message string.
        """
        if not isinstance(value, str) and value is not None:
            self.logger.warning(f"Non-string value provided for status: {value} Converting to string.")
            value = str(value)
        self._status = value

    @property
    def status_code(self) -> int:
        """
        Get or set the HTTP status code for the current status message.

        :return: The HTTP status code.
        """
        return self._status_code or 500

    @status_code.setter
    def status_code(self, value: int):
        """
        Set the HTTP status code for the current status message.

        :param value: The HTTP status code.
        """
        if not isinstance(value, int) or 0 > value or value > 599:
            raise ValueError("status_code should be valid HTTP status code.")
        self._status_code = value

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
            return ("OK", 200) if self._ready else ("Starting...", 503)

        @self._health_app.route("/status")
        def status():
            """
            Status check endpoint.

            Returns a dictionary with readiness, status message, and uptime.
            Returns 503 Service Unavailable if the service is not ready.
            """
            return {
                "status": self._status,
                "uptime_seconds": self.uptime
            }, self._status_code if self._ready else 503

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
