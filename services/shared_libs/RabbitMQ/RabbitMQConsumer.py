from abc import ABC, abstractmethod

from pika.channel import Channel
from pika.spec import Basic, BasicProperties

from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ


class RabbitMQConsumer(AbstractRabbitMQ, ABC):

    def consume(self, queue: str, auto_ack: bool = False):
        self.channel.queue_declare(queue=queue, durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=queue, on_message_callback=self.callback,  auto_ack=auto_ack)
        print(f"Consuming messages from queue '{queue}'...")
        self.channel.start_consuming()

    @abstractmethod
    def callback(self, ch: Channel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
        """Subclasses should override this to handle incoming messages."""
        pass
