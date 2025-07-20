from abc import ABC

from services.shared_libs.RabbitMQ import RabbitMQProducer


class AbstractEar(RabbitMQProducer, ABC):
    pass
