from abc import ABC

import pika
from pika.exceptions import AMQPChannelError, AMQPConnectionError

from services.shared_libs.RabbitMQ.AbstractRabbitMQ import AbstractRabbitMQ


class RabbitMQProducer(AbstractRabbitMQ, ABC):

    def publish(self, message: bytes, routing_key: str, exchange: str = '', durable: bool = True) -> None:
        """
        Publishes a message to the specified exchange and routing key.

        :param message: The message to publish.
        :param routing_key: The routing key used to route the message to the correct queue.
        :param exchange: The exchange to publish the message to. If left blank, the message will be published to the default exchange.
        :param durable: If True, the message will be persisted to disk. If False, the message will not be persisted.
        """
        self._basic_publish(exchange, routing_key, message, durable)

    def _basic_publish(self, exchange: str, routing_key: str, body: bytes, durable: bool = True) -> None:
        """
        Publishes a message to the specified exchange and routing key.

        :param exchange: The exchange to publish the message to. If left blank, the message will be published to the default exchange.
        :param routing_key: The routing key used to route the message to the correct queue.
        :param body: The message to publish.
        :param durable: If True, the message will be persisted to disk. If False, the message will not be persisted.
        """
        if not self._ready():
            msg = "RabbitMQProducer is not connected."
            self.logger.error(msg)
            raise RuntimeError(msg + " Call connect() first.")

        try:
            self._channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=pika.DeliveryMode.Persistent if durable else pika.DeliveryMode.Transient)
            )
            self.logger.info(f"Published message to exchange: {exchange}, routing key: {routing_key}")
        except AMQPChannelError as e:
            self.logger.error(f"AMQP Channel Error during publish: {e}")
            raise e
        except AMQPConnectionError as e:
            self.logger.error(f"AMQP Connection Error during publish: {e}")
            raise e
        except Exception as e:
            self.logger.critical(f"An unexpected error occurred during publish: {e}")
            raise e
