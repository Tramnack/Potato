import threading
import time

from flask import Flask


class HealthCheckMixin:
    _is_ready = False
    _status = "unknown"
    _health_app = Flask(__name__)
    __no_app = False

    def __init__(self, health_check_port: int = 8000):
        if self.__no_app:
            self._health_port = None
            self._health_app = None
            self._is_ready = True
            return

        try:
            health_check_port = int(health_check_port)
        except ValueError:
            raise ValueError("health_check_port must be an integer.")

        self._health_port = health_check_port
        self._setup_health_routines()
        self._start_health_server()
        self._start_time = time.time()

    @classmethod
    def no_app(cls):
        cls.__no_app = True
        return cls(health_check_port=0)

    @property
    def health_check_port(self):
        return self._health_port

    @property
    def ready(self):
        return self._is_ready

    @ready.setter
    def ready(self, value):
        self._is_ready = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    def _setup_health_routines(self):
        @self._health_app.route("/health")
        def health():
            return ("OK", 200) if self._is_ready else ("Starting...", 503)

        @self._health_app.route("/status")
        def status():
            uptime = time.time() - self._start_time
            return {
                "status": self._status,
                "ready": self._is_ready,
                "uptime_seconds": round(uptime, 2)
            }, 200 if self._is_ready else 503

    def _start_health_server(self):
        print(f"Starting health server on port {self._health_port}")
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
