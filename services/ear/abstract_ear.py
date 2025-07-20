from abc import ABC

from services.shared_libs import HealthCheckMixin
from services.shared_libs.RabbitMQ import RabbitMQProducer, RMQ_HOST, RMQ_PORT


class AbstractEar(RabbitMQProducer, HealthCheckMixin, ABC):
    def __init__(self,
                 host: str = RMQ_HOST,
                 port: int = RMQ_PORT,
                 max_attempts: int = 5,
                 attempt_interval: float = 5.0,
                 health_port=8000):
        HealthCheckMixin.__init__(self, health_port)
        RabbitMQProducer.__init__(self, host, port, max_attempts, attempt_interval)
