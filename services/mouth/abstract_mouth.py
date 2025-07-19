from abc import abstractmethod, ABC

from services.shared_libs.RabbitMQ import RabbitMQConsumer


class AbstractMouth(RabbitMQConsumer, ABC):
    pass