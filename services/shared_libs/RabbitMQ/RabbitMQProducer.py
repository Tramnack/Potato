from abc import ABC

import pika

from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ


class RabbitMQProducer(AbstractRabbitMQ, ABC):
    def setup(self):
        # Optionally declare exchange or queue here
        pass

    def publish(self, queue: str, message, durable: bool = True):
        self.channel.queue_declare(queue=queue, durable=durable)
        self.channel.basic_publish(
            exchange='',
            routing_key=queue,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2) if durable else None
        )
        print(f" [x] Sent '{message}'")