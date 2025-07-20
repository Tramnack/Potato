from abc import ABC

from services.shared_libs.RabbitMQ import RabbitMQConsumer


class AbstractMouth(RabbitMQConsumer, ABC):
    pass
