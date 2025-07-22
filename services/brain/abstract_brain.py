from abc import ABC

from services.shared_libs.RabbitMQ import RabbitMQConsumer, RabbitMQProducer, RMQ_HOST, RMQ_PORT


class AbstractBrain(RabbitMQConsumer, RabbitMQProducer, ABC):
    def __init__(self,
                 queue_name: str,
                 host: str = RMQ_HOST,
                 port: int = RMQ_PORT,
                 connection_attempts: int = 5,
                 retry_delay: float = 5):
        RabbitMQConsumer.__init__(self, queue_name, host, port, connection_attempts, retry_delay)
        RabbitMQProducer.__init__(self, host, port, connection_attempts, retry_delay)
