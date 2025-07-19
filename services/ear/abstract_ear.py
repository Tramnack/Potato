from abc import abstractmethod, ABC

from services.shared_libs.RabbitMQ import RabbitMQProducer


class AbstractEar(RabbitMQProducer, ABC):
    pass
