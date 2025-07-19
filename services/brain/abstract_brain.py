from abc import abstractmethod, ABC

from services.shared_libs.RabbitMQ import RabbitMQConsumer, RabbitMQProducer


class AbstractBrain(RabbitMQConsumer, RabbitMQProducer, ABC):
    pass