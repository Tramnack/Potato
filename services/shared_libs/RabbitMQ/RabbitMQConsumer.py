from abc import ABC

from pika.exceptions import ChannelClosedByBroker, ChannelClosed

from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ


class RabbitMQConsumer(AbstractRabbitMQ):
    def setup(self):
        # Optionally declare queue or bindings
        pass

    def consume(self, queue: str, callback, auto_ack: bool = False):
        self.channel.queue_declare(queue=queue, durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=auto_ack)
        print(f"Consuming messages from queue '{queue}'...")
        self.channel.start_consuming()

