import os
import sys

from services.shared_libs.RabbitMQ import RabbitMQConsumer


def main():
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))  # Also good to make port dynamic

    consumer = RabbitMQConsumer(RABBITMQ_HOST, RABBITMQ_PORT)
    print(' [*] Brain waiting for messages. To exit press CTRL+C')
    consumer.consume('ear_to_brain', callback, auto_ack=True)


def callback(ch, method, properties, body):
    received_text = body.decode()
    print(f" [x] Brain received '{received_text}'")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            exit(0)
