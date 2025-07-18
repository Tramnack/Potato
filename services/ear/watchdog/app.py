import os
import time

from services.shared_libs.RabbitMQ import RabbitMQProducer


def main():
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))  # Also good to make port dynamic

    producer = RabbitMQProducer(RABBITMQ_HOST, RABBITMQ_PORT)

    try:
        i = 0
        while True:
            i += 1
            user_input = f"Message Nr.{i}"
            message = user_input.encode()
            producer.publish('ear_to_brain', message)
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
