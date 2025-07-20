import threading

from flask import Flask


class HealthCheckMixin:
    _is_ready = False
    _health_app = Flask(__name__)

    def __init__(self, health_port=8000):
        self._health_port = health_port
        self._setup_health_routines()
        self._start_health_server()

    @property
    def health_port(self):
        return self._health_port

    @property
    def ready(self):
        return self._is_ready

    @ready.setter
    def ready(self, value):
        self._is_ready = value

    def _setup_health_routines(self):
        @self._health_app.route("/health")
        def health():
            return ("OK", 200) if self._is_ready else ("Starting...", 503)

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
