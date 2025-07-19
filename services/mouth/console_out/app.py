import os

from services.shared_libs.RabbitMQ import RabbitMQConsumer


def main():
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))

    consumer = RabbitMQConsumer(RABBITMQ_HOST, RABBITMQ_PORT)
    print(' [*] Mouth waiting for messages. To exit press CTRL+C')
    consumer.consume('brain_to_mouth', callback, auto_ack=False)


def callback(ch, method, properties, body):
    received_text = body.decode()
    print(f" [x] Mouth received '{received_text}'")
    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    main()
